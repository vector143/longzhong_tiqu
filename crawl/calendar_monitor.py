#!/usr/bin/env python
"""
华尔街见闻 - 财经日历监控脚本

监控财经日历数据，支持按地区、重要性、类型筛选
默认监控：中国、日本、欧元区、美国的2星及以上宏观数据
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from crawl.wallstreetcn_calendar import (
    WallStreetCNCalendarCrawler,
    WallStreetCNCalendarMonitor,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / "calendar"


def _positive_int(value: str) -> int:
    """argparse 正整数类型"""
    import argparse

    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("必须是整数") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("必须是正整数")
    return parsed


def save_to_json(
    items,
    output_dir: Optional[str] = None,
):
    """保存财经日历到JSON文件"""
    if output_dir is None:
        output_dir = str(DEFAULT_OUTPUT_DIR)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for item in items:
        try:
            # 文件命名
            item_id = item.get("id", "unknown")
            country = item.get("country_id", "XX")
            date = datetime.now().strftime("%Y%m%d")
            filename = f"Calendar_{country}_{date}_{item_id}.json"
            filepath = output_path / filename

            # 保存JSON
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(item, f, ensure_ascii=False, indent=2)

            print(f"   ✅ 已保存: {filename}")

        except Exception as e:
            print(f"   ❌ 保存失败: {e}")


def on_new_items(items, output_dir: Optional[str] = None):
    """处理新日历事件的回调函数"""
    if not items:
        return

    print(f"\n{'='*60}")
    print(f"📅 收到 {len(items)} 个新日历事件")
    print(f"{'='*60}")

    # 显示事件摘要
    for i, item in enumerate(items, 1):
        title = item.get("title", "")
        country = item.get("country", "")
        importance = item.get("importance", 0)
        stars = "⭐" * importance

        print(f"\n{i}. [{country}] {stars} {title}")

        # 显示数据
        if item.get("actual"):
            print(f"   实际值: {item.get('actual')} {item.get('unit', '')}")
        if item.get("forecast"):
            print(f"   预测值: {item.get('forecast')} {item.get('unit', '')}")
        if item.get("previous"):
            print(f"   前值: {item.get('previous')} {item.get('unit', '')}")

        # 显示前瞻
        foresight = item.get("foresight", "")
        if foresight:
            preview = foresight[:100]
            print(f"   前瞻: {preview}...")

    # 保存到文件
    print("\n💾 保存日历事件...")
    save_to_json(items, output_dir=output_dir)
    print(f"{'='*60}\n")


def fetch_mode(
    start_date=None,
    end_date=None,
    countries=None,
    min_importance=2,
    calendar_types=None,
    output_dir: Optional[str] = None,
):
    """单次抓取模式"""
    crawler = WallStreetCNCalendarCrawler()

    countries = countries or ["中国", "美国", "日本", "欧元区"]
    calendar_types = calendar_types or ["宏观"]

    print("🔍 抓取财经日历数据...")
    print(f"   地区: {', '.join(countries)}")
    print(f"   重要性: {min_importance}星及以上")
    print(f"   类型: {', '.join(calendar_types)}")
    if start_date:
        print(f"   开始日期: {start_date}")
    if end_date:
        print(f"   结束日期: {end_date}")

    items = crawler.fetch_and_parse(
        start_date=start_date,
        end_date=end_date,
        countries=countries,
        min_importance=min_importance,
        calendar_types=calendar_types,
    )

    if items:
        print(f"✅ 获取到 {len(items)} 个日历事件")
        on_new_items(items, output_dir=output_dir)
    else:
        print("❌ 未获取到日历事件")


def monitor_mode(
    interval=3600,
    countries=None,
    min_importance=2,
    calendar_types=None,
    output_dir: Optional[str] = None,
):
    """监控模式"""
    crawler = WallStreetCNCalendarCrawler()
    monitor = WallStreetCNCalendarMonitor(
        crawler=crawler,
        poll_interval=interval,
        countries=countries or ["中国", "美国", "日本", "欧元区"],
        min_importance=min_importance,
        calendar_types=calendar_types or ["宏观"],
    )

    print("🚀 启动财经日历监控")
    monitor.start(lambda items: on_new_items(items, output_dir=output_dir))


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="华尔街见闻 - 财经日历监控",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 单次抓取（默认：中国、美国、日本、欧元区，2星及以上，宏观）
  python calendar_monitor.py --fetch

  # 自定义地区和重要性
  python calendar_monitor.py --fetch --countries 中国 美国 --importance 3

  # 指定日期范围
  python calendar_monitor.py --fetch --start 2026-02-10 --end 2026-02-17

  # 监控模式（每小时检查一次）
  python calendar_monitor.py --monitor --interval 3600

  # 只监控3星事件
  python calendar_monitor.py --fetch --importance 3
        """,
    )

    parser.add_argument(
        "--fetch", "-f", action="store_true", help="单次抓取模式（默认）"
    )

    parser.add_argument("--monitor", "-m", action="store_true", help="持续监控模式")

    parser.add_argument(
        "--interval",
        "-i",
        type=_positive_int,
        default=3600,
        help="监控轮询间隔（秒） (默认: 3600)",
    )

    parser.add_argument(
        "--countries",
        "-c",
        nargs="+",
        default=["中国", "美国", "日本", "欧元区"],
        help="监控的国家/地区",
    )

    parser.add_argument(
        "--importance",
        type=int,
        default=2,
        choices=[1, 2, 3, 4, 5],
        help="最低重要性（1-5星） (默认: 2)",
    )

    parser.add_argument(
        "--types",
        "-t",
        nargs="+",
        default=["宏观"],
        help="日历类型 (默认: 宏观)",
    )

    parser.add_argument("--start", help="开始日期 (YYYY-MM-DD)")

    parser.add_argument("--end", help="结束日期 (YYYY-MM-DD)")

    parser.add_argument(
        "--output",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help="输出目录 (默认: 项目根目录/output/calendar)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("🎯 华尔街见闻 - 财经日历监控")
    print("=" * 60)
    print(f"监控地区: {', '.join(args.countries)}")
    print(f"最低重要性: {args.importance}星")
    print(f"日历类型: {', '.join(args.types)}")
    if args.monitor:
        print(f"轮询间隔: {args.interval} 秒")
        print("按 Ctrl+C 停止监控")
    print("=" * 60)
    print()

    if args.monitor:
        monitor_mode(
            interval=args.interval,
            countries=args.countries,
            min_importance=args.importance,
            calendar_types=args.types,
            output_dir=args.output,
        )
    else:
        fetch_mode(
            start_date=args.start,
            end_date=args.end,
            countries=args.countries,
            min_importance=args.importance,
            calendar_types=args.types,
            output_dir=args.output,
        )


if __name__ == "__main__":
    main()
