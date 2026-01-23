#!/usr/bin/env python
"""
隆众资讯爬虫 - 统一运行入口

使用方式：
    # 爬取最近2小时文章后启动监控
    python run.py --keyword 原油 --hours 2 --monitor

    # 只爬取，不监控
    python run.py --keyword 原油 --hours 2

    # 只启动监控
    python run.py --keyword 原油 --monitor

    # 爬取最近1天的文章
    python run.py --keyword 原油 --days 1

    # 清理所有历史记录
    python run.py --clean
"""

import argparse
import sys
from pathlib import Path


def clean_all_data(force: bool = False) -> None:
    """
    清理所有爬取历史数据

    Args:
        force: 是否跳过确认
    """
    dirs_to_clean = [
        "articles/json",
        "articles/markdown",
        "articles/html",
        "articles/word",
        "output/report/cleaned",
    ]

    files_to_clean = [
        "OIL_filename_mapping.csv",
        "原油_articles_summary.csv",
        "原油_articles_with_content.json",
    ]

    # 统计要删除的内容
    total_files = 0
    for dir_path in dirs_to_clean:
        p = Path(dir_path)
        if p.exists():
            total_files += len(list(p.glob("*")))

    for file_path in files_to_clean:
        if Path(file_path).exists():
            total_files += 1

    if total_files == 0:
        print("✅ 没有需要清理的数据")
        return

    print("⚠️  将删除以下数据:")
    print("   - articles/ 下所有文件")
    print("   - output/report/cleaned/ 下所有文件")
    print("   - 映射文件和汇总文件")
    print(f"   共计约 {total_files} 个文件")

    if not force:
        confirm = input("\n确认删除? [y/N]: ").strip().lower()
        if confirm != "y":
            print("❌ 已取消")
            return

    # 执行清理
    for dir_path in dirs_to_clean:
        p = Path(dir_path)
        if p.exists():
            for f in p.glob("*"):
                if f.is_file():
                    f.unlink()
            print(f"   🗑️  已清理 {dir_path}/")

    for file_path in files_to_clean:
        p = Path(file_path)
        if p.exists():
            p.unlink()
            print(f"   🗑️  已删除 {file_path}")

    # 清理其他可能的汇总文件
    for csv_file in Path(".").glob("*_articles_summary.csv"):
        csv_file.unlink()
        print(f"   🗑️  已删除 {csv_file}")

    for json_file in Path(".").glob("*_articles_with_content.json"):
        json_file.unlink()
        print(f"   🗑️  已删除 {json_file}")

    print("\n✅ 清理完成")


def main():
    parser = argparse.ArgumentParser(
        description="隆众资讯爬虫 - 统一运行入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py --keyword 原油 --hours 2 --monitor   # 爬取2小时内文章后监控
  python run.py --keyword 原油 --days 1              # 爬取最近1天文章
  python run.py --keyword 原油 --monitor             # 直接启动监控
  python run.py --keyword 原油 --pages 5             # 爬取5页文章
  python run.py --clean                              # 清理所有历史数据
  python run.py --clean --force                      # 强制清理（无需确认）
        """,
    )

    parser.add_argument(
        "--keyword", "-k", type=str, default="原油", help="搜索关键词 (默认: 原油)"
    )
    parser.add_argument("--hours", type=int, default=None, help="爬取最近N小时的文章")
    parser.add_argument("--days", type=int, default=None, help="爬取最近N天的文章")
    parser.add_argument("--pages", "-p", type=int, default=5, help="爬取页数 (默认: 5)")
    parser.add_argument(
        "--monitor", "-m", action="store_true", help="爬取完成后启动实时监控"
    )
    parser.add_argument(
        "--interval", "-i", type=int, default=10, help="监控轮询间隔(分钟) (默认: 10)"
    )
    parser.add_argument(
        "--monitor-only", action="store_true", help="跳过初始爬取，直接启动监控"
    )
    parser.add_argument("--clean", action="store_true", help="清理所有历史爬取数据")
    parser.add_argument(
        "--force", "-f", action="store_true", help="强制执行（跳过确认）"
    )

    args = parser.parse_args()

    # 清理模式
    if args.clean:
        clean_all_data(force=args.force)
        return

    # 如果只启动监控
    if args.monitor_only:
        print(f"🚀 直接启动监控模式 (关键词: {args.keyword})")
        from monitor.runner import run_monitor

        sys.exit(
            run_monitor(["--keyword", args.keyword, "--interval", str(args.interval)])
        )

    # 执行初始爬取
    if args.hours or args.days or (not args.monitor):
        print("=" * 50)
        print(f"🔍 开始爬取 '{args.keyword}' 相关文章")
        if args.hours:
            print(f"   时间范围: 最近 {args.hours} 小时")
        elif args.days:
            print(f"   时间范围: 最近 {args.days} 天")
        print(f"   爬取页数: {args.pages}")
        print("=" * 50)

        from crawl.pipeline import extract_from_keyword_async_multithread

        extract_from_keyword_async_multithread(
            keyword=args.keyword,
            hours_back=args.hours,
            days_back=args.days,
            pages_to_crawl=args.pages,
        )
        print("\n✅ 初始爬取完成")

    # 启动监控
    if args.monitor:
        print("\n" + "=" * 50)
        print("🖥️ 启动实时监控模式")
        print("=" * 50)
        from monitor.runner import run_monitor

        sys.exit(
            run_monitor(["--keyword", args.keyword, "--interval", str(args.interval)])
        )


if __name__ == "__main__":
    main()
