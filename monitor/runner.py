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
from dataclasses import dataclass
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
from monitor.utils import (
    PidFileManager,
    ThreadSafeSet,
    TokenBucketRateLimiter,
    check_disk_space,
)


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
    parser.add_argument(
        "--no-history",
        "--monitor-only",
        action="store_true",
        dest="no_history",
        help="仅启动监控，跳过历史爬取",
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


def _find_keyword_overlaps(keywords: List[str]) -> List[Tuple[str, str]]:
    """找出存在包含关系的关键词对，减少误配时的重复抓取。"""
    overlaps: List[Tuple[str, str]] = []
    for index, left in enumerate(keywords):
        for right in keywords[index + 1 :]:
            if left == right:
                continue
            if left in right or right in left:
                overlaps.append((left, right))
    return overlaps


def _clone_cookies_manager(
    base_manager: OilChemCookiesManager,
) -> OilChemCookiesManager:
    """
    克隆 Cookie 管理器，隔离多关键词并发时的 requests.Session。
    """
    cloned = OilChemCookiesManager(base_manager.cookies_file)
    if not hasattr(base_manager, "session") or not hasattr(cloned, "session"):
        return cloned

    try:
        cloned.session.cookies.clear()
        cloned.session.cookies.update(base_manager.session.cookies)
        cloned.session.headers.update(dict(base_manager.session.headers))
    except Exception:
        return cloned

    return cloned


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


@dataclass
class MonitorRuntime:
    """隆众监控运行时资源包，可供 CLI 和嵌入式适配器复用。"""

    state: MonitorState
    cookies_manager: OilChemCookiesManager
    pid_manager: Optional[PidFileManager] = None
    qiniu_uploader: Optional[AsyncMemoryQiniuUploader] = None
    scheduler: Optional[CrawlScheduler] = None
    scheduler_controller: Optional[MultiCrawlScheduler] = None
    keyboard: Optional[KeyboardListener] = None

    @property
    def controller(self):
        """统一返回单关键词或多关键词调度控制器。"""
        return self.scheduler_controller or self.scheduler

    def start(self) -> None:
        """启动调度器。"""
        start_monitor_runtime(self)

    def stop(self, wait_for_job: bool = True, timeout: float = 60.0) -> None:
        """停止并清理运行时资源。"""
        stop_monitor_runtime(self, wait_for_job=wait_for_job, timeout=timeout)

    def pause(self) -> None:
        """暂停调度器。"""
        controller = self.controller
        if controller is not None and getattr(controller, "is_running", False):
            controller.pause()

    def resume(self) -> None:
        """恢复调度器。"""
        controller = self.controller
        if controller is not None and getattr(controller, "is_running", False):
            controller.resume()

    def run_now(self) -> None:
        """触发立即执行。"""
        controller = self.controller
        if controller is not None:
            controller.run_now()


def build_monitor_runtime(
    keywords: List[str],
    interval_minutes: int,
    *,
    no_history: bool = False,
    days_back: Optional[int] = 30,
    hours_back: Optional[int] = None,
    pages_to_crawl: Optional[int] = 3,
    settings=None,
    force: bool = False,
    enable_pid: bool = True,
    monitor_enabled: bool = True,
    print_preflight: bool = True,
) -> MonitorRuntime:
    """
    构建可复用的隆众监控运行时资源。

    该函数只负责资源初始化，不创建 UI 或信号处理器。
    """
    settings = settings or get_settings()
    monitor_cfg = settings.monitor
    state = MonitorState(
        recent_limit=monitor_cfg.recent_articles_limit,
        poll_history_limit=monitor_cfg.poll_history_limit,
    )
    cookies_manager = OilChemCookiesManager(settings.crawler.cookies_file)
    runtime = MonitorRuntime(state=state, cookies_manager=cookies_manager)

    try:
        if enable_pid:
            pid_manager = PidFileManager()
            try:
                pid_manager.create()
            except RuntimeError:
                if not force:
                    raise
                print("⚠️ 使用 --force 强制启动")
                pid_manager.force_cleanup()
                pid_manager.create()
            runtime.pid_manager = pid_manager

        ok, errors, warnings = _preflight_check(cookies_manager)
        if print_preflight:
            _print_preflight(errors, warnings)
        if not ok:
            raise RuntimeError("启动前预检未通过")

        if no_history:
            if print_preflight:
                print("⏭️ 已按 --no-history/--monitor-only 跳过历史爬取")
        else:
            _run_history_crawl(
                keywords=keywords,
                days_back=days_back,
                hours_back=hours_back,
                pages_to_crawl=pages_to_crawl,
                settings=settings,
            )

        if not monitor_enabled:
            return runtime

        if settings.output.upload_to_qiniu:
            qiniu_config = settings.get_qiniu_config()
            if qiniu_config:
                runtime.qiniu_uploader = AsyncMemoryQiniuUploader(
                    qiniu_config["access_key"],
                    qiniu_config["secret_key"],
                    qiniu_config["bucket_name"],
                    prefix=qiniu_config.get("prefix", "crawled_articles"),
                    max_upload_workers=settings.crawler.max_upload_workers,
                )
                runtime.qiniu_uploader.start_upload_workers()
                if print_preflight:
                    print("✅ 七牛云上传器已启动")
            elif print_preflight:
                print("⚠️ 七牛云上传已启用但配置缺失，已跳过上传")
        elif print_preflight:
            print("⏸️ 七牛云上传已禁用")

        naming_system = UniversalNamingSystem(settings.crawler.project_code)
        existing_ids = ThreadSafeSet(naming_system.load_existing_article_ids())
        if print_preflight:
            print(f"📌 已加载 {len(existing_ids)} 个历史文章 ID")

        converter = AsyncFormatConverter(
            base_dir=settings.crawler.base_dir,
            qiniu_uploader=runtime.qiniu_uploader,
            naming_system=naming_system,
            save_locally=settings.output.save_locally,
            upload_to_qiniu=settings.output.upload_to_qiniu,
        )

        shared_request_gate = None
        shared_rate_limiter = None
        if len(keywords) > 1:
            shared_request_gate = threading.RLock()
            shared_rate_limiter = TokenBucketRateLimiter(
                requests_per_minute=getattr(monitor_cfg, "requests_per_minute", 30),
                min_interval=getattr(monitor_cfg, "min_request_interval", 0.5),
            )

        schedulers: List[CrawlScheduler] = []
        for keyword in keywords:
            scheduler_cookies_manager = (
                _clone_cookies_manager(cookies_manager)
                if len(keywords) > 1
                else cookies_manager
            )
            schedulers.append(
                CrawlScheduler(
                    state,
                    interval_minutes=interval_minutes,
                    keyword=keyword,
                    cookies_manager=scheduler_cookies_manager,
                    converter=converter,
                    existing_ids=existing_ids,
                    output_formats=settings.output.default_formats.copy(),
                    max_pages=monitor_cfg.max_pages_per_poll,
                    early_stop_threshold=monitor_cfg.early_stop_threshold,
                    validate_session_before_poll=monitor_cfg.validate_session_before_poll,
                    max_retries=monitor_cfg.max_retries,
                    retry_base_delay=monitor_cfg.retry_base_delay,
                    manage_state_pause=len(keywords) == 1,
                    request_gate=shared_request_gate,
                    rate_limiter=shared_rate_limiter,
                )
            )

        if len(schedulers) == 1:
            runtime.scheduler = schedulers[0]
        else:
            runtime.scheduler_controller = MultiCrawlScheduler(schedulers, state)

        return runtime

    except Exception:
        stop_monitor_runtime(runtime, wait_for_job=False, timeout=1.0)
        raise


def start_monitor_runtime(runtime: MonitorRuntime) -> None:
    """启动运行时调度器。"""
    controller = runtime.controller
    if controller is not None:
        controller.start()


def stop_monitor_runtime(
    runtime: MonitorRuntime,
    wait_for_job: bool = True,
    timeout: float = 60.0,
) -> None:
    """停止运行时调度器并清理资源。"""
    controller = runtime.controller
    if controller is not None and getattr(controller, "is_running", False):
        controller.stop(wait_for_job=wait_for_job, timeout=timeout)

    if runtime.qiniu_uploader is not None:
        try:
            runtime.qiniu_uploader.wait_for_completion()
        except Exception as exc:
            print(f"⚠️ 等待上传完成时异常: {exc}")
        runtime.qiniu_uploader.stop_upload_workers()
        runtime.qiniu_uploader = None

    if runtime.keyboard is not None and runtime.keyboard.is_running:
        runtime.keyboard.stop()
    runtime.keyboard = None

    if runtime.pid_manager is not None:
        runtime.pid_manager.cleanup()
        runtime.pid_manager = None


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

    # 确定运行参数：显式 CLI 关键词优先，未指定时才回退配置默认值
    keywords = _normalize_keywords(args.keywords, args.keyword)
    if not keywords:
        keywords = _normalize_keywords(monitor_cfg.default_keyword)
    interval_minutes = args.interval or monitor_cfg.poll_interval_minutes
    interactive = monitor_cfg.interactive and not args.no_interactive

    # L4: TTY 检测 - 非 TTY 环境自动禁用交互模式
    if interactive and not sys.stdout.isatty():
        interactive = False
        print("⚠️ 检测到非 TTY 环境，已自动禁用交互模式")

    _print_banner(keywords, interval_minutes, interactive)

    if args.no_history and not args.no_monitor:
        print("⚠️ 当前以 --no-history 启动，首轮轮询前存在冷启动漏数窗口。")

    overlap_pairs = _find_keyword_overlaps(keywords)
    if overlap_pairs:
        overlap_text = "，".join(f"{left}/{right}" for left, right in overlap_pairs)
        print(f"⚠️ 关键词存在重叠，可能增加重复命中与无效抓取: {overlap_text}")

    runtime: Optional[MonitorRuntime] = None
    ui: Optional[MonitorUI] = None
    stop_event = threading.Event()

    def _handle_signal(signum, _frame) -> None:
        """信号处理器"""
        sig_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
        print(f"\n📨 收到 {sig_name} 信号，准备退出...")
        stop_event.set()

        if ui is not None:
            ui.stop()
        if runtime is not None and runtime.controller is not None:
            controller = runtime.controller
            if getattr(controller, "is_running", False):
                controller.stop(wait_for_job=True)

    # 注册信号处理（仅在主线程）
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGINT, _handle_signal)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _handle_signal)
    else:
        print("⚠️ 当前非主线程运行，信号处理已禁用")

    try:
        runtime = build_monitor_runtime(
            keywords=keywords,
            interval_minutes=interval_minutes,
            no_history=args.no_history,
            days_back=args.days,
            hours_back=args.hours,
            pages_to_crawl=args.pages,
            settings=settings,
            force=args.force,
            enable_pid=True,
            monitor_enabled=not args.no_monitor,
            print_preflight=True,
        )

        if args.no_monitor:
            print("⏹️ 已按 --no-monitor 跳过监控")
            return 0

        start_monitor_runtime(runtime)

        if interactive:
            # 交互模式：启动 Rich UI
            keyboard = KeyboardListener()
            runtime.keyboard = keyboard
            # 计算刷新率，避免除零
            refresh_interval = monitor_cfg.ui_refresh_interval
            if refresh_interval <= 0:
                refresh_interval = 1.0
            ui = MonitorUI(
                runtime.state,
                runtime.controller,
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

    except RuntimeError as exc:
        if str(exc) == "启动前预检未通过":
            print("❌ 启动前预检未通过，退出")
            return 1
        print(f"❌ {exc}")
        return 1

    except Exception as exc:
        if runtime is not None:
            runtime.state.set_error(f"监控运行异常: {exc}")
        print(f"❌ 监控运行异常: {exc}")
        import traceback

        traceback.print_exc()
        return 1

    finally:
        if runtime is not None:
            print("\n🧹 正在清理资源...")
            stop_monitor_runtime(runtime, wait_for_job=True, timeout=60.0)
            print("✅ 资源清理完成")


def main() -> None:
    """命令行入口"""
    sys.exit(run_monitor())


if __name__ == "__main__":
    main()
