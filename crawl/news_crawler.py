#!/usr/bin/env python
"""
华尔街见闻 - 实时新闻爬虫（推荐使用）

获取华尔街见闻的实时快讯，支持按频道、重要性筛选
这是获取最新新闻的正确方式
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from crawl.multi_commodity_monitor import fetch_mode

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="华尔街见闻 - 实时新闻爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 获取全球频道最新20条新闻
  python news_crawler.py --channel global-channel --limit 20

  # 获取多个频道的新闻
  python news_crawler.py --channels global-channel commodity-channel --limit 10

  # 只获取重要新闻（2星及以上）
  python news_crawler.py --channel global-channel --important --limit 20

  # 获取中国相关的新闻
  python news_crawler.py --channel a-stock-channel --limit 20
        """,
    )

    parser.add_argument(
        "--channel",
        default="global-channel",
        help="频道名称 (默认: global-channel)",
    )

    parser.add_argument(
        "--channels",
        nargs="+",
        help="多个频道名称",
    )

    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=20,
        help="获取数量 (默认: 20)",
    )

    parser.add_argument(
        "--important",
        action="store_true",
        help="只获取重要新闻（2星及以上）",
    )

    args = parser.parse_args()

    # 确定要爬取的频道
    channels = args.channels if args.channels else [args.channel]

    print("=" * 60)
    print("🎯 华尔街见闻 - 实时新闻爬虫")
    print("=" * 60)
    print(f"频道: {', '.join(channels)}")
    print(f"数量: {args.limit}")
    print(f"过滤: {'重要新闻' if args.important else '全部新闻'}")
    print("=" * 60)
    print()

    # 调用抓取函数
    fetch_mode(
        channels=channels,
        limit=args.limit,
        important_only=args.important,
    )

    print("\n✅ 抓取完成！")
    print("数据保存在: output/report/cleaned/")
