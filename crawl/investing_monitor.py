#!/usr/bin/env python
"""
Investing.com 新闻监控脚本

功能：
1. 首次运行：爬取每个频道的历史文章（默认100篇）
2. 后续运行：增量爬取新文章
3. 自动去重：基于 content_digest 去重
4. 持续监控：定时检查新文章

使用示例:
  # 首次运行，爬取历史文章
  python investing_monitor.py --history 100 --proxy http://127.0.0.1:7897

  # 增量监控模式（每5分钟检查一次）
  python investing_monitor.py --monitor --interval 300 --proxy http://127.0.0.1:7897

  # 单次增量爬取
  python investing_monitor.py --proxy http://127.0.0.1:7897
"""

import sys
import json
import time
import argparse
import threading
from pathlib import Path
from datetime import datetime
from typing import Set, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from crawl.investing_crawler import InvestingCommodityNewsCrawler
from crawl.investing_formatter import InvestingFormatter


class RateLimiter:
    """智能限速器 - 替代固定sleep，支持并发"""

    def __init__(self, min_interval: float = 1.0):
        """
        初始化限速器

        Args:
            min_interval: 最小请求间隔（秒）
        """
        self.min_interval = min_interval
        self.last_request_time = 0
        self.lock = threading.Lock()

    def wait(self):
        """等待直到可以发起下一个请求"""
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time

            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)

            self.last_request_time = time.time()


class InvestingMonitor:
    """Investing.com 新闻监控器"""

    def __init__(
        self,
        output_dir: str = None,
        proxy: str = None,
        max_workers: int = 5,
        rate_limit: float = 1.0,
    ):
        """
        初始化监控器

        Args:
            output_dir: 输出目录（默认：项目根目录/output/report/cleaned）
            proxy: 代理地址
            max_workers: 最大并发数（默认：5）
            rate_limit: 请求最小间隔（秒，默认：1.0）
        """
        # 默认输出目录：项目根目录/output/report/cleaned
        if output_dir is None:
            project_root = Path(__file__).parent.parent
            output_dir = project_root / "output" / "report" / "cleaned"

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.proxy = proxy
        self.formatter = InvestingFormatter()

        # 并发控制
        self.max_workers = max_workers
        self.rate_limiter = RateLimiter(min_interval=rate_limit)
        self.semaphore = threading.Semaphore(max_workers)
        self.lock = threading.Lock()

        # 去重数据库文件：保存在项目根目录
        project_root = Path(__file__).parent.parent
        self.db_file = project_root / "investing_articles.db.json"
        self.seen_digests = self._load_seen_digests()

    def _load_seen_digests(self) -> Set[str]:
        """加载已爬取文章的digest集合"""
        if self.db_file.exists():
            try:
                with open(self.db_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return set(data.get("digests", []))
            except Exception as e:
                print(f"⚠️ 加载去重数据库失败: {e}")
        return set()

    def _save_seen_digests(self):
        """保存已爬取文章的digest集合"""
        try:
            data = {
                "digests": list(self.seen_digests),
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_count": len(self.seen_digests),
            }
            with open(self.db_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ 保存去重数据库失败: {e}")

    def _is_duplicate(self, content_digest: str) -> bool:
        """检查文章是否已存在"""
        return content_digest in self.seen_digests

    def _mark_as_seen(self, content_digest: str):
        """标记文章为已爬取"""
        self.seen_digests.add(content_digest)

    def _save_article(self, article: Dict[str, Any], channel: str) -> bool:
        """
        保存文章到文件

        Args:
            article: 标准格式的文章数据
            channel: 频道名称

        Returns:
            是否保存成功
        """
        try:
            # 文件命名：与隆众格式一致
            # 格式：YYYY-MM-DD_机构_标题_文章ID.json
            date = article.get("date", "")
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")

            institution = article.get("institution", "Investing.com")
            title = article.get("title", "untitled")
            article_id = article.get("article_id", "unknown")

            # 清理标题中的特殊字符
            title_clean = title.replace("/", "_").replace("\\", "_").replace(":", "_")
            if len(title_clean) > 50:
                title_clean = title_clean[:50]

            filename = f"{date}_{institution}_{title_clean}_{article_id}.json"
            filepath = self.output_dir / filename

            # 保存JSON
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(article, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            print(f"   ❌ 保存失败: {e}")
            return False

    def crawl_history(
        self, channels: List[str], target_count: int = 100, delay: float = 3.0
    ) -> Dict[str, int]:
        """
        爬取历史文章

        Args:
            channels: 频道列表
            target_count: 每个频道目标文章数
            delay: 请求延迟

        Returns:
            各频道爬取统计
        """
        print("=" * 80)
        print("📚 历史文章爬取模式")
        print("=" * 80)
        print(f"📺 频道: {', '.join(channels)}")
        print(f"🎯 目标数量: 每个频道 {target_count} 篇")
        print(f"⏱️  请求延迟: {delay} 秒")
        if self.proxy:
            print(f"🌐 代理: {self.proxy}")
        print("=" * 80)
        print()

        stats = {}

        for channel in channels:
            print(f"\n{'='*80}")
            print(f"📺 正在爬取频道: {channel}")
            print(f"{'='*80}\n")

            crawler = InvestingCommodityNewsCrawler(channel=channel, proxy=self.proxy)

            collected = []
            page = 1
            max_pages = 20  # 最多爬取20页

            while len(collected) < target_count and page <= max_pages:
                print(f"📄 正在获取第 {page} 页...")

                result = crawler.fetch_news_list(page=page, delay=delay)

                if not result["success"] or not result["data"]:
                    print(f"⚠️ 第 {page} 页获取失败或无数据，停止爬取")
                    break

                # 获取详细内容
                for i, news_item in enumerate(result["data"], 1):
                    if len(collected) >= target_count:
                        break

                    print(
                        f"[{len(collected)+1}/{target_count}] {news_item.get('title', '')[:50]}..."
                    )

                    # 获取文章内容
                    content_result = crawler.fetch_article_content(news_item["url"])

                    if content_result["success"]:
                        # 更新新闻项
                        news_item["content"] = content_result["content"]
                        news_item["html_content"] = content_result["html_content"]
                        if content_result["publish_time"]:
                            news_item["publish_time"] = content_result["publish_time"]
                        if content_result["author"]:
                            news_item["author"] = content_result["author"]

                        # 转换为标准格式
                        standard_data = self.formatter.format_to_standard(news_item)
                        content_digest = standard_data["content_digest"]

                        # 去重检查
                        if self._is_duplicate(content_digest):
                            print("   ⏭️  已存在，跳过")
                            continue

                        # 保存文章
                        if self._save_article(standard_data, channel):
                            self._mark_as_seen(content_digest)
                            collected.append(standard_data)
                            print(f"   ✅ 已保存 ({len(collected)}/{target_count})")
                        else:
                            print("   ❌ 保存失败")
                    else:
                        print(f"   ⚠️ 内容获取失败: {content_result['error']}")

                    # 添加延迟
                    if len(collected) < target_count:
                        time.sleep(delay)

                page += 1

            # 保存去重数据库
            self._save_seen_digests()

            stats[channel] = len(collected)
            print(f"\n✅ 频道 {channel} 完成: 爬取 {len(collected)} 篇文章")

        return stats

    def _crawl_channel_incremental(
        self, channel: str, max_pages: int = 3
    ) -> tuple[str, int]:
        """
        单个频道的增量爬取（用于并发）

        Args:
            channel: 频道名称
            max_pages: 最多检查页数

        Returns:
            (频道名, 新增文章数)
        """
        print(f"\n{'='*80}")
        print(f"📺 检查频道: {channel}")
        print(f"{'='*80}\n")

        crawler = InvestingCommodityNewsCrawler(channel=channel, proxy=self.proxy)

        new_articles = []
        consecutive_old_count = 0
        max_consecutive_old = 5

        for page in range(1, max_pages + 1):
            print(f"📄 [{channel}] 检查第 {page} 页...")

            # 使用限速器替代固定延迟
            self.rate_limiter.wait()
            result = crawler.fetch_news_list(page=page, delay=0)

            if not result["success"] or not result["data"]:
                print(f"⚠️ [{channel}] 第 {page} 页获取失败或无数据")
                break

            # 收集需要获取详情的文章
            new_items = []
            page_old_count = 0

            for news_item in result["data"]:
                temp_standard = self.formatter.format_to_standard(news_item)
                quick_digest = temp_standard["content_digest"]

                if self._is_duplicate(quick_digest):
                    page_old_count += 1
                    consecutive_old_count += 1

                    if consecutive_old_count >= max_consecutive_old:
                        print(
                            f"   ℹ️  [{channel}] 连续遇到 {max_consecutive_old} 篇旧文章，停止检查"
                        )
                        break
                    continue

                consecutive_old_count = 0
                new_items.append(news_item)

            # 并发获取文章详情
            if new_items:
                fetched = self._fetch_articles_concurrent(new_items, channel, crawler)
                new_articles.extend(fetched)

            page_new_count = len(new_items)
            if page_new_count > 0 or page_old_count > 0:
                print(
                    f"   [{channel}] 第 {page} 页: 新增 {page_new_count} 篇, 跳过 {page_old_count} 篇"
                )

            if consecutive_old_count >= max_consecutive_old:
                print(f"   ℹ️  [{channel}] 已到达已爬取内容区域，停止翻页")
                break

            if page_new_count == 0 and page_old_count > 0:
                print(f"   ℹ️  [{channel}] 本页无新文章，停止翻页")
                break

        if len(new_articles) > 0:
            print(f"\n✅ 频道 {channel} 完成: 新增 {len(new_articles)} 篇文章")
        else:
            print(f"\n✅ 频道 {channel} 完成: 无新文章")

        return channel, len(new_articles)

    def _fetch_articles_concurrent(
        self,
        news_items: List[Dict[str, Any]],
        channel: str,
        crawler: InvestingCommodityNewsCrawler,
    ) -> List[Dict[str, Any]]:
        """
        并发获取多篇文章详情

        Args:
            news_items: 文章列表
            channel: 频道名称
            crawler: 爬虫实例

        Returns:
            成功保存的文章列表
        """
        saved_articles = []
        crawler_channel = getattr(crawler, "channel", channel)

        def fetch_one(news_item):
            """获取单篇文章"""
            with self.semaphore:
                title_short = news_item.get("title", "")[:50]
                print(f"🆕 [{channel}] 发现新文章: {title_short}...")

                # 使用限速器
                self.rate_limiter.wait()
                # 详情抓取使用独立 crawler，避免多个线程共享同一个 requests.Session。
                worker_crawler = InvestingCommodityNewsCrawler(
                    channel=crawler_channel,
                    proxy=self.proxy,
                )
                content_result = worker_crawler.fetch_article_content(news_item["url"])

                if content_result["success"]:
                    news_item["content"] = content_result["content"]
                    news_item["html_content"] = content_result["html_content"]
                    if content_result["publish_time"]:
                        news_item["publish_time"] = content_result["publish_time"]
                    if content_result["author"]:
                        news_item["author"] = content_result["author"]

                    standard_data = self.formatter.format_to_standard(news_item)
                    content_digest = standard_data["content_digest"]

                    # 线程安全的去重检查和保存
                    with self.lock:
                        if self._is_duplicate(content_digest):
                            print(f"   ⏭️  [{channel}] 内容重复，跳过")
                            return None

                        if self._save_article(standard_data, channel):
                            self._mark_as_seen(content_digest)
                            print(f"   ✅ [{channel}] 已保存")
                            return standard_data
                else:
                    print(f"   ⚠️ [{channel}] 内容获取失败")

            return None

        # 使用线程池并发获取
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(fetch_one, item) for item in news_items]

            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        saved_articles.append(result)
                except Exception as e:
                    print(f"   ❌ [{channel}] 处理失败: {e}")

        return saved_articles

    def crawl_incremental(
        self, channels: List[str], delay: float = 3.0, max_pages: int = 3
    ) -> Dict[str, int]:
        """
        增量爬取新文章（并发版本）

        Args:
            channels: 频道列表
            delay: 请求延迟（已废弃，使用 rate_limit 替代）
            max_pages: 最多检查页数

        Returns:
            各频道新增文章数
        """
        print("=" * 80)
        print("🔄 增量爬取模式（并发优化）")
        print("=" * 80)
        print(f"📺 频道: {', '.join(channels)}")
        print(f"📄 检查页数: 最多 {max_pages} 页（遇到旧文章自动停止）")
        print(f"🚀 并发数: {self.max_workers}")
        print(f"⏱️  限速: {self.rate_limiter.min_interval} 秒/请求")
        if self.proxy:
            print(f"🌐 代理: {self.proxy}")
        print(f"📊 已知文章数: {len(self.seen_digests)}")
        print("=" * 80)
        print()

        stats = {}

        # 并发处理多个频道
        with ThreadPoolExecutor(max_workers=len(channels)) as executor:
            futures = {
                executor.submit(
                    self._crawl_channel_incremental, channel, max_pages
                ): channel
                for channel in channels
            }

            for future in as_completed(futures):
                try:
                    channel, count = future.result()
                    stats[channel] = count
                except Exception as e:
                    channel = futures[future]
                    print(f"❌ 频道 {channel} 处理失败: {e}")
                    stats[channel] = 0

        # 保存去重数据库
        self._save_seen_digests()

        return stats

    def monitor_loop(
        self, channels: List[str], interval: int = 300, delay: float = 3.0
    ):
        """
        持续监控模式

        Args:
            channels: 频道列表
            interval: 检查间隔（秒）
            delay: 请求延迟
        """
        print("=" * 80)
        print("🔁 持续监控模式")
        print("=" * 80)
        print(f"📺 频道: {', '.join(channels)}")
        print(f"⏰ 检查间隔: {interval} 秒 ({interval/60:.1f} 分钟)")
        print(f"⏱️  请求延迟: {delay} 秒")
        if self.proxy:
            print(f"🌐 代理: {self.proxy}")
        print("=" * 80)
        print()

        round_num = 1

        try:
            while True:
                print(f"\n{'='*80}")
                print(
                    f"🔄 第 {round_num} 轮检查 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                print(f"{'='*80}\n")

                stats = self.crawl_incremental(channels, delay=delay)

                total_new = sum(stats.values())
                print(f"\n{'='*80}")
                print(f"✅ 本轮完成: 共新增 {total_new} 篇文章")
                if total_new > 0:
                    for channel, count in stats.items():
                        if count > 0:
                            print(f"   - {channel}: {count} 篇")
                else:
                    print("   所有频道均无新文章")
                print(f"📊 数据库总计: {len(self.seen_digests)} 篇文章")
                print(f"{'='*80}\n")

                next_check_time = datetime.now().timestamp() + interval
                next_check_str = datetime.fromtimestamp(next_check_time).strftime(
                    "%H:%M:%S"
                )
                print(f"😴 等待 {interval} 秒后进行下一轮检查...")
                print(f"   下次检查时间: {next_check_str}")
                print("   (按 Ctrl+C 停止监控)\n")

                time.sleep(interval)
                round_num += 1

        except KeyboardInterrupt:
            print("\n\n⚠️ 收到停止信号，退出监控...")
            print(f"📊 最终统计: 共爬取 {len(self.seen_digests)} 篇文章")


def main():
    parser = argparse.ArgumentParser(
        description="Investing.com 新闻监控脚本（历史爬取+增量监控+自动去重）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 首次运行，爬取每个频道100篇历史文章
  python investing_monitor.py --history 100 --proxy http://127.0.0.1:7897

  # 增量爬取新文章（单次）
  python investing_monitor.py --proxy http://127.0.0.1:7897

  # 持续监控模式（每5分钟检查一次）
  python investing_monitor.py --monitor --interval 300 --proxy http://127.0.0.1:7897

  # 只爬取特定频道
  python investing_monitor.py --channels commodities economy --proxy http://127.0.0.1:7897
        """,
    )

    parser.add_argument(
        "--history",
        type=int,
        default=None,
        help="历史爬取模式：每个频道爬取的文章数量（例如: 100）",
    )

    parser.add_argument(
        "--monitor",
        "-m",
        action="store_true",
        help="持续监控模式（定时检查新文章）",
    )

    parser.add_argument(
        "--interval",
        "-i",
        type=int,
        default=300,
        help="监控模式的检查间隔（秒）(默认: 300秒=5分钟)",
    )

    parser.add_argument(
        "--channels",
        "-c",
        nargs="+",
        choices=["commodities", "economic-indicators", "economy"],
        default=["commodities", "economic-indicators", "economy"],
        help="要爬取的频道列表 (默认: 所有频道)",
    )

    parser.add_argument(
        "--delay",
        "-d",
        type=float,
        default=1.0,
        help="请求最小间隔（秒）(默认: 1.0，用于限速器)",
    )

    parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=5,
        help="最大并发数 (默认: 5)",
    )

    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="输出目录 (默认: output/report/cleaned)",
    )

    parser.add_argument(
        "--proxy",
        "-x",
        default=None,
        help="代理地址 (例如: http://127.0.0.1:7897)",
    )

    args = parser.parse_args()

    # 创建监控器（使用新的并发参数）
    monitor = InvestingMonitor(
        output_dir=args.output,
        proxy=args.proxy,
        max_workers=args.workers,
        rate_limit=args.delay,
    )

    # 根据参数选择模式
    if args.history:
        # 历史爬取模式
        stats = monitor.crawl_history(
            channels=args.channels,
            target_count=args.history,
            delay=args.delay,
        )

        total = sum(stats.values())
        print(f"\n{'='*80}")
        print("✅ 历史爬取完成！")
        print(f"📊 总计: {total} 篇文章")
        for channel, count in stats.items():
            print(f"   - {channel}: {count} 篇")
        print(f"💾 保存位置: {args.output}")
        print(f"{'='*80}")

    elif args.monitor:
        # 持续监控模式
        monitor.monitor_loop(
            channels=args.channels,
            interval=args.interval,
            delay=args.delay,
        )

    else:
        # 单次增量爬取模式
        stats = monitor.crawl_incremental(
            channels=args.channels,
            delay=args.delay,
        )

        total = sum(stats.values())
        print(f"\n{'='*80}")
        print("✅ 增量爬取完成！")
        print(f"📊 新增: {total} 篇文章")
        for channel, count in stats.items():
            print(f"   - {channel}: {count} 篇")
        print(f"💾 保存位置: {args.output}")
        print(f"📊 数据库总计: {len(monitor.seen_digests)} 篇文章")
        print(f"{'='*80}")


if __name__ == "__main__":
    main()
