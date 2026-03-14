"""
爬取管道 - 主流程控制
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Union

from config import get_settings
from crawl.api_requests import get_article_list
from crawl.worker import crawl_article_worker_async
from clients import OilChemCookiesManager, AsyncMemoryQiniuUploader
from convert import AsyncFormatConverter
from core import IncrementalUpdateLogger, UniversalNamingSystem
from storage import save_results

if TYPE_CHECKING:
    from monitor.utils import ThreadSafeSet


@dataclass
class CrawlResult:
    """爬取结果"""

    new_articles: List[Dict[str, Any]]  # 新爬取的文章列表
    skipped_count: int  # 跳过的已存在文章数
    success_count: int  # 成功数
    failed_count: int  # 失败数
    elapsed_time: float  # 耗时(秒)


def crawl_articles_async_multithread(
    keyword: str,
    pages: int = 3,
    delay: float = 2,
    cookies_manager: Optional[OilChemCookiesManager] = None,
    output_formats: Optional[List[str]] = None,
    days_back: Optional[int] = None,
    hours_back: Optional[int] = None,
    converter: Optional[AsyncFormatConverter] = None,
    max_crawl_workers: int = 5,
    max_upload_workers: int = 3,
) -> List[Dict[str, Any]]:
    """
    异步多线程爬取文章

    Args:
        keyword: 搜索关键词
        pages: 爬取页数
        delay: 请求间延时
        cookies_manager: Cookie管理器
        output_formats: 输出格式列表
        days_back: 向前追溯天数
        hours_back: 向前追溯小时数
        converter: 格式转换器
        max_crawl_workers: 最大爬取线程数
        max_upload_workers: 最大上传线程数

    Returns:
        文章数据列表
    """
    if output_formats is None:
        output_formats = ["html", "word"]

    all_articles: List[Dict[str, Any]] = []
    all_article_data: List[Dict[str, Any]] = []

    # 确定使用的session
    session = None
    if cookies_manager and cookies_manager.session:
        session = cookies_manager.session
        print("🔐 使用cookies会话进行爬取")
    else:
        print("⚠️  未使用cookies会话（可能无法访问全文）")

    # 获取所有文章列表
    print("📋 正在获取文章列表...")
    for page in range(1, pages + 1):
        print(f"获取第 {page} 页文章列表...")
        list_data = get_article_list(
            keyword,
            page_no=page,
            session=session,
            days_back=days_back,
            hours_back=hours_back,
        )
        if not list_data:
            print(f"第 {page} 页没有数据")
            continue

        articles = list_data["response"]["list"]
        print(f"第 {page} 页找到 {len(articles)} 篇文章")

        for article in articles:
            # 创建副本，将 article_id 追加到标题以避免 cleaned 文件名碰撞
            article_id = str(article.get("articleId", "")).strip()
            article_copy = dict(article)
            if article_id:
                original_title = article.get("title", "")
                article_copy["title"] = (
                    f"{original_title}_{article_id}" if original_title else article_id
                )

            all_article_data.append(
                {
                    "article": article_copy,
                    "index": len(all_article_data) + 1,
                    "total": 0,  # 稍后更新为实际总数
                }
            )

    # 更新实际总数
    total_count = len(all_article_data)
    for item in all_article_data:
        item["total"] = total_count

    print(f"📊 总共获取到 {total_count} 篇文章，开始异步多线程处理...")

    # 使用线程池处理文章
    with ThreadPoolExecutor(max_workers=max_crawl_workers) as executor:
        future_to_article = {
            executor.submit(
                crawl_article_worker_async,
                article_data,
                session,
                output_formats,
                converter,
                delay,
            ): article_data
            for article_data in all_article_data
        }

        completed_count = 0
        for future in as_completed(future_to_article):
            article_data = future_to_article[future]
            try:
                result = future.result()
                if result:
                    all_articles.append(result)
                    completed_count += 1
                    if (
                        converter
                        and converter.qiniu_uploader
                        and converter.upload_to_qiniu
                    ):
                        stats = converter.qiniu_uploader.get_upload_stats()
                        print(
                            f"✅ 完成进度: {completed_count}/{len(all_article_data)} | "
                            f"上传队列: {stats['queue_size']}"
                        )
                    else:
                        print(f"✅ 完成进度: {completed_count}/{len(all_article_data)}")
                else:
                    print(f"❌ 文章处理失败: {article_data['article']['title']}")
            except Exception as e:
                print(f"❌ 文章处理异常: {e}")

    return all_articles


def extract_from_keyword_async_multithread(
    keyword: str = "原油",
    pages_to_crawl: int = None,
    delay_between_requests: float = None,
    use_cookies: bool = True,
    output_formats: Optional[List[str]] = None,
    days_back: Optional[int] = None,
    hours_back: Optional[int] = None,
    qiniu_config: Optional[Dict[str, str]] = None,
    save_locally: bool = None,
    upload_to_qiniu: bool = None,
    max_crawl_workers: int = None,
    max_upload_workers: int = None,
) -> None:
    """
    异步多线程主函数 - 增强时间范围控制和日志记录

    Args:
        keyword: 搜索关键词
        pages_to_crawl: 爬取页数（默认从配置读取）
        delay_between_requests: 请求间延时（默认从配置读取）
        use_cookies: 是否使用Cookie
        output_formats: 输出格式列表（默认从配置读取）
        days_back: 向前追溯天数
        hours_back: 向前追溯小时数
        qiniu_config: 七牛云配置（默认从配置读取）
        save_locally: 是否本地保存（默认从配置读取）
        upload_to_qiniu: 是否上传七牛云（默认从配置读取）
        max_crawl_workers: 最大爬取线程数（默认从配置读取）
        max_upload_workers: 最大上传线程数（默认从配置读取）
    """
    # 从配置加载默认值
    settings = get_settings()

    if pages_to_crawl is None:
        pages_to_crawl = settings.crawler.default_pages
    if delay_between_requests is None:
        delay_between_requests = settings.crawler.default_delay
    if output_formats is None:
        output_formats = settings.output.default_formats.copy()
    if save_locally is None:
        save_locally = settings.output.save_locally
    if upload_to_qiniu is None:
        upload_to_qiniu = settings.output.upload_to_qiniu
    if max_crawl_workers is None:
        max_crawl_workers = settings.crawler.max_crawl_workers
    if max_upload_workers is None:
        max_upload_workers = settings.crawler.max_upload_workers
    if qiniu_config is None:
        qiniu_config = settings.get_qiniu_config()

    logger = IncrementalUpdateLogger(settings.crawler.log_file)
    logger.log_session_start(keyword, days_back=days_back, hours_back=hours_back)

    # 初始化上传器
    qiniu_uploader = None
    if qiniu_config and upload_to_qiniu:
        qiniu_uploader = AsyncMemoryQiniuUploader(
            qiniu_config["access_key"],
            qiniu_config["secret_key"],
            qiniu_config["bucket_name"],
            prefix=qiniu_config.get("prefix", "crawled_articles"),
            max_upload_workers=max_upload_workers,
        )
        qiniu_uploader.start_upload_workers()
        print("✅ 异步上传器初始化并启动成功")
    elif upload_to_qiniu and not qiniu_config:
        print("⚠️ 七牛云上传已启用，但未提供配置，跳过上传")
    else:
        print("⏸️ 七牛云上传已禁用")

    naming_system = UniversalNamingSystem(settings.crawler.project_code)
    converter = AsyncFormatConverter(
        base_dir=settings.crawler.base_dir,
        qiniu_uploader=qiniu_uploader,
        naming_system=naming_system,
        save_locally=save_locally,
        upload_to_qiniu=upload_to_qiniu,
    )

    cookies_manager = None
    if use_cookies:
        cookies_manager = OilChemCookiesManager(settings.crawler.cookies_file)
        if not cookies_manager.load_cookies():
            logger.log_error("Cookies加载失败")
            print(cookies_manager.get_export_instructions())
            if qiniu_uploader:
                qiniu_uploader.stop_upload_workers()
            return
        if not cookies_manager.validate_session():
            logger.log_error("Cookies验证失败")
            print(cookies_manager.get_export_instructions())
            if qiniu_uploader:
                qiniu_uploader.stop_upload_workers()
            return

    print(f"🚀 开始异步多线程爬取 '{keyword}' 相关文章...")
    _print_config(
        hours_back,
        days_back,
        output_formats,
        save_locally,
        upload_to_qiniu,
        max_crawl_workers,
        max_upload_workers,
        naming_system,
    )

    start_time = time.time()

    try:
        articles = crawl_articles_async_multithread(
            keyword=keyword,
            pages=pages_to_crawl,
            delay=delay_between_requests,
            cookies_manager=cookies_manager,
            output_formats=output_formats,
            days_back=days_back,
            hours_back=hours_back,
            converter=converter,
            max_crawl_workers=max_crawl_workers,
            max_upload_workers=max_upload_workers,
        )

        if qiniu_uploader and upload_to_qiniu:
            print("\n⏳ 爬取完成，等待上传队列清空...")
            qiniu_uploader.wait_for_completion()
        else:
            print("\n✅ 爬取完成")

        elapsed_time = time.time() - start_time

        if articles:
            count = save_results(articles, keyword, qiniu_uploader, save_locally)
            logger.log_articles_stats(articles)

            if qiniu_uploader and upload_to_qiniu:
                stats = qiniu_uploader.get_detailed_stats()
                print("\n📊 异步上传统计详情:")
                print(f"   总提交任务: {stats['total_submitted']}")
                print(f"   成功上传: {stats['total_success']}")
                print(f"   失败上传: {stats['total_failed']}")
                print(f"   文件类型分布: {stats.get('file_type_breakdown', {})}")

            print("\n=== 异步多线程爬取完成 ===")
            print(f"共爬取 {count} 篇文章")
            print(f"总耗时: {elapsed_time:.2f} 秒")
            print(f"平均每篇文章: {elapsed_time / count:.2f} 秒")
            logger.log_session_end(count, elapsed_time)
        else:
            print("❌ 没有爬取到任何文章")
            logger.log_error("没有爬取到任何文章")

    except Exception as e:
        error_msg = f"爬取过程发生异常: {str(e)}"
        print(f"❌ {error_msg}")
        logger.log_error(error_msg)
    finally:
        if qiniu_uploader and upload_to_qiniu:
            qiniu_uploader.stop_upload_workers()


def _print_config(
    hours_back,
    days_back,
    output_formats,
    save_locally,
    upload_to_qiniu,
    max_crawl_workers,
    max_upload_workers,
    naming_system,
):
    """打印配置信息"""
    if hours_back is not None:
        print(f"📅 时间范围: 最近 {hours_back} 小时")
    elif days_back is not None:
        print(f"📅 时间范围: 最近 {days_back} 天")
    else:
        print("📅 时间范围: 不限时间（所有数据）")
    print(f"📁 输出格式: {', '.join(output_formats)}")
    print(f"💾 本地保存: {'✅ 已启用' if save_locally else '❌ 已禁用'}")
    print(f"📤 七牛云上传: {'✅ 已启用' if upload_to_qiniu else '❌ 已禁用'}")
    print(f"🧵 爬取线程: {max_crawl_workers} 个")
    if upload_to_qiniu:
        print(f"📤 上传线程: {max_upload_workers} 个")
    print(f"📊 映射文件: {naming_system.mapping_file}")


def incremental_crawl(
    keyword: str,
    existing_ids: Union[Set[str], "ThreadSafeSet"],
    cookies_manager: Optional[OilChemCookiesManager] = None,
    converter: Optional[AsyncFormatConverter] = None,
    output_formats: Optional[List[str]] = None,
    max_pages: int = 3,
    early_stop_threshold: int = 10,
    delay: float = 1.0,
) -> CrawlResult:
    """
    增量爬取 - 只爬取新文章

    Args:
        keyword: 搜索关键词
        existing_ids: 已存在的文章ID集合（支持普通set或ThreadSafeSet，会被原地更新）
        cookies_manager: Cookie管理器
        converter: 格式转换器
        output_formats: 输出格式列表
        max_pages: 最大爬取页数
        early_stop_threshold: 连续遇到旧文章阈值，触发提前停止
        delay: 请求间延时

    Returns:
        CrawlResult: 爬取结果
    """
    if output_formats is None:
        output_formats = ["html", "word"]

    start_time = time.time()
    new_articles: List[Dict[str, Any]] = []
    skipped_count = 0
    failed_count = 0
    consecutive_old = 0

    # 获取 session
    session = None
    if cookies_manager and cookies_manager.session:
        session = cookies_manager.session

    print(f"🔍 开始增量爬取 '{keyword}'，已有 {len(existing_ids)} 篇文章记录")

    for page in range(1, max_pages + 1):
        print(f"📋 获取第 {page}/{max_pages} 页文章列表...")
        list_data = get_article_list(keyword, page_no=page, session=session)

        if not list_data:
            print(f"⚠️ 第 {page} 页没有数据")
            break

        articles = list_data.get("response", {}).get("list", [])
        if not articles:
            print(f"⚠️ 第 {page} 页文章列表为空")
            break

        print(f"📊 第 {page} 页找到 {len(articles)} 篇文章")

        for article in articles:
            article_id = str(article.get("articleId", "")).strip()

            # 检查是否已存在
            if article_id and article_id in existing_ids:
                skipped_count += 1
                consecutive_old += 1
                print(f"⏭️ 跳过已存在: {article.get('title', '')[:30]}...")

                # 提前停止检查
                if early_stop_threshold > 0 and consecutive_old >= early_stop_threshold:
                    print(f"🛑 连续遇到 {consecutive_old} 篇旧文章，提前停止")
                    elapsed_time = time.time() - start_time
                    return CrawlResult(
                        new_articles=new_articles,
                        skipped_count=skipped_count,
                        success_count=len(new_articles),
                        failed_count=failed_count,
                        elapsed_time=elapsed_time,
                    )
                continue

            # 重置连续旧文章计数
            consecutive_old = 0

            # 创建副本，将 article_id 追加到标题以避免 cleaned 文件名碰撞
            article_copy = dict(article)
            if article_id:
                original_title = article.get("title", "")
                article_copy["title"] = (
                    f"{original_title}_{article_id}" if original_title else article_id
                )

            # 爬取新文章
            article_data = {
                "article": article_copy,
                "index": len(new_articles) + 1,
                "total": 0,  # 增量模式不知道总数
            }

            result = crawl_article_worker_async(
                article_data, session, output_formats, converter, delay
            )

            if result:
                new_articles.append(result)
                # 更新已存在集合
                if article_id:
                    existing_ids.add(article_id)
                print(f"✅ 新增文章: {article.get('title', '')[:30]}...")
            else:
                failed_count += 1
                print(f"❌ 爬取失败: {article.get('title', '')[:30]}...")

    elapsed_time = time.time() - start_time
    print(
        f"\n📊 增量爬取完成: 新增 {len(new_articles)} 篇, "
        f"跳过 {skipped_count} 篇, 失败 {failed_count} 篇, "
        f"耗时 {elapsed_time:.2f}秒"
    )

    return CrawlResult(
        new_articles=new_articles,
        skipped_count=skipped_count,
        success_count=len(new_articles),
        failed_count=failed_count,
        elapsed_time=elapsed_time,
    )
