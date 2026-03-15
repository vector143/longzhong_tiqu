#!/usr/bin/env python
"""
统一监控入口脚本

集成三个监控系统：
1. 隆众资讯监控
2. 华尔街见闻监控
3. Investing.com 监控

使用 Rich 界面实时展示所有监控状态
"""

import argparse
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from monitor.manager import MonitorManager
from monitor.adapters import WallStreetCNAdapter, InvestingAdapter, LongZhongAdapter
from monitor.unified_ui import UnifiedMonitorUI


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="统一监控系统 - 集成隆众/华尔街见闻/Investing.com",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 启动所有监控（使用默认配置）
  python unified_monitor.py

  # 自定义隆众关键词
  python unified_monitor.py --lz-keywords "原油,甲醇,PTA"

  # 自定义华尔街见闻频道
  python unified_monitor.py --wsj-channels commodity-channel oil-channel

  # 自定义 Investing 代理
  python unified_monitor.py --inv-proxy http://127.0.0.1:7897

  # 自定义 Investing 抓取节流
  python unified_monitor.py --inv-delay 1.5 --inv-max-pages 5 --inv-workers 2

  # 开启 Investing 自适应轮询（空轮询自动降频）
  python unified_monitor.py --inv-adaptive --inv-max-interval 180

  # 禁用某个监控源
  python unified_monitor.py --disable-lz --disable-wsj

  # 自定义轮询间隔
  python unified_monitor.py --lz-interval 60 --wsj-interval 30 --inv-interval 300
        """,
    )

    # 隆众资讯配置
    parser.add_argument(
        "--lz-keywords",
        type=str,
        default="原油,甲醇,PTA,乙二醇,铜,白银,橡胶,天然橡胶",
        help="隆众资讯关键词（逗号分隔）",
    )
    parser.add_argument(
        "--lz-interval",
        type=int,
        default=30,
        help="隆众资讯轮询间隔（分钟）",
    )
    parser.add_argument(
        "--disable-lz",
        action="store_true",
        help="禁用隆众资讯监控",
    )

    # 华尔街见闻配置
    parser.add_argument(
        "--wsj-channels",
        nargs="+",
        default=[
            "commodity-channel",
            "oil-channel",
            "gold-channel",
            "gold-forex-channel",
            "goldc-channel",
        ],
        help="华尔街见闻频道列表",
    )
    parser.add_argument(
        "--wsj-interval",
        type=int,
        default=30,
        help="华尔街见闻轮询间隔（秒）",
    )
    parser.add_argument(
        "--wsj-important",
        action="store_true",
        help="华尔街见闻只监控重要快讯",
    )
    parser.add_argument(
        "--disable-wsj",
        action="store_true",
        help="禁用华尔街见闻监控",
    )

    # Investing.com 配置
    parser.add_argument(
        "--inv-channels",
        nargs="+",
        default=["commodities", "economic-indicators", "economy"],
        help="Investing.com 频道列表",
    )
    parser.add_argument(
        "--inv-interval",
        type=int,
        default=30,
        help="Investing.com 轮询间隔（秒）",
    )
    parser.add_argument(
        "--inv-proxy",
        type=str,
        default="http://127.0.0.1:7897",
        help="Investing.com 代理地址",
    )
    parser.add_argument(
        "--inv-delay",
        type=float,
        default=3.0,
        help="Investing.com 单请求延迟（秒）",
    )
    parser.add_argument(
        "--inv-max-pages",
        type=int,
        default=3,
        help="Investing.com 单轮最大翻页数",
    )
    parser.add_argument(
        "--inv-workers",
        type=int,
        default=3,
        help="Investing.com 单轮最大并发数",
    )
    parser.add_argument(
        "--inv-adaptive",
        action="store_true",
        help="开启 Investing 自适应轮询（空轮询自动拉长间隔）",
    )
    parser.add_argument(
        "--inv-max-interval",
        type=int,
        default=180,
        help="Investing 自适应轮询最大间隔（秒）",
    )
    parser.add_argument(
        "--disable-inv",
        action="store_true",
        help="禁用 Investing.com 监控",
    )

    # UI 配置
    parser.add_argument(
        "--refresh-rate",
        type=float,
        default=0.5,
        help="UI 刷新间隔（秒），默认 0.5 秒（2 FPS）",
    )

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    print("=" * 60)
    print("🎯 统一监控系统")
    print("=" * 60)

    # 创建监控管理器
    manager = MonitorManager()

    # 注册监控适配器
    enabled_count = 0

    if not args.disable_lz:
        print(f"✅ 隆众资讯: {args.lz_keywords}")
        keywords = [k.strip() for k in args.lz_keywords.split(",")]
        lz_adapter = LongZhongAdapter(
            keywords=keywords,
            interval=args.lz_interval,
            no_history=True,
        )
        manager.register(lz_adapter)
        enabled_count += 1

    if not args.disable_wsj:
        print(f"✅ 华尔街见闻: {len(args.wsj_channels)} 个频道")
        wsj_adapter = WallStreetCNAdapter(
            channels=args.wsj_channels,
            interval=args.wsj_interval,
            important_only=args.wsj_important,
        )
        manager.register(wsj_adapter)
        enabled_count += 1

    if not args.disable_inv:
        print(f"✅ Investing.com: {len(args.inv_channels)} 个频道")
        inv_adapter = InvestingAdapter(
            channels=args.inv_channels,
            interval=args.inv_interval,
            proxy=args.inv_proxy,
            delay=args.inv_delay,
            max_pages=args.inv_max_pages,
            workers=args.inv_workers,
            adaptive_interval=args.inv_adaptive,
            max_interval=args.inv_max_interval,
        )
        manager.register(inv_adapter)
        enabled_count += 1

    if enabled_count == 0:
        print("❌ 错误: 至少需要启用一个监控源")
        return 1

    print(f"\n📊 已启用 {enabled_count} 个监控源")
    print("=" * 60)
    print()

    # 信号处理
    def signal_handler(signum, frame):
        print("\n\n⚠️ 收到停止信号，正在停止所有监控...")
        manager.stop_all(timeout=10.0)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 启动所有监控
    manager.start_all()

    # 启动 UI
    ui = UnifiedMonitorUI(manager, refresh_rate=args.refresh_rate)
    ui.run()

    return 0


if __name__ == "__main__":
    sys.exit(main())
