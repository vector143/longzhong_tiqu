"""
统一监控 Rich UI 界面

提供：
- 全局汇总
- 源列表
- 当前选中源详情
- 最近产出
- 快捷键控制
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Iterable, Optional

from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from monitor.adapter import MonitorState, MonitorStatus
from monitor.keyboard import KeyboardListener
from monitor.manager import MonitorManager


class UnifiedMonitorUI:
    """统一监控控制台"""

    def __init__(
        self,
        manager: MonitorManager,
        refresh_rate: float = 0.2,
        console: Optional[Console] = None,
        keyboard_listener: Optional[KeyboardListener] = None,
    ):
        if refresh_rate <= 0:
            raise ValueError("refresh_rate 必须为正数")

        self.manager = manager
        self.refresh_rate = refresh_rate
        self.console = console or Console()
        self._keyboard = keyboard_listener or KeyboardListener()
        self._keys_registered = False
        self._start_time = datetime.now()
        self._should_exit = False

    def _register_keys(self) -> None:
        if self._keys_registered:
            return

        self._keyboard.register_key("q", self._on_quit)
        self._keyboard.register_key("Q", self._on_quit)
        self._keyboard.register_key("j", self._on_select_next)
        self._keyboard.register_key("J", self._on_select_next)
        self._keyboard.register_key("k", self._on_select_previous)
        self._keyboard.register_key("K", self._on_select_previous)
        self._keyboard.register_key("r", self._on_run_now)
        self._keyboard.register_key("R", self._on_run_now)
        self._keyboard.register_key("p", self._on_toggle_pause)
        self._keyboard.register_key("P", self._on_toggle_pause)
        self._keyboard.register_key("s", self._on_stop_selected)
        self._keyboard.register_key("S", self._on_stop_selected)
        self._keys_registered = True

    def _on_quit(self) -> None:
        self._should_exit = True
        self.manager.stop_all(timeout=10.0)

    def _on_select_next(self) -> None:
        self.manager.select_next()

    def _on_select_previous(self) -> None:
        self.manager.select_previous()

    def _on_run_now(self) -> None:
        self.manager.run_selected_now()

    def _on_toggle_pause(self) -> None:
        self.manager.toggle_selected_pause()

    def _on_stop_selected(self) -> None:
        self.manager.stop_selected(timeout=10.0)

    def _create_header(self) -> Panel:
        uptime = datetime.now() - self._start_time
        total_seconds = int(uptime.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        summary = self.manager.get_summary()

        text = Text()
        text.append("统一监控控制台", style="bold cyan")
        text.append(
            f" | 运行时间 {hours:02d}:{minutes:02d}:{seconds:02d}", style="green"
        )
        text.append(f" | 监控源 {summary['sources']}", style="yellow")
        text.append(f" | 运行中 {summary['running']}", style="green")
        if summary["paused"] > 0:
            text.append(f" | 已暂停 {summary['paused']}", style="yellow")
        if summary["errors"] > 0:
            text.append(f" | 错误 {summary['errors']}", style="red bold")
        text.append(f" | 总采集 {summary['total_items']}", style="cyan")

        return Panel(text, style="bold white on blue")

    def _create_source_list(self) -> Panel:
        table = Table(box=box.SIMPLE_HEAVY, expand=True)
        table.add_column("", width=2)
        table.add_column("监控源", overflow="fold")
        table.add_column("状态", justify="center", width=10)
        table.add_column("本轮", justify="right", width=6)
        table.add_column("累计", justify="right", width=6)

        selected_name = self.manager.get_selected_name()
        for name, state in self.manager.get_all_states().items():
            marker = "▶" if name == selected_name else " "
            table.add_row(
                marker,
                name,
                self._status_text(state),
                str(state.items_count),
                str(state.total_items),
            )

        if not table.rows:
            table.add_row("-", "暂无监控源", "-", "-", "-")

        return Panel(table, title="源列表", border_style="cyan")

    def _create_selected_detail(self) -> Panel:
        selected_name = self.manager.get_selected_name()
        if selected_name is None:
            return Panel("暂无选中监控源", title="当前选中", border_style="yellow")

        state = self.manager.get_selected_state()
        table = Table(show_header=False, box=box.SIMPLE, expand=True)
        table.add_column("字段", style="cyan", width=14)
        table.add_column("值", style="white")

        table.add_row("当前选中", selected_name)
        table.add_row("状态", self._status_text(state))
        table.add_row("最后运行", self._format_datetime(state.last_run))
        table.add_row("运行时长", self._format_running_time(state.running_time))
        table.add_row("轮询间隔", self._format_interval(state))
        table.add_row("本轮采集", str(state.items_count))
        table.add_row("累计采集", str(state.total_items))

        for label, value in self._iter_detail_rows(state):
            table.add_row(label, value)

        subtitle = None
        if state.last_error:
            subtitle = f"错误: {state.last_error[:70]}"

        return Panel(table, title="当前选中", subtitle=subtitle, border_style="green")

    def _create_recent_items(self) -> Panel:
        selected_name = self.manager.get_selected_name()
        if selected_name is None:
            return Panel("暂无产出", title="最近产出", border_style="yellow")

        state = self.manager.get_selected_state()
        items = state.extra.get("recent_items") or state.extra.get("last_items") or []
        stats = state.extra.get("stats")

        table = Table(box=box.SIMPLE_HEAVY, expand=True)
        table.add_column("时间", width=10, justify="center")
        table.add_column("内容", overflow="fold")

        if items:
            for item in items[:8]:
                table.add_row(str(item.get("time", "--")), str(item.get("title", "-")))
        elif isinstance(stats, dict) and stats:
            for channel, count in list(stats.items())[:8]:
                table.add_row("统计", f"{channel}: {count}")
        else:
            table.add_row("--", "暂无产出")

        return Panel(table, title="最近产出", border_style="magenta")

    def _create_footer(self) -> Panel:
        text = Text()
        text.append("[J/K] ", style="bold cyan")
        text.append("切换源  ", style="white")
        text.append("[R] ", style="bold cyan")
        text.append("立即运行  ", style="white")
        text.append("[P] ", style="bold cyan")
        text.append("暂停/继续  ", style="white")
        text.append("[S] ", style="bold cyan")
        text.append("停止当前源  ", style="white")
        text.append("[Q] ", style="bold cyan")
        text.append("退出并停止全部", style="white")
        return Panel(text, style="dim")

    def _create_layout(self) -> Layout:
        layout = Layout(name="root")
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=3),
        )
        layout["body"].split_row(
            Layout(name="sources", size=42),
            Layout(name="details", ratio=1),
        )
        layout["details"].split_column(
            Layout(name="selected", ratio=3),
            Layout(name="recent", ratio=2),
        )

        layout["header"].update(self._create_header())
        layout["sources"].update(self._create_source_list())
        layout["selected"].update(self._create_selected_detail())
        layout["recent"].update(self._create_recent_items())
        layout["footer"].update(self._create_footer())
        return layout

    def run(self):
        self._should_exit = False
        self._register_keys()

        if not self._keyboard.is_running:
            self._keyboard.start()

        try:
            with Live(
                self._create_layout(),
                console=self.console,
                refresh_per_second=1.0 / self.refresh_rate,
                screen=True,
            ) as live:
                while not self._should_exit:
                    live.update(self._create_layout())
                    if not self.manager.is_any_running():
                        break
                    time.sleep(self.refresh_rate)

                live.update(self._create_layout())
                time.sleep(min(self.refresh_rate, 1.0))

        except KeyboardInterrupt:
            self.manager.stop_all(timeout=10.0)
            self.console.print("\n[yellow]⚠️ 收到停止信号，正在停止所有监控...[/]")
        finally:
            self._keyboard.stop()

    @staticmethod
    def _format_datetime(value: Optional[datetime]) -> str:
        if value is None:
            return "--:--:--"
        return value.strftime("%H:%M:%S")

    @staticmethod
    def _format_running_time(seconds: float) -> str:
        if seconds <= 0:
            return "--"
        total_seconds = int(seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    @staticmethod
    def _status_text(state: MonitorState) -> str:
        mapping = {
            MonitorStatus.RUNNING: "[green]运行中[/green]",
            MonitorStatus.IDLE: "[yellow]空闲[/yellow]",
            MonitorStatus.PAUSED: "[yellow]已暂停[/yellow]",
            MonitorStatus.ERROR: "[red]错误[/red]",
            MonitorStatus.STOPPED: "[dim]已停止[/dim]",
        }
        return mapping.get(state.status, state.status.value)

    @staticmethod
    def _format_interval(state: MonitorState) -> str:
        interval = state.extra.get("interval")
        if interval is None:
            return "--"

        unit = state.extra.get("interval_unit")
        if unit == "minutes":
            return f"{interval} 分钟"
        if unit == "hours":
            return f"{interval} 小时"
        return f"{interval} 秒"

    @staticmethod
    def _join_values(values: Iterable[str], limit: int = 4) -> str:
        items = [str(value) for value in values]
        if len(items) <= limit:
            return ", ".join(items)
        return ", ".join(items[:limit]) + "..."

    def _iter_detail_rows(self, state: MonitorState):
        extra = state.extra
        if "keywords" in extra and isinstance(extra["keywords"], list):
            yield "关键词", self._join_values(extra["keywords"])
        if "proxy" in extra and extra["proxy"]:
            yield "代理", str(extra["proxy"])
        if "current_keyword" in extra:
            yield "当前关键词", str(extra["current_keyword"])
        if "channels" in extra and isinstance(extra["channels"], list):
            yield "频道", self._join_values(extra["channels"])
        if "last_channel" in extra:
            yield "最后频道", str(extra["last_channel"])
