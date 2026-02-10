#!/usr/bin/env python
"""
华尔街见闻 - 多频道商品监控脚本

同时监控所有商品相关的频道：
- commodity-channel (大宗商品)
- oil-channel (原油)
- gold-channel (黄金)
- gold-forex-channel (黄金外汇)
- goldc-channel (黄金C)

支持单次抓取模式（--fetch）
"""

import sys
import threading
import time
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from crawl.wallstreetcn import WallStreetCNLiveCrawler, WallStreetCNMonitor
from crawl.wallstreetcn_formatter import WallStreetCNFormatter
import json
from datetime import datetime

# 商品相关的所有频道
COMMODITY_CHANNELS = [
    "commodity-channel",  # 大宗商品
    "oil-channel",  # 原油
    "gold-channel",  # 黄金
    "gold-forex-channel",  # 黄金外汇
    "goldc-channel",  # 黄金C
]


def save_to_json(items, output_dir="articles/wallstreetcn"):
    """保存快讯到JSON文件（隆众格式）"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    formatter = WallStreetCNFormatter()

    for item in items:
        try:
            # 转换为隆众格式
            standard_data = formatter.format_to_standard(item)

            # 文件命名
            item_id = standard_data.get("article_id", "unknown")
            date = standard_data.get("date", "").replace("-", "")
            if not date:
                date = datetime.now().strftime("%Y%m%d")
            filename = f"WSJ_{date}_{item_id}.json"
            filepath = output_path / filename

            # 保存JSON
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(standard_data, f, ensure_ascii=False, indent=2)

            print(f"   ✅ 已保存: {filename}")

        except Exception as e:
            print(f"   ❌ 保存失败: {e}")


def on_new_items(channel_name, items):
    """处理新快讯的回调函数"""
    if not items:
        return

    print(f"\n{'='*60}")
    print(f"📰 [{channel_name}] 收到 {len(items)} 条新快讯")
    print(f"{'='*60}")

    # 显示快讯摘要
    for i, item in enumerate(items, 1):
        title = item.get("title", "快讯") or "快讯"
        print(f"\n{i}. [{item.get('display_time_str')}] {title}")
        content_preview = item.get("content_text", "")[:100]
        print(f"   {content_preview}...")
        print(f"   🔗 {item.get('url')}")

    # 保存到文件
    print("\n💾 保存快讯...")
    save_to_json(items)
    print(f"{'='*60}\n")


def monitor_channel(channel_name, interval=30, important_only=False):
    """监控单个频道"""
    crawler = WallStreetCNLiveCrawler()
    monitor = WallStreetCNMonitor(
        crawler=crawler,
        poll_interval=interval,
        channel=channel_name,
        important_only=important_only,
    )

    def callback(items):
        on_new_items(channel_name, items)

    print(f"🚀 启动 {channel_name} 监控")
    monitor.start(callback=callback)


def fetch_mode(channels, limit=20, important_only=False):
    """单次抓取多个频道"""
    crawler = WallStreetCNLiveCrawler()
    filter_msg = "重要快讯" if important_only else "全部快讯"
    for channel in channels:
        print(f"🔍 抓取 {channel} 频道最新 {limit} 条快讯（{filter_msg}）...")
        items = crawler.fetch_incremental(
            channel=channel, limit=limit, important_only=important_only
        )
        if items:
            print(f"✅ {channel} 获取到 {len(items)} 条快讯")
            on_new_items(channel, items)
        else:
            print(f"❌ {channel} 未获取到快讯")


def main():
    """主函数：同时监控所有商品相关频道"""
    import argparse

    parser = argparse.ArgumentParser(
        description="华尔街见闻 - 多频道商品监控",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 监控所有商品频道（默认）
  python multi_commodity_monitor.py

  # 只监控重要快讯
  python multi_commodity_monitor.py --important

  # 自定义轮询间隔
  python multi_commodity_monitor.py --interval 60

  # 只监控特定频道
  python multi_commodity_monitor.py --channels commodity-channel oil-channel

  # 单次抓取最新20条
  python multi_commodity_monitor.py --fetch --limit 20
        """,
    )

    parser.add_argument(
        "--interval", "-i", type=int, default=30, help="轮询间隔（秒） (默认: 30)"
    )

    parser.add_argument("--important", action="store_true", help="只监控重要快讯")

    parser.add_argument("--fetch", "-f", action="store_true", help="单次抓取模式")

    parser.add_argument(
        "--limit", "-l", type=int, default=20, help="单次抓取数量 (默认: 20)"
    )

    parser.add_argument(
        "--channels", nargs="+", default=COMMODITY_CHANNELS, help="要监控的频道列表"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("🎯 华尔街见闻 - 多频道商品监控")
    print("=" * 60)
    print(f"监控频道: {len(args.channels)} 个")
    for channel in args.channels:
        print(f"  - {channel}")
    print(f"轮询间隔: {args.interval} 秒")
    print(f"过滤模式: {'重要快讯' if args.important else '全部快讯'}")
    print("按 Ctrl+C 停止监控")
    print("=" * 60)
    print()

    if args.fetch:
        fetch_mode(args.channels, limit=args.limit, important_only=args.important)
        return

    # 创建多个监控线程
    threads = []
    for channel in args.channels:
        t = threading.Thread(
            target=monitor_channel,
            args=(channel, args.interval, args.important),
            daemon=True,
        )
        t.start()
        threads.append(t)
        time.sleep(1)  # 错开启动时间

    # 等待所有线程
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\n\n⏹️ 监控已停止")
        sys.exit(0)


if __name__ == "__main__":
    main()
