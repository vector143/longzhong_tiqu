"""
爬虫Worker - 单篇文章处理
"""

import random
import threading
import time
from typing import Any, Dict, List, Optional

from config.settings import get_settings
from convert import AsyncFormatConverter, html_to_text_and_tables
from convert.cleaned_converter import CleanedConverter
from crawl.oilchem_requests import extract_article_content

# 模块级别缓存 CleanedConverter 实例
_cleaned_converter: Optional[CleanedConverter] = None
_cleaned_converter_lock = threading.Lock()


def _get_cleaned_converter() -> Optional[CleanedConverter]:
    """
    获取或创建 CleanedConverter 单例

    Returns:
        CleanedConverter 实例，如果 cleaned 功能未启用或初始化失败则返回 None
    """
    global _cleaned_converter
    settings = get_settings()

    if not settings.cleaned.enable:
        return None

    if _cleaned_converter is None:
        with _cleaned_converter_lock:
            if _cleaned_converter is None:
                try:
                    _cleaned_converter = CleanedConverter(
                        output_dir=settings.cleaned.output_dir,
                        on_duplicate=settings.cleaned.on_duplicate,
                        filename_max_length=settings.cleaned.filename_max_length,
                    )
                except Exception as e:
                    print(f"⚠️ CleanedConverter 初始化失败（已忽略）: {e}")
                    return None
    return _cleaned_converter


def crawl_article_worker_async(
    article_data: Dict[str, Any],
    session,
    output_formats: List[str],
    converter: AsyncFormatConverter,
    delay: float = 1,
) -> Optional[Dict[str, Any]]:
    """
    异步版本的工作线程函数

    Args:
        article_data: 包含article, index, total的字典
        session: requests会话对象
        output_formats: 输出格式列表
        converter: 格式转换器
        delay: 请求间延时

    Returns:
        处理结果字典，失败返回None
    """
    try:
        article = article_data["article"]
        index = article_data["index"]
        total = article_data["total"]

        print(
            f"🧵 {threading.current_thread().name} 处理第 {index}/{total} 篇: "
            f"{article['title'][:40]}..."
        )

        # 提取正文内容
        content_data = extract_article_content(article["url"], session=session)

        # 检查是否需要登录或无权限
        html_content = content_data["html_content"]
        if "需要登录" in html_content or "没有开通该新闻的页面权限" in html_content:
            print(f"⏭️ 跳过无权限: {article['title'][:30]}...")
            return None

        # 处理文件
        upload_status: Dict[str, bool] = {}
        local_files: Dict[str, str] = {}

        # Markdown格式
        if "markdown" in output_formats:
            md_result = converter.save_as_markdown(
                html_content,
                article["title"],
                article.get("articleId", f"id_{index}"),
                publish_time=article.get("publishTime"),
            )
            if md_result:
                upload_status["markdown"] = True
                if md_result["local_saved"]:
                    local_files["markdown"] = md_result["local_path"]
            else:
                return None

        # JSON格式
        if "json" in output_formats:
            json_result = converter.save_as_json(
                html_content,
                article["title"],
                article.get("articleId", f"id_{index}"),
                publish_time=article.get("publishTime"),
                url=article.get("url"),
                column_name=article.get("columnName"),
            )
            if json_result:
                upload_status["json"] = True
                if json_result["local_saved"]:
                    local_files["json"] = json_result["local_path"]

                # 转换为 cleaned 格式（异常隔离，不影响主流程）
                cleaned_conv = _get_cleaned_converter()
                if cleaned_conv is not None:
                    try:
                        content_text, tables = html_to_text_and_tables(html_content)
                        cleaned_result = cleaned_conv.convert(
                            {
                                "articleId": article.get("articleId", f"id_{index}"),
                                "title": article["title"],
                                "publishTime": article.get("publishTime"),
                                "url": article.get("url"),
                                "columnName": article.get("columnName"),
                                "source": article.get("source", ""),
                                "content": content_text,
                                "tables": tables,
                            },
                            source_path=json_result.get("local_path"),
                        )
                        if cleaned_result.success and cleaned_result.cleaned_path:
                            local_files["cleaned"] = str(cleaned_result.cleaned_path)
                        elif not cleaned_result.success and cleaned_result.error:
                            print(f"⚠️ cleaned 转换失败: {cleaned_result.error}")
                    except Exception as e:
                        print(f"⚠️ cleaned 转换异常（已忽略）: {e}")
            else:
                return None

        # HTML格式
        if "html" in output_formats:
            html_result = converter.save_as_html_async(
                html_content,
                article["title"],
                article.get("articleId", f"id_{index}"),
                publish_time=article.get("publishTime"),
            )
            if html_result:
                upload_status["html"] = html_result.get("upload_submitted", False)
                if html_result["local_saved"]:
                    local_files["html"] = html_result["local_path"]

        # Word格式
        if "word" in output_formats:
            word_result = converter.html_to_word_async(
                html_content,
                article["title"],
                article.get("articleId", f"id_{index}"),
                publish_time=article.get("publishTime"),
            )
            if word_result:
                upload_status["word"] = word_result.get("upload_submitted", False)
                if word_result["local_saved"]:
                    local_files["word"] = word_result["local_path"]

        # 整理返回数据
        result_data = {
            "articleId": article.get("articleId", ""),
            "title": article.get("title", ""),
            "publishTime": article.get("publishTime", ""),
            "url": article.get("url", ""),
            "columnName": article.get("columnName", ""),
            "content_preview": article.get("content", "")[:100] + "...",
            "upload_status": upload_status,
            "local_files": local_files,
            "images_count": len(content_data["images_data"]),
            "has_tables": "table" in html_content.lower(),
        }

        # 请求间延时
        time.sleep(delay + random.uniform(0.1, 0.5))

        return result_data

    except Exception as e:
        print(f"❌ 线程 {threading.current_thread().name} 处理文章失败: {e}")
        return None
