"""
Rich 监控界面模块

提供：
- 实时监控界面布局（Layout + Panel + Table）
- 与 MonitorState 的状态数据联动
- 快捷键控制（Q 退出 / R 立即运行 / P 暂停或恢复）
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import List, Optional, Tuple, TypeVar, Union

from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from monitor.keyboard import KeyboardListener
from monitor.scheduler import CrawlScheduler, MultiCrawlScheduler
from monitor.state import MonitorState

T = TypeVar("T")


class MonitorUI:
    """
    Rich 监控界面

    使用 Live + Layout + Table + Panel 渲染实时界面，
    并与调度器/键盘监听集成。

    Example:
        state = MonitorState()
        scheduler = CrawlScheduler(state)
        keyboard = KeyboardListener()
        ui = MonitorUI(state, scheduler, keyboard)
        scheduler.start()
        ui.run()  # 阻塞运行
    """

    def __init__(
        self,
        state: MonitorState,
        scheduler: Union[CrawlScheduler, MultiCrawlScheduler],
        keyboard_listener: Optional[KeyboardListener] = None,
        refresh_per_second: float = 4.0,
        recent_limit: Optional[int] = None,
        poll_history_limit: Optional[int] = None,
        console: Optional[Console] = None,
        keywords: Optional[List[str]] = None,
    ) -> None:
        """
        初始化监控界面

        Args:
            state: 监控状态管理器
            scheduler: 爬取调度器
            keyboard_listener: 键盘监听器（可选，None 时自动创建）
            refresh_per_second: 界面刷新频率（每秒）
            recent_limit: 最近文章显示数量上限
            poll_history_limit: 轮询历史显示数量上限
            console: Rich Console 实例

        Raises:
            ValueError: refresh_per_second 必须为正数
        """
        if refresh_per_second <= 0:
            raise ValueError("refresh_per_second 必须为正数")

        self._state = state
        self._scheduler = scheduler
        self._keyboard = keyboard_listener or KeyboardListener()
        self._refresh_per_second = refresh_per_second
        self._recent_limit = recent_limit
        self._poll_history_limit = poll_history_limit
        self._console = console or Console()
        self._stop_event = threading.Event()
        self._keys_registered = False
        self._keywords = keywords or []

    def run(self) -> None:
        """
        启动 Live 循环

        - 启动键盘监听
        - 持续刷新界面，直到收到退出信号
        """
        self._stop_event.clear()
        self._register_keys()

        if not self._keyboard.is_running:
            self._keyboard.start()

        refresh_interval = 1.0 / self._refresh_per_second

        try:
            with Live(
                self._build_layout(),
                refresh_per_second=self._refresh_per_second,
                console=self._console,
                screen=True,
            ) as live:
                while not self._stop_event.is_set():
                    # 检查每日重置
                    self._state.check_daily_reset()
                    # 更新界面
                    live.update(self._build_layout())
                    time.sleep(refresh_interval)

        except KeyboardInterrupt:
            self._stop_event.set()

        finally:
            self._keyboard.stop()
            if self._scheduler.is_running:
                self._scheduler.stop()

    def stop(self) -> None:
        """停止监控界面"""
        self._stop_event.set()

    def _register_keys(self) -> None:
        """注册快捷键回调"""
        if self._keys_registered:
            return

        # Q - 退出
        self._keyboard.register_key("q", self._on_quit)
        self._keyboard.register_key("Q", self._on_quit)

        # R - 立即运行
        self._keyboard.register_key("r", self._on_run_now)
        self._keyboard.register_key("R", self._on_run_now)

        # P - 暂停/恢复
        self._keyboard.register_key("p", self._on_toggle_pause)
        self._keyboard.register_key("P", self._on_toggle_pause)

        self._keys_registered = True

    def _on_quit(self) -> None:
        """退出监控"""
        self._stop_event.set()

    def _on_run_now(self) -> None:
        """立即执行一次轮询"""
        self._scheduler.run_now()

    def _on_toggle_pause(self) -> None:
        """暂停/恢复调度"""
        if not self._scheduler.is_running:
            self._scheduler.start()
            return

        if self._scheduler.is_paused:
            self._scheduler.resume()
        else:
            self._scheduler.pause()

    def _build_layout(self) -> Layout:
        """构建整体布局"""
        layout = Layout(name="root")

        # 分割为头部、主体、底部
        layout.split(
            Layout(name="header", size=4),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=3),
        )

        # 主体分割为统计、文章、轮询
        layout["body"].split(
            Layout(name="stats", size=7),
            Layout(name="articles", ratio=1),
            Layout(name="polls", ratio=1),
        )

        # 填充各区域内容
        layout["header"].update(self._render_header())
        layout["stats"].update(self._render_stats())
        layout["articles"].update(self._render_articles())
        layout["polls"].update(self._render_polls())
        layout["footer"].update(self._render_footer())

        return layout

    def _render_header(self) -> Panel:
        """渲染头部信息"""
        table = Table.grid(expand=True)
        table.add_column(justify="left")
        table.add_column(justify="center")
        table.add_column(justify="right")

        # 状态显示
        status_label, status_color = self._status_display()
        status_text = Text(f"状态: ● {status_label}", style=status_color)

        # 下次轮询时间
        next_poll = self._format_time(self._state.next_poll_time)
        next_text = Text(f"下次轮询: {next_poll}", style="cyan")

        table.add_row(
            Text("🔍 隆众资讯爬虫监控", style="bold"),
            status_text,
            next_text,
        )
        if self._keywords:
            keywords_text = Text(
                f"关键词: {self._format_keywords(self._keywords)}", style="yellow"
            )
            table.add_row(keywords_text, Text(""), Text(""))

        # 错误信息显示
        subtitle = None
        if self._state.last_error:
            error_msg = self._state.last_error[:50]
            if len(self._state.last_error) > 50:
                error_msg += "..."
            subtitle = f"❌ {error_msg}"

        return Panel(table, style="bold white", subtitle=subtitle)

    def _render_stats(self) -> Panel:
        """渲染今日统计面板"""
        table = Table(
            show_header=False,
            box=box.SQUARE,
            expand=True,
            pad_edge=False,
        )

        for _ in range(4):
            table.add_column(justify="center", width=15)

        # 标题行
        table.add_row(
            Text("总爬取", style="bold"),
            Text("成功", style="bold green"),
            Text("失败", style="bold red"),
            Text("跳过", style="bold yellow"),
        )

        # 数据行
        table.add_row(
            str(self._state.today_total),
            str(self._state.today_success),
            str(self._state.today_failed),
            str(self._state.today_skipped),
        )

        # 运行时间
        uptime = self._state.get_uptime()
        uptime_str = self._format_uptime(uptime)

        return Panel(
            table,
            title="📊 今日统计",
            subtitle=f"运行时间: {uptime_str} | 总轮询: {self._state.total_polls}次",
        )

    def _render_articles(self) -> Panel:
        """渲染最近爬取文章表格"""
        table = Table(box=box.MINIMAL_DOUBLE_HEAD, expand=True)
        table.add_column("时间", justify="center", width=10)
        table.add_column("关键词", justify="center", width=10)
        table.add_column("标题", overflow="fold")
        table.add_column("发布时间", justify="center", width=12)
        table.add_column("状态", justify="center", width=8)

        articles = self._limit_items(self._state.recent_articles, self._recent_limit)

        if not articles:
            table.add_row("--", "--", "暂无数据", "--", "--")
            return Panel(table, title="📰 最近爬取文章")

        for record in articles:
            crawl_time = self._format_time(record.crawl_time)
            status_text = self._article_status_text(record.status)
            # 截断标题
            title = (
                record.title[:40] + "..." if len(record.title) > 40 else record.title
            )
            table.add_row(
                crawl_time,
                record.keyword or "-",
                title,
                record.publish_time[:10],
                status_text,
            )

        return Panel(table, title="📰 最近爬取文章")

    def _render_polls(self) -> Panel:
        """渲染轮询历史表格"""
        table = Table(box=box.MINIMAL_DOUBLE_HEAD, expand=True)
        table.add_column("时间", justify="center", width=10)
        table.add_column("关键词", justify="center", width=10)
        table.add_column("新增", justify="right", width=8)
        table.add_column("成功", justify="right", width=8)
        table.add_column("失败", justify="right", width=8)
        table.add_column("跳过", justify="right", width=8)
        table.add_column("耗时", justify="right", width=10)

        polls = self._limit_items(self._state.poll_history, self._poll_history_limit)

        if not polls:
            table.add_row("--", "-", "-", "-", "-", "-", "-")
            return Panel(table, title="📈 轮询历史")

        for record in polls:
            poll_time = self._format_time(record.poll_time)
            table.add_row(
                poll_time,
                record.keyword or "-",
                str(record.new_count),
                str(record.success_count),
                str(record.failed_count),
                str(record.skipped_count),
                f"{record.elapsed_seconds:.2f}s",
            )

        return Panel(table, title="📈 轮询历史")

    @staticmethod
    def _render_footer() -> Panel:
        """渲染底部提示栏"""
        text = Text()
        text.append("[Q] ", style="bold cyan")
        text.append("退出  ", style="white")
        text.append("[R] ", style="bold cyan")
        text.append("立即运行  ", style="white")
        text.append("[P] ", style="bold cyan")
        text.append("暂停/继续", style="white")

        return Panel(text, style="dim")

    @staticmethod
    def _format_time(value: Optional[datetime], fallback: str = "--:--:--") -> str:
        """格式化时间为 HH:MM:SS 格式"""
        if value is None:
            return fallback
        return value.strftime("%H:%M:%S")

    @staticmethod
    def _format_uptime(seconds: float) -> str:
        """格式化运行时间"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

    @staticmethod
    def _limit_items(items: List[T], limit: Optional[int]) -> List[T]:
        """截断列表到指定长度"""
        if limit is None:
            return list(items)
        return list(items)[:limit]

    def _status_display(self) -> Tuple[str, str]:
        """获取状态显示文本和颜色"""
        status = self._state.status
        mapping = {
            "idle": ("空闲", "yellow"),
            "running": ("运行中", "green"),
            "paused": ("已暂停", "magenta"),
            "error": ("错误", "red"),
        }
        return mapping.get(status, (status, "white"))

    @staticmethod
    def _article_status_text(status: str) -> Text:
        """获取文章状态显示文本"""
        if status == "success":
            return Text("✅ 成功", style="green")
        if status == "failed":
            return Text("❌ 失败", style="red")
        return Text(status or "-", style="white")

    @staticmethod
    def _format_keywords(keywords: List[str], max_length: int = 60) -> str:
        """格式化关键词列表显示"""
        text = ", ".join(keywords)
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."
