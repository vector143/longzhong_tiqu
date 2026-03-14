#!/usr/bin/env python
"""
Investing.com 爬虫使用示例

演示如何在代码中使用爬虫
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from crawl.investing_crawler import InvestingCommodityNewsCrawler
from crawl.investing_formatter import InvestingFormatter


def example_1_fetch_news_list():
    """示例1: 获取新闻列表"""
    print("=" * 80)
    print("示例1: 获取新闻列表")
    print("=" * 80)

    crawler = InvestingCommodityNewsCrawler()
    result = crawler.fetch_news_list(page=1, delay=2.0)

    if result["success"]:
        news_list = result["data"]
        print(f"✅ 成功获取 {len(news_list)} 条新闻\n")

        # 显示前3条
        for i, news in enumerate(news_list[:3], 1):
            print(f"{i}. {news['title']}")
            print(f"   URL: {news['url']}")
            print(f"   时间: {news['publish_time']}")
            print()
    else:
        print(f"❌ 获取失败: {result['error']}")


def example_2_fetch_article_content():
    """示例2: 获取文章详细内容"""
    print("=" * 80)
    print("示例2: 获取文章详细内容")
    print("=" * 80)

    crawler = InvestingCommodityNewsCrawler()

    # 先获取列表
    result = crawler.fetch_news_list(page=1, delay=2.0)
    if not result["success"] or not result["data"]:
        print("❌ 无法获取新闻列表")
        return

    # 获取第一篇文章的详细内容
    first_article = result["data"][0]
    print(f"正在获取: {first_article['title']}\n")

    content = crawler.fetch_article_content(first_article["url"])

    if content["success"]:
        print(f"标题: {content['title']}")
        print(f"作者: {content['author']}")
        print(f"时间: {content['publish_time']}")
        print("\n内容预览:")
        print(content["content"][:300] + "...")
    else:
        print(f"❌ 获取失败: {content['error']}")


def example_3_format_data():
    """示例3: 格式化数据"""
    print("=" * 80)
    print("示例3: 格式化数据为标准格式")
    print("=" * 80)

    crawler = InvestingCommodityNewsCrawler()
    formatter = InvestingFormatter()

    # 获取新闻
    result = crawler.fetch_news_list(page=1, delay=2.0)
    if not result["success"] or not result["data"]:
        print("❌ 无法获取新闻列表")
        return

    # 格式化第一条新闻
    first_article = result["data"][0]
    standard_data = formatter.format_to_standard(first_article)

    print("标准格式数据:")
    print(f"  文章ID: {standard_data['article_id']}")
    print(f"  标题: {standard_data['title']}")
    print(f"  日期: {standard_data['date']}")
    print(f"  时间: {standard_data['time']}")
    print(f"  来源: {standard_data['source']}")
    print(f"  分类: {standard_data['category']}")
    print(f"  URL: {standard_data['url']}")


def example_4_multiple_pages():
    """示例4: 爬取多页"""
    print("=" * 80)
    print("示例4: 爬取多页新闻")
    print("=" * 80)

    crawler = InvestingCommodityNewsCrawler()
    all_news = crawler.fetch_multiple_pages(max_pages=2, delay=2.0)

    print(f"✅ 共获取 {len(all_news)} 条新闻")

    # 按日期统计
    from collections import Counter

    dates = [news.get("publish_time", "")[:10] for news in all_news]
    date_counts = Counter(dates)

    print("\n按日期统计:")
    for date, count in sorted(date_counts.items(), reverse=True):
        print(f"  {date}: {count} 条")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Investing.com 爬虫使用示例")
    parser.add_argument(
        "--example",
        "-e",
        type=int,
        choices=[1, 2, 3, 4],
        default=1,
        help="选择示例 (1-4)",
    )

    args = parser.parse_args()

    examples = {
        1: example_1_fetch_news_list,
        2: example_2_fetch_article_content,
        3: example_3_format_data,
        4: example_4_multiple_pages,
    }

    examples[args.example]()
