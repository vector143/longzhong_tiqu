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

    def _create_download_stats(self) -> Panel:
        states = self.manager.get_all_states()
        table = Table(box=box.SIMPLE_HEAVY, expand=True)
        table.add_column("来源", width=14, no_wrap=True, overflow="ellipsis")
        table.add_column("本轮", justify="right", width=4)
        table.add_column("累计", justify="right", width=6)
        table.add_column("占比", justify="right", width=6)

        total_downloaded = sum(state.total_items for state in states.values())
        if not states:
            table.add_row("暂无监控源", "-", "-", "-")
        else:
            for name, state in states.items():
                ratio = (
                    f"{(state.total_items / total_downloaded) * 100:.1f}%"
                    if total_downloaded > 0
                    else "0.0%"
                )
                table.add_row(
                    name,
                    str(state.items_count),
                    str(state.total_items),
                    ratio,
                )

        return Panel(table, title="下载统计", border_style="blue")

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
        table.add_row("轮询间隔", self._format_interval(state))
        table.add_row(
            "运行概览",
            (
                f"最后运行 {self._format_datetime(state.last_run)} | "
                f"运行时长 {self._format_running_time(state.running_time)}"
            ),
        )
        table.add_row(
            "采集统计",
            f"本轮 {state.items_count} | 累计 {state.total_items}",
        )

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
        stats = state.extra.get("channel_stats") or state.extra.get("stats")

        table = Table(box=box.SIMPLE_HEAVY, expand=True)
        table.add_column("时间", width=10, justify="center")
        table.add_column("内容", overflow="fold")

        if items:
            summary = self._build_channel_stats_summary(state)
            if summary:
                table.add_row("频道统计", summary)
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
        layout["sources"].split_column(
            Layout(name="source_list", ratio=3),
            Layout(name="download_stats", ratio=2),
        )
        layout["details"].split_column(
            Layout(name="selected", ratio=3),
            Layout(name="recent", ratio=2),
        )

        layout["header"].update(self._create_header())
        layout["source_list"].update(self._create_source_list())
        layout["download_stats"].update(self._create_download_stats())
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

    @classmethod
    def _format_extra_datetime(cls, value) -> str:
        if isinstance(value, datetime):
            return cls._format_datetime(value)
        if value in (None, ""):
            return "--:--:--"
        return str(value)

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

    @staticmethod
    def _format_seconds(value) -> str:
        if value in (None, ""):
            return "0s"
        number = float(value)
        if number.is_integer():
            return f"{int(number)}s"
        return f"{number:.1f}s"

    def _build_channel_stats_summary(self, state: MonitorState) -> Optional[str]:
        stats = state.extra.get("channel_stats") or state.extra.get("stats")
        if not isinstance(stats, dict) or not stats:
            return None
        pairs = [f"{channel}:{count}" for channel, count in stats.items()]
        return self._join_values(pairs, limit=3)

    def _build_runtime_control_summary(self, state: MonitorState) -> Optional[str]:
        extra = state.extra
        runtime_mode = extra.get("runtime_mode")
        runtime_status = extra.get("runtime_status")
        worker_count = extra.get("runtime_worker_count")
        active_workers = extra.get("runtime_active_workers")

        if runtime_mode is None and runtime_status is None:
            return None

        parts = []
        if runtime_mode is not None:
            parts.append(str(runtime_mode))
        if runtime_status is not None:
            parts.append(str(runtime_status))
        if worker_count is not None:
            active = 0 if active_workers is None else active_workers
            parts.append(f"worker {active}/{worker_count}")
        if int(extra.get("runtime_restarts", 0)) > 0:
            parts.append(f"重启 {extra['runtime_restarts']}")
        return " | ".join(parts)

    def _iter_detail_rows(self, state: MonitorState):
        extra = state.extra
        runtime_summary = self._build_runtime_control_summary(state)
        if runtime_summary:
            yield "运行控制", runtime_summary

        schedule_parts = []
        next_run_at = extra.get("next_run_at") or extra.get("next_poll_time")
        if next_run_at is not None:
            schedule_parts.append(f"下次 {self._format_extra_datetime(next_run_at)}")
        if extra.get("last_success_at") is not None:
            schedule_parts.append(
                f"上次成功 {self._format_extra_datetime(extra['last_success_at'])}"
            )
        if schedule_parts:
            yield "调度状态", " | ".join(schedule_parts)

        failure_parts = []
        if int(extra.get("consecutive_failures", 0)) > 0:
            failure_parts.append(f"连续失败 {extra['consecutive_failures']}")
        if float(extra.get("backoff_seconds", 0) or 0) > 0:
            failure_parts.append(
                f"退避 {self._format_seconds(extra['backoff_seconds'])}"
            )
        if failure_parts:
            yield "失败退避", " | ".join(failure_parts)

        if "keywords" in extra and isinstance(extra["keywords"], list):
            yield "关键词", self._join_values(extra["keywords"])

        runtime_parts = []
        if "important_only" in extra:
            runtime_parts.append(
                "仅重要快讯" if extra["important_only"] else "全部快讯"
            )
        if "proxy" in extra and extra["proxy"]:
            runtime_parts.append(f"代理 {extra['proxy']}")
        if "delay" in extra:
            runtime_parts.append(f"延迟 {self._format_seconds(extra['delay'])}")
        if "max_pages" in extra:
            runtime_parts.append(f"翻页 {extra['max_pages']}")
        if runtime_parts:
            yield "运行参数", " | ".join(runtime_parts)

        if "output_dir" in extra and extra["output_dir"]:
            yield "输出目录", str(extra["output_dir"])
        if "current_keyword" in extra:
            yield "当前关键词", str(extra["current_keyword"])
        if "channels" in extra and isinstance(extra["channels"], list):
            yield "频道", self._join_values(extra["channels"])
        if "last_channel" in extra:
            yield "最后频道", str(extra["last_channel"])
