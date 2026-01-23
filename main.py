"""
隆众资讯爬虫 - 兼容入口

实际实现已拆分到各子模块，此文件保持向后兼容。
新代码请使用子模块的直接导入方式。
"""

# === 兼容性导出 ===
# 保持旧的 import 方式可用：from main import XXX

from config import Settings, get_settings
from core import IncrementalUpdateLogger, UniversalNamingSystem
from clients import OilChemCookiesManager, AsyncMemoryQiniuUploader, UploadTask
from crawl import get_article_list, extract_article_content, crawl_article_worker_async
from crawl.pipeline import (
    crawl_articles_async_multithread,
    extract_from_keyword_async_multithread,
)
from convert import (
    html_table_to_markdown,
    html_to_markdown,
    html_table_to_data,
    html_to_text_and_tables,
    AsyncFormatConverter,
)
from storage import save_results
from utils import format_timestamp

# === 公共API ===
__all__ = [
    # 配置
    "Settings",
    "get_settings",
    # 核心类
    "IncrementalUpdateLogger",
    "UniversalNamingSystem",
    # 客户端
    "OilChemCookiesManager",
    "AsyncMemoryQiniuUploader",
    "UploadTask",
    # 爬虫
    "get_article_list",
    "extract_article_content",
    "crawl_article_worker_async",
    "crawl_articles_async_multithread",
    "extract_from_keyword_async_multithread",
    # 转换
    "html_table_to_markdown",
    "html_to_markdown",
    "html_table_to_data",
    "html_to_text_and_tables",
    "AsyncFormatConverter",
    # 存储
    "save_results",
    # 工具
    "format_timestamp",
]


def main():
    """CLI主入口函数 - 使用配置系统默认值"""
    # 所有参数从配置系统读取，仅覆盖keyword
    extract_from_keyword_async_multithread(keyword="原油")


if __name__ == "__main__":
    main()
