"""
监控主入口模块

负责：
- 启动前预检（PID/Cookie/磁盘/七牛配置）
- 初始化调度器与交互/非交互运行
- 信号处理与资源清理
"""

from __future__ import annotations

import argparse
import signal
import sys
import threading
import time
from typing import List, Optional, Tuple

from clients import AsyncMemoryQiniuUploader, OilChemCookiesManager
from config import get_settings
from convert import AsyncFormatConverter
from core import UniversalNamingSystem
from crawl.pipeline import extract_from_keyword_async_multithread
from monitor.keyboard import KeyboardListener
from monitor.scheduler import CrawlScheduler, MultiCrawlScheduler
from monitor.state import MonitorState
from monitor.ui import MonitorUI
from monitor.utils import PidFileManager, ThreadSafeSet, check_disk_space


def _positive_int(value: str) -> int:
    """argparse 正整数类型"""
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("必须是整数") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("必须是正整数")
    return parsed


def _non_negative_int(value: str) -> int:
    """argparse 非负整数类型"""
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("必须是整数") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("必须是非负整数")
    return parsed


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="隆众资讯爬虫监控系统",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--keyword",
        type=str,
        default=None,
        help="搜索关键词",
    )
    parser.add_argument(
        "--keywords",
        type=str,
        default=None,
        help="搜索关键词列表（逗号分隔）",
    )
    parser.add_argument(
        "--interval",
        type=_positive_int,
        default=None,
        help="轮询间隔（分钟）",
    )
    parser.add_argument(
        "--days",
        type=_non_negative_int,
        default=30,
        help="历史回溯天数（用于历史爬取）",
    )
    parser.add_argument(
        "--hours",
        type=_non_negative_int,
        default=None,
        help="历史回溯小时数（用于历史爬取）",
    )
    parser.add_argument(
        "--pages",
        type=_positive_int,
        default=3,
        help="历史爬取页数",
    )
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="禁用交互模式（无 Rich UI）",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制启动（忽略过期 PID 文件）",
    )
    parser.add_argument(
        "--no-monitor",
        action="store_true",
        help="仅历史爬取，不启动监控",
    )
    return parser.parse_args(argv)


def _preflight_check(
    cookies_manager: OilChemCookiesManager,
) -> Tuple[bool, List[str], List[str]]:
    """
    启动前预检

    Returns:
        (是否通过, 错误列表, 警告列表)
    """
    settings = get_settings()
    errors: List[str] = []
    warnings: List[str] = []

    # 七牛云配置检查
    if settings.output.upload_to_qiniu and not settings.qiniu.is_configured:
        errors.append("七牛云上传已启用但未配置 access_key/secret_key/bucket_name")

    # Cookie 加载与验证
    if not cookies_manager.load_cookies():
        errors.append(f"Cookie 加载失败: {cookies_manager.cookies_file}")
    else:
        try:
            if not cookies_manager.validate_session():
                errors.append("Cookie 会话无效，请重新导出")
        except Exception as e:
            errors.append(f"Cookie 验证异常: {e}")

    # 磁盘空间检查
    ok, free_mb = check_disk_space(
        settings.crawler.base_dir,
        threshold_mb=settings.monitor.min_disk_space_mb,
    )
    if not ok:
        message = (
            f"磁盘空间不足: 剩余 {free_mb:.1f}MB"
            f" < {settings.monitor.min_disk_space_mb}MB"
        )
        if settings.output.save_locally:
            errors.append(f"{message}（本地保存已启用，无法继续）")
        else:
            warnings.append(f"{message}（仅上传七牛云，可继续运行）")

    return len(errors) == 0, errors, warnings


def _print_preflight(errors: List[str], warnings: List[str]) -> None:
    """打印预检结果"""
    print("\n🔎 启动前预检：")
    print("-" * 40)

    if not errors and not warnings:
        print("✅ 所有检查通过")
        return

    for error in errors:
        print(f"  ❌ {error}")
    for warning in warnings:
        print(f"  ⚠️ {warning}")

    print("-" * 40)


def _print_banner(
    keywords: List[str], interval_minutes: int, interactive: bool
) -> None:
    """打印启动信息"""
    print("\n" + "=" * 50)
    print("🔍 隆众资讯爬虫监控系统")
    print("=" * 50)
    print(f"  关键词: {', '.join(keywords)}")
    print(f"  轮询间隔: {interval_minutes} 分钟")
    print(f"  交互模式: {'是' if interactive else '否'}")
    print("=" * 50 + "\n")


def _normalize_keywords(*values: Optional[str]) -> List[str]:
    """合并并清洗关键词列表（去重，保持顺序）"""
    keywords: List[str] = []
    for value in values:
        if not value:
            continue
        for item in value.split(","):
            item = item.strip()
            if item and item not in keywords:
                keywords.append(item)
    return keywords


def _run_history_crawl(
    keywords: List[str],
    days_back: Optional[int],
    hours_back: Optional[int],
    pages_to_crawl: Optional[int],
    settings,
) -> None:
    """执行历史爬取"""
    # 0 值视为未指定
    if days_back == 0:
        days_back = None
    if hours_back == 0:
        hours_back = None

    # 检查是否有历史爬取请求
    history_requested = any([days_back, hours_back, pages_to_crawl])
    if not history_requested or not keywords:
        return

    # --days 与 --hours 互斥
    if days_back and hours_back:
        print("⚠️ --days 与 --hours 不能同时使用，优先使用 --days")
        hours_back = None

    # 七牛配置检查
    upload_to_qiniu = settings.output.upload_to_qiniu
    qiniu_config = None
    if upload_to_qiniu:
        qiniu_config = settings.get_qiniu_config()
        if not qiniu_config:
            print("⚠️ 七牛云上传已启用但配置缺失，历史爬取将跳过上传")
            upload_to_qiniu = False

    print("\n" + "=" * 50)
    print("⏳ 开始历史爬取...")
    print("=" * 50)
    if days_back:
        print(f"  📅 时间范围: 最近 {days_back} 天")
    elif hours_back:
        print(f"  📅 时间范围: 最近 {hours_back} 小时")
    else:
        print("  📅 时间范围: 不限（按页数爬取）")
    if pages_to_crawl:
        print(f"  📄 爬取页数: {pages_to_crawl}")
    print(f"  🔑 关键词: {', '.join(keywords)}")
    print("=" * 50 + "\n")

    for keyword in keywords:
        print(f"\n🔎 正在爬取关键词: {keyword}")
        print("-" * 40)
        extract_from_keyword_async_multithread(
            keyword=keyword,
            pages_to_crawl=pages_to_crawl,
            days_back=days_back,
            hours_back=hours_back,
            output_formats=settings.output.default_formats.copy(),
            qiniu_config=qiniu_config,
            save_locally=settings.output.save_locally,
            upload_to_qiniu=upload_to_qiniu,
            max_crawl_workers=settings.crawler.max_crawl_workers,
            max_upload_workers=settings.crawler.max_upload_workers,
        )

    print("\n" + "=" * 50)
    print("✅ 历史爬取完成")
    print("=" * 50 + "\n")


def run_monitor(argv: Optional[List[str]] = None) -> int:
    """
    运行监控系统

    Args:
        argv: 命令行参数列表，None 时使用 sys.argv

    Returns:
        退出码（0 成功，非 0 失败）
    """
    args = _parse_args(argv)
    settings = get_settings()
    monitor_cfg = settings.monitor

    # 确定运行参数
    keywords = _normalize_keywords(
        args.keywords, args.keyword, monitor_cfg.default_keyword
    )
    interval_minutes = args.interval or monitor_cfg.poll_interval_minutes
    interactive = monitor_cfg.interactive and not args.no_interactive

    # L4: TTY 检测 - 非 TTY 环境自动禁用交互模式
    if interactive and not sys.stdout.isatty():
        interactive = False
        print("⚠️ 检测到非 TTY 环境，已自动禁用交互模式")

    _print_banner(keywords, interval_minutes, interactive)

    # 初始化状态管理器
    state = MonitorState(
        recent_limit=monitor_cfg.recent_articles_limit,
        poll_history_limit=monitor_cfg.poll_history_limit,
    )

    # Cookie 管理器
    cookies_manager = OilChemCookiesManager(settings.crawler.cookies_file)

    # PID 文件检查
    pid_manager = PidFileManager()
    try:
        pid_manager.create()
    except RuntimeError as exc:
        print(f"❌ {exc}")
        if not args.force:
            return 1
        # L7: --force 参数时先强制清理再重新创建
        print("⚠️ 使用 --force 强制启动")
        pid_manager.force_cleanup()
        try:
            pid_manager.create()
        except RuntimeError as exc2:
            print(f"❌ 强制启动失败: {exc2}")
            return 1

    # 资源变量
    qiniu_uploader: Optional[AsyncMemoryQiniuUploader] = None
    scheduler: Optional[CrawlScheduler] = None
    scheduler_controller: Optional[MultiCrawlScheduler] = None
    ui: Optional[MonitorUI] = None
    keyboard: Optional[KeyboardListener] = None
    stop_event = threading.Event()

    def _handle_signal(signum, _frame) -> None:
        """信号处理器"""
        sig_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
        print(f"\n📨 收到 {sig_name} 信号，准备退出...")
        stop_event.set()

        if ui is not None:
            ui.stop()
        if scheduler_controller is not None and scheduler_controller.is_running:
            scheduler_controller.stop(wait_for_job=True)
        elif scheduler is not None and scheduler.is_running:
            scheduler.stop(wait_for_job=True)

    # 注册信号处理（仅在主线程）
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGINT, _handle_signal)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _handle_signal)
    else:
        print("⚠️ 当前非主线程运行，信号处理已禁用")

    try:
        # 启动前预检
        ok, errors, warnings = _preflight_check(cookies_manager)
        _print_preflight(errors, warnings)

        if not ok:
            print("❌ 启动前预检未通过，退出")
            return 1

        # 执行历史爬取（如果指定了 --days/--hours/--pages）
        _run_history_crawl(
            keywords=keywords,
            days_back=args.days,
            hours_back=args.hours,
            pages_to_crawl=args.pages,
            settings=settings,
        )

        # 如果指定了 --no-monitor，跳过监控直接退出
        if args.no_monitor:
            print("⏹️ 已按 --no-monitor 跳过监控")
            return 0

        # 初始化七牛上传器
        if settings.output.upload_to_qiniu:
            qiniu_config = settings.get_qiniu_config()
            if qiniu_config:
                qiniu_uploader = AsyncMemoryQiniuUploader(
                    qiniu_config["access_key"],
                    qiniu_config["secret_key"],
                    qiniu_config["bucket_name"],
                    prefix=qiniu_config.get("prefix", "crawled_articles"),
                    max_upload_workers=settings.crawler.max_upload_workers,
                )
                qiniu_uploader.start_upload_workers()
                print("✅ 七牛云上传器已启动")
            else:
                print("⚠️ 七牛云上传已启用但配置缺失，已跳过上传")
        else:
            print("⏸️ 七牛云上传已禁用")

        # 加载历史文章 ID（使用线程安全集合）
        naming_system = UniversalNamingSystem(settings.crawler.project_code)
        existing_ids = ThreadSafeSet(naming_system.load_existing_article_ids())
        print(f"📌 已加载 {len(existing_ids)} 个历史文章 ID")

        # 初始化格式转换器
        converter = AsyncFormatConverter(
            base_dir=settings.crawler.base_dir,
            qiniu_uploader=qiniu_uploader,
            naming_system=naming_system,
            save_locally=settings.output.save_locally,
            upload_to_qiniu=settings.output.upload_to_qiniu,
        )

        # 初始化调度器
        schedulers: List[CrawlScheduler] = []
        for keyword in keywords:
            schedulers.append(
                CrawlScheduler(
                    state,
                    interval_minutes=interval_minutes,
                    keyword=keyword,
                    cookies_manager=cookies_manager,
                    converter=converter,
                    existing_ids=existing_ids,
                    output_formats=settings.output.default_formats.copy(),
                    max_pages=monitor_cfg.max_pages_per_poll,
                    early_stop_threshold=monitor_cfg.early_stop_threshold,
                    validate_session_before_poll=monitor_cfg.validate_session_before_poll,
                    max_retries=monitor_cfg.max_retries,
                    retry_base_delay=monitor_cfg.retry_base_delay,
                    manage_state_pause=len(keywords) == 1,
                )
            )

        if len(schedulers) == 1:
            scheduler = schedulers[0]
            scheduler.start()
        else:
            scheduler_controller = MultiCrawlScheduler(schedulers, state)
            scheduler_controller.start()

        if interactive:
            # 交互模式：启动 Rich UI
            keyboard = KeyboardListener()
            # 计算刷新率，避免除零
            refresh_interval = monitor_cfg.ui_refresh_interval
            if refresh_interval <= 0:
                refresh_interval = 1.0
            ui = MonitorUI(
                state,
                scheduler_controller or scheduler,
                keyboard_listener=keyboard,
                refresh_per_second=1.0 / refresh_interval,
                recent_limit=monitor_cfg.recent_articles_limit,
                poll_history_limit=monitor_cfg.poll_history_limit,
                keywords=keywords,
            )
            ui.run()
            stop_event.set()
        else:
            # 非交互模式：简单循环等待
            print("\n🖥️ 非交互模式已启动")
            print("   按 Ctrl+C 退出\n")

            try:
                while not stop_event.is_set():
                    time.sleep(0.5)
            except KeyboardInterrupt:
                stop_event.set()

        return 0

    except Exception as exc:
        state.set_error(f"监控运行异常: {exc}")
        print(f"❌ 监控运行异常: {exc}")
        import traceback

        traceback.print_exc()
        return 1

    finally:
        # 资源清理（顺序重要：先停调度器等待轮询 -> 等待上传 -> 停键盘 -> 清PID）
        print("\n🧹 正在清理资源...")

        # 1. 先停止调度器，等待当前轮询完成
        if scheduler_controller is not None and scheduler_controller.is_running:
            scheduler_controller.stop(wait_for_job=True, timeout=60.0)
        elif scheduler is not None and scheduler.is_running:
            scheduler.stop(wait_for_job=True, timeout=60.0)

        # 2. 等待上传队列完成（轮询已停，不会有新上传）
        if qiniu_uploader is not None:
            try:
                print("⏳ 等待上传队列完成...")
                qiniu_uploader.wait_for_completion()
            except Exception as exc:
                print(f"⚠️ 等待上传完成时异常: {exc}")
            qiniu_uploader.stop_upload_workers()

        # 3. 停止键盘监听
        if keyboard is not None and keyboard.is_running:
            keyboard.stop()

        # 4. 最后清理 PID 文件
        pid_manager.cleanup()
        print("✅ 资源清理完成")


def main() -> None:
    """命令行入口"""
    sys.exit(run_monitor())


if __name__ == "__main__":
    main()
