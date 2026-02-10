#!/usr/bin/env python
"""
华尔街见闻爬虫运行脚本

使用方式：
    # 实时监控模式（每30秒轮询一次）
    python -m crawl.wallstreetcn_runner --monitor --interval 30

    # 单次抓取最新20条
    python -m crawl.wallstreetcn_runner --fetch --limit 20

    # 指定频道监控
    python -m crawl.wallstreetcn_runner --monitor --channel global --interval 60
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from crawl.wallstreetcn import WallStreetCNLiveCrawler, WallStreetCNMonitor
from crawl.wallstreetcn_formatter import WallStreetCNFormatter


def save_to_json(
    items: List[Dict[str, Any]],
    output_dir: str = "articles/wallstreetcn",
    use_standard_format: bool = True,
):
    """
    保存快讯到JSON文件

    Args:
        items: 快讯列表
        output_dir: 输出目录
        use_standard_format: 是否使用标准格式（参考隆众资讯）
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 如果使用标准格式，先转换
    if use_standard_format:
        formatter = WallStreetCNFormatter()
        items_to_save = [formatter.format_to_standard(item) for item in items]
    else:
        items_to_save = items

    for i, item in enumerate(items_to_save):
        try:
            # 使用ID和日期作为文件名（与隆众资讯格式一致）
            if use_standard_format:
                item_id = item.get("article_id", "unknown")
                date = item.get("date", "").replace("-", "")  # 20260210
                if not date:
                    date = datetime.now().strftime("%Y%m%d")
                filename = f"WSJ_{date}_{item_id}.json"
            else:
                item_id = item.get("id", "unknown")
                display_time = (
                    item.get("display_time_str", "").replace(" ", "_").replace(":", "")
                )
                if not display_time:
                    display_time = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"wsj_{item_id}_{display_time}.json"

            filepath = output_path / filename

            # 保存JSON
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(item, f, ensure_ascii=False, indent=2)

            print(f"   ✅ 已保存: {filename}")

        except Exception as e:
            print(
                f"   ❌ 保存失败 {item.get('id') if not use_standard_format else item.get('article_id')}: {e}"
            )


def save_to_markdown(
    items: List[Dict[str, Any]], output_dir: str = "articles/wallstreetcn"
):
    """
    保存快讯到Markdown文件

    Args:
        items: 快讯列表
        output_dir: 输出目录
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for item in items:
        try:
            # 使用ID和时间戳作为文件名
            item_id = item.get("id", "unknown")
            display_time = (
                item.get("display_time_str", "").replace(" ", "_").replace(":", "")
            )
            if not display_time:
                display_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"wsj_{item_id}_{display_time}.md"
            filepath = output_path / filename

            # 构建Markdown内容
            channels_str = ", ".join(item.get("channels", []))
            md_content = f"""# {item.get('title', '无标题') or '快讯'}

**来源**: {item.get('source', '华尔街见闻')}
**作者**: {item.get('author_name', 'N/A')}
**频道**: {channels_str or 'N/A'}
**发布时间**: {item.get('display_time_str', 'N/A')}
**评分**: {item.get('score', 0)}
**链接**: {item.get('url', 'N/A')}

---

## 内容

{item.get('content_text', item.get('content', ''))}

---

*抓取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

            # 保存Markdown
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md_content)

            print(f"   ✅ 已保存: {filename}")

        except Exception as e:
            print(f"   ❌ 保存失败 {item.get('id')}: {e}")


def on_new_items(items: List[Dict[str, Any]], save_format: str = "json"):
    """
    处理新快讯的回调函数

    Args:
        items: 新快讯列表
        save_format: 保存格式 (json/markdown/both)
    """
    if not items:
        return

    print(f"\n{'='*60}")
    print(f"📰 收到 {len(items)} 条新快讯")
    print(f"{'='*60}")

    # 显示快讯摘要
    for i, item in enumerate(items, 1):
        print(
            f"\n{i}. [{item.get('display_time_str')}] {item.get('title', '快讯') or '快讯'}"
        )
        content_preview = item.get("content_text", "")[:100]
        print(f"   {content_preview}...")
        print(f"   🔗 {item.get('url')}")

    # 保存到文件
    print("\n💾 保存快讯...")
    if save_format in ("json", "both"):
        save_to_json(items, use_standard_format=True)  # 使用标准格式
    if save_format in ("markdown", "both"):
        save_to_markdown(items)

    print(f"{'='*60}\n")


def fetch_mode(
    channel: str = "global-channel",
    limit: int = 20,
    important_only: bool = False,
    min_score: int = 1,
):
    """
    单次抓取模式

    Args:
        channel: 频道名称
        limit: 抓取数量
        important_only: 是否只抓取重要快讯
        min_score: 最低评分过滤
    """
    filter_msg = (
        f"重要快讯 (Score>={min_score})"
        if important_only or min_score > 1
        else "全部快讯"
    )
    print(f"🔍 开始抓取华尔街见闻 {channel} 频道最新 {limit} 条快讯 ({filter_msg})...")

    crawler = WallStreetCNLiveCrawler()
    items = crawler.fetch_incremental(
        channel=channel, limit=limit, important_only=important_only, min_score=min_score
    )

    if items:
        print(f"✅ 成功获取 {len(items)} 条快讯")
        on_new_items(items, save_format="json")  # 只保存JSON格式
    else:
        print("❌ 未获取到快讯")


def monitor_mode(
    channel: str = "global-channel",
    interval: int = 30,
    save_format: str = "both",
    important_only: bool = False,
    min_score: int = 1,
):
    """
    实时监控模式

    Args:
        channel: 频道名称
        interval: 轮询间隔（秒）
        save_format: 保存格式
        important_only: 是否只监控重要快讯
        min_score: 最低评分过滤
    """
    filter_msg = (
        f"重要快讯 (Score>={min_score})"
        if important_only or min_score > 1
        else "全部快讯"
    )
    print("🚀 启动华尔街见闻实时监控")
    print(f"   频道: {channel}")
    print(f"   轮询间隔: {interval} 秒")
    print(f"   过滤模式: {filter_msg}")
    print(f"   保存格式: {save_format}")
    print("   按 Ctrl+C 停止监控\n")

    crawler = WallStreetCNLiveCrawler()
    monitor = WallStreetCNMonitor(
        crawler=crawler,
        poll_interval=interval,
        channel=channel,
        important_only=important_only,
        min_score=min_score,
    )

    # 启动监控，传入回调函数
    monitor.start(callback=lambda items: on_new_items(items, save_format))


def main():
    parser = argparse.ArgumentParser(
        description="华尔街见闻全球快讯爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 实时监控（每30秒轮询）
  python -m crawl.wallstreetcn_runner --monitor --interval 30

  # 单次抓取最新20条
  python -m crawl.wallstreetcn_runner --fetch --limit 20

  # 只抓取重要快讯（Score >= 2）
  python -m crawl.wallstreetcn_runner --fetch --limit 50 --important

  # 监控重要快讯
  python -m crawl.wallstreetcn_runner --monitor --interval 30 --min-score 2

  # 监控并只保存JSON格式
  python -m crawl.wallstreetcn_runner --monitor --format json

注意:
  首次运行前，请先通过浏览器开发者工具确认API接口地址，
  并在 crawl/wallstreetcn.py 中更新 API_ENDPOINT 常量。
        """,
    )

    parser.add_argument("--monitor", "-m", action="store_true", help="启动实时监控模式")

    parser.add_argument("--fetch", "-f", action="store_true", help="单次抓取模式")

    parser.add_argument(
        "--channel",
        "-c",
        type=str,
        default="global-channel",
        help="频道名称 (默认: global-channel)",
    )

    parser.add_argument(
        "--interval", "-i", type=int, default=30, help="监控轮询间隔（秒） (默认: 30)"
    )

    parser.add_argument(
        "--limit", "-l", type=int, default=20, help="单次抓取数量 (默认: 20)"
    )

    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "markdown", "both"],
        default="json",
        help="保存格式 (默认: json，只保存标准JSON格式)",
    )

    parser.add_argument(
        "--important", action="store_true", help="只抓取重要快讯 (Score >= 2)"
    )

    parser.add_argument(
        "--min-score",
        type=int,
        default=1,
        choices=[1, 2],
        help="最低评分过滤 (1=全部, 2=重要) (默认: 1)",
    )

    args = parser.parse_args()

    # 检查模式
    if not args.monitor and not args.fetch:
        parser.print_help()
        print("\n❌ 错误: 必须指定 --monitor 或 --fetch 模式")
        sys.exit(1)

    # 执行对应模式
    try:
        if args.monitor:
            monitor_mode(
                channel=args.channel,
                interval=args.interval,
                save_format=args.format,
                important_only=args.important,
                min_score=args.min_score,
            )
        elif args.fetch:
            fetch_mode(
                channel=args.channel,
                limit=args.limit,
                important_only=args.important,
                min_score=args.min_score,
            )
    except KeyboardInterrupt:
        print("\n\n⏹️ 程序已停止")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 程序出错: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
