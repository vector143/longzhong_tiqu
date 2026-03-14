#!/usr/bin/env python
"""
Investing.com 商品新闻爬虫 - 运行脚本

使用示例:
  # 爬取前3页新闻（仅列表）
  python investing_runner.py --pages 3

  # 爬取前2页新闻并获取详细内容
  python investing_runner.py --pages 2 --fetch-content

  # 自定义延迟和输出目录
  python investing_runner.py --pages 5 --delay 3 --output ./output
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from crawl.investing_crawler import InvestingCommodityNewsCrawler
from crawl.investing_formatter import InvestingFormatter


def save_to_json(items, output_dir, channel="commodities", fetch_content=False):
    """
    保存新闻到JSON文件

    Args:
        items: 新闻列表
        output_dir: 输出目录
        channel: 频道名称
        fetch_content: 是否获取了详细内容
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    formatter = InvestingFormatter()
    saved_count = 0

    for item in items:
        try:
            # 转换为标准格式
            standard_data = formatter.format_to_standard(item)

            # 文件命名（包含频道信息）
            article_id = standard_data.get("article_id", "unknown")
            date = standard_data.get("date", "").replace("-", "")
            if not date:
                date = datetime.now().strftime("%Y%m%d")

            # 频道前缀
            channel_prefix = channel.upper().replace("-", "_")
            filename = f"INVESTING_{channel_prefix}_{date}_{article_id}.json"
            filepath = output_path / filename

            # 保存JSON
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(standard_data, f, ensure_ascii=False, indent=2)

            saved_count += 1
            print(f"   ✅ 已保存: {filename}")

        except Exception as e:
            print(f"   ❌ 保存失败: {e}")

    return saved_count


def main():
    parser = argparse.ArgumentParser(
        description="Investing.com 新闻爬虫（支持多频道）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 爬取商品新闻
  python investing_runner.py --channel commodities --pages 3

  # 爬取经济指标新闻，限制10条
  python investing_runner.py --channel economic-indicators --pages 2 --limit 10

  # 爬取经济新闻并获取详细内容
  python investing_runner.py --channel economy --pages 2 --fetch-content

  # 爬取所有频道，每个频道限制20条
  python investing_runner.py --all-channels --pages 2 --limit 20
        """,
    )

    parser.add_argument(
        "--channel",
        choices=["commodities", "economic-indicators", "economy"],
        default="commodities",
        help="新闻频道 (默认: commodities)",
    )

    parser.add_argument(
        "--all-channels",
        "-a",
        action="store_true",
        help="爬取所有频道",
    )

    parser.add_argument(
        "--pages",
        "-p",
        type=int,
        default=3,
        help="爬取页数 (默认: 3)",
    )

    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=None,
        help="限制每个频道爬取的新闻数量（不设置则爬取所有）",
    )

    parser.add_argument(
        "--delay",
        "-d",
        type=float,
        default=2.0,
        help="请求延迟（秒）(默认: 2.0)",
    )

    parser.add_argument(
        "--fetch-content",
        "-f",
        action="store_true",
        help="是否获取文章详细内容（会增加爬取时间）",
    )

    parser.add_argument(
        "--output",
        "-o",
        default="./output",
        help="输出目录 (默认: ./output)",
    )

    parser.add_argument(
        "--proxy",
        "-x",
        default=None,
        help="代理地址 (例如: http://127.0.0.1:7890 或 socks5://127.0.0.1:1080)",
    )

    args = parser.parse_args()

    # 确定要爬取的频道
    channels = (
        ["commodities", "economic-indicators", "economy"]
        if args.all_channels
        else [args.channel]
    )

    print("=" * 80)
    print("🚀 Investing.com 新闻爬虫")
    print("=" * 80)
    print(f"📺 频道: {', '.join(channels)}")
    print(f"📄 爬取页数: {args.pages}")
    if args.limit:
        print(f"🔢 数量限制: 每个频道 {args.limit} 条")
    print(f"⏱️  请求延迟: {args.delay} 秒")
    print(f"📖 获取详细内容: {'是' if args.fetch_content else '否'}")
    print(f"💾 输出目录: {args.output}")
    if args.proxy:
        print(f"🌐 代理服务器: {args.proxy}")
    print("=" * 80)
    print()

    total_news = 0
    total_saved = 0

    for channel in channels:
        print(f"\n{'='*80}")
        print(f"📺 正在爬取频道: {channel}")
        print(f"{'='*80}\n")

        # 初始化爬虫
        crawler = InvestingCommodityNewsCrawler(channel=channel, proxy=args.proxy)

        # 获取新闻列表
        print("📋 开始获取新闻列表...")
        all_news = crawler.fetch_multiple_pages(max_pages=args.pages, delay=args.delay)

        if not all_news:
            print(f"❌ 频道 {channel} 未获取到任何新闻")
            continue

        # 应用数量限制
        if args.limit and len(all_news) > args.limit:
            print(f"📊 获取到 {len(all_news)} 条新闻，限制为 {args.limit} 条")
            all_news = all_news[: args.limit]
        else:
            print(f"\n✅ 共获取 {len(all_news)} 条新闻")

        # 如果需要获取详细内容
        if args.fetch_content:
            print("\n📖 开始获取文章详细内容...")
            for i, news_item in enumerate(all_news, 1):
                print(f"\n[{i}/{len(all_news)}] {news_item.get('title', '')[:50]}...")

                content_result = crawler.fetch_article_content(news_item["url"])

                if content_result["success"]:
                    # 更新新闻项
                    news_item["content"] = content_result["content"]
                    news_item["html_content"] = content_result["html_content"]
                    if content_result["publish_time"]:
                        news_item["publish_time"] = content_result["publish_time"]
                    if content_result["author"]:
                        news_item["author"] = content_result["author"]
                    print("   ✅ 内容获取成功")
                else:
                    print(f"   ⚠️ 内容获取失败: {content_result['error']}")

                # 添加延迟
                if i < len(all_news):
                    import time

                    time.sleep(args.delay)

        # 保存结果
        print("\n💾 保存新闻到文件...")
        saved_count = save_to_json(all_news, args.output, channel, args.fetch_content)

        total_news += len(all_news)
        total_saved += saved_count

        print(f"\n✅ 频道 {channel} 完成: {len(all_news)} 条新闻, {saved_count} 个文件")

    print("\n" + "=" * 80)
    print("✅ 全部爬取完成！")
    print(f"📊 总计: {total_news} 条新闻")
    print(f"💾 已保存: {total_saved} 个文件")
    print(f"📁 保存位置: {args.output}")
    print("=" * 80)


if __name__ == "__main__":
    main()
