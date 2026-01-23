"""
网络请求模块

提供文章列表获取和正文内容提取功能。
"""

import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from utils.time_utils import format_timestamp


def get_article_list(
    keyword: str,
    page_no: int = 1,
    page_size: int = 10,
    session: Optional[requests.Session] = None,
    days_back: Optional[int] = None,
    hours_back: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    获取文章列表 - 支持时间范围控制

    Args:
        keyword: 搜索关键词
        page_no: 页码
        page_size: 每页数量
        session: 可选的requests会话
        days_back: 向前追溯天数
        hours_back: 向前追溯小时数

    Returns:
        文章列表数据字典，失败返回None
    """
    url = "https://search.oilchem.net/article/search"
    params = {
        "keyword": keyword,
        "pageNo": page_no,
        "pageSize": page_size,
        "channelIds": "",
        "highlightFields": "title,content",
    }

    # 时间范围计算
    if hours_back is not None:
        end_time = int(time.time() * 1000)
        start_time = int(end_time - (hours_back * 60 * 60 * 1000))
        params["startTime"] = str(start_time)
        params["endTime"] = str(end_time)
        print(
            f"⏰ 时间范围: 最近 {hours_back} 小时 "
            f"({format_timestamp(start_time)} 至 {format_timestamp(end_time)})"
        )
    elif days_back is not None:
        end_time = int(time.time() * 1000)
        start_time = int(end_time - (days_back * 24 * 60 * 60 * 1000))
        params["startTime"] = str(start_time)
        params["endTime"] = str(end_time)
        print(
            f"⏰ 时间范围: 最近 {days_back} 天 "
            f"({format_timestamp(start_time)} 至 {format_timestamp(end_time)})"
        )

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": f"https://search.oilchem.net/article.html?keyword={quote(keyword)}",
    }

    try:
        if session:
            response = session.get(url, params=params, headers=headers)
        else:
            response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"获取文章列表失败: {e}")
        return None


def extract_article_content(
    article_url: str, session: Optional[requests.Session] = None
) -> Dict[str, Any]:
    """
    提取文章正文内容

    Args:
        article_url: 文章URL
        session: 可选的requests会话

    Returns:
        包含html_content, images_data, title的字典
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    try:
        # URL规范化
        if article_url.startswith("//"):
            article_url = "https:" + article_url
        elif article_url.startswith("/"):
            article_url = "https://www.oilchem.net" + article_url

        print(f"📖 正在提取: {article_url}")

        if session:
            response = session.get(article_url, headers=headers, timeout=10)
        else:
            response = requests.get(article_url, headers=headers, timeout=10)

        response.raise_for_status()
        response.encoding = "utf-8"

        # 检查登录状态
        if "立即登录" in response.text:
            print("❌ 需要登录：检测到'立即登录'提示")
            return {
                "html_content": "需要登录才能访问全文",
                "images_data": [],
                "title": "需要登录",
            }

        soup = BeautifulSoup(response.text, "html.parser")

        # 内容选择器
        content_selectors = [
            ".article-content",
            ".content",
            ".main-content",
            ".detail-content",
            ".article-detail",
            ".news-content",
            '[class*="content"]',
            '[class*="article"]',
            ".text",
        ]

        content_elem = None
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                break

        if not content_elem:
            content_elem = soup.find("body")

        if content_elem:
            content_copy = BeautifulSoup(str(content_elem), "html.parser")

            # 清理无关元素
            clean_selectors = [
                "script",
                "style",
                "nav",
                "header",
                "footer",
                ".ad",
                ".ads",
                ".advertisement",
                ".sidebar",
                ".side-bar",
                ".menu",
                ".navigation",
                ".nav",
                ".comment",
                ".comments",
                ".share",
                ".social",
                ".breadcrumb",
                ".breadcrumbs",
                ".pagination",
                ".page-nav",
                ".related",
                ".recommend",
                ".popup",
                ".modal",
                ".toolbar",
                ".tools",
                ".widget",
                ".plugin",
                ".banner",
                ".promotion",
                '[class*="ad"]',
                '[class*="banner"]',
                '[class*="menu"]',
                '[class*="nav"]',
                '[id*="ad"]',
            ]

            for clean_selector in clean_selectors:
                for elem in content_copy.select(clean_selector):
                    elem.decompose()

            # 提取标题
            title_elem = content_copy.find(["h1", "h2"]) or soup.find("title")
            title = title_elem.get_text(strip=True) if title_elem else "无标题"

            # 提取图片信息
            images_data: List[Dict[str, Any]] = []
            for img_idx, img in enumerate(content_copy.find_all("img")):
                img_src = img.get("src")
                if img_src:
                    images_data.append(
                        {"src": img_src, "alt": img.get("alt", ""), "index": img_idx}
                    )

            return {
                "html_content": str(content_copy),
                "images_data": images_data,
                "title": title,
            }

        return {"html_content": "正文提取失败", "images_data": [], "title": "提取失败"}

    except Exception as e:
        print(f"❌ 提取正文失败 {article_url}: {e}")
        return {
            "html_content": f"提取失败: {str(e)}",
            "images_data": [],
            "title": "提取失败",
        }
