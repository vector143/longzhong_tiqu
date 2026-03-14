"""
统一监控 Rich UI 界面

提供美观的终端界面，实时展示多个监控源的状态
"""

import time
from datetime import datetime
from typing import Dict

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from monitor.adapter import MonitorState, MonitorStatus
from monitor.manager import MonitorManager


class UnifiedMonitorUI:
    """统一监控 UI"""

    def __init__(self, manager: MonitorManager, refresh_rate: float = 0.2):
        """
        初始化 UI

        Args:
            manager: 监控管理器
            refresh_rate: 刷新率（秒），默认 0.2 秒（5 FPS）
        """
        self.manager = manager
        self.refresh_rate = refresh_rate
        self.console = Console()
        self._start_time = datetime.now()
        self._total_items = 0

    def _create_header(self) -> Panel:
        """创建头部面板"""
        running_time = (datetime.now() - self._start_time).total_seconds()
        hours = int(running_time // 3600)
        minutes = int((running_time % 3600) // 60)
        seconds = int(running_time % 60)

        states = self.manager.get_all_states()
        total_items = sum(state.total_items for state in states.values())
        running_count = sum(
            1 for state in states.values() if state.status == MonitorStatus.RUNNING
        )
        error_count = sum(
            1 for state in states.values() if state.status == MonitorStatus.ERROR
        )

        header_text = Text()
        header_text.append("🎯 统一监控系统", style="bold cyan")
        header_text.append(
            f" | 运行时间: {hours:02d}:{minutes:02d}:{seconds:02d}", style="green"
        )
        header_text.append(f" | 监控源: {len(states)}", style="yellow")
        header_text.append(f" | 运行中: {running_count}", style="green")
        if error_count > 0:
            header_text.append(f" | 错误: {error_count}", style="red bold")
        header_text.append(f" | 总采集: {total_items}", style="cyan")

        return Panel(header_text, style="bold white on blue")

    def _create_monitor_table(self, name: str, state: MonitorState) -> Table:
        """创建单个监控的表格"""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Key", style="cyan", width=15)
        table.add_column("Value", style="white")

        # 状态
        status_style = {
            MonitorStatus.RUNNING: "green",
            MonitorStatus.IDLE: "yellow",
            MonitorStatus.PAUSED: "yellow",
            MonitorStatus.ERROR: "red bold",
            MonitorStatus.STOPPED: "dim",
        }.get(state.status, "white")

        status_icon = {
            MonitorStatus.RUNNING: "🟢",
            MonitorStatus.IDLE: "🟡",
            MonitorStatus.PAUSED: "🟡",
            MonitorStatus.ERROR: "🔴",
            MonitorStatus.STOPPED: "⚫",
        }.get(state.status, "⚪")

        table.add_row("状态", f"{status_icon} [{status_style}]{state.status.value}[/]")

        # 运行时间
        if state.running_time > 0:
            hours = int(state.running_time // 3600)
            minutes = int((state.running_time % 3600) // 60)
            seconds = int(state.running_time % 60)
            table.add_row("运行时间", f"{hours:02d}:{minutes:02d}:{seconds:02d}")

        # 采集数据
        table.add_row("本轮采集", f"{state.items_count}")
        table.add_row("总计采集", f"{state.total_items}")

        # 最后运行
        if state.last_run:
            last_run_str = state.last_run.strftime("%H:%M:%S")
            table.add_row("最后运行", last_run_str)

        # 扩展信息
        if "channels" in state.extra:
            channels = state.extra["channels"]
            if isinstance(channels, list):
                table.add_row("频道数", str(len(channels)))

        if "keywords" in state.extra:
            keywords = state.extra["keywords"]
            if isinstance(keywords, list):
                table.add_row("关键词", ", ".join(keywords[:3]))

        if "interval" in state.extra:
            table.add_row("轮询间隔", f"{state.extra['interval']}秒")

        # 错误信息
        if state.last_error:
            error_text = (
                state.last_error[:50] + "..."
                if len(state.last_error) > 50
                else state.last_error
            )
            table.add_row("错误", f"[red]{error_text}[/]")

        return table

    def _create_monitor_panels(self) -> Dict[str, Panel]:
        """创建所有监控面板"""
        states = self.manager.get_all_states()
        panels = {}

        for name, state in states.items():
            table = self._create_monitor_table(name, state)

            # 根据状态选择边框颜色
            border_style = {
                MonitorStatus.RUNNING: "green",
                MonitorStatus.ERROR: "red",
                MonitorStatus.IDLE: "yellow",
                MonitorStatus.STOPPED: "dim",
            }.get(state.status, "white")

            panels[name] = Panel(
                table,
                title=f"[bold]{name}[/]",
                border_style=border_style,
            )

        return panels

    def _create_footer(self) -> Panel:
        """创建底部面板"""
        footer_text = Text()
        footer_text.append("💡 提示: ", style="bold yellow")
        footer_text.append("按 ", style="dim")
        footer_text.append("Ctrl+C", style="bold red")
        footer_text.append(" 停止所有监控", style="dim")

        return Panel(footer_text, style="dim white on black")

    def _create_layout(self) -> Layout:
        """创建布局"""
        layout = Layout()

        # 分割布局
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )

        # 头部
        layout["header"].update(self._create_header())

        # 主体 - 根据监控数量动态分割
        panels = self._create_monitor_panels()

        if len(panels) == 1:
            layout["body"].update(list(panels.values())[0])
        elif len(panels) == 2:
            layout["body"].split_row(*panels.values())
        elif len(panels) == 3:
            layout["body"].split_row(*panels.values())
        else:
            # 超过3个，分两行
            layout["body"].split_column(
                Layout(name="row1"),
                Layout(name="row2"),
            )
            panel_list = list(panels.values())
            mid = len(panel_list) // 2
            layout["body"]["row1"].split_row(*panel_list[:mid])
            layout["body"]["row2"].split_row(*panel_list[mid:])

        # 底部
        layout["footer"].update(self._create_footer())

        return layout

    def run(self):
        """运行 UI"""
        try:
            with Live(
                self._create_layout(),
                console=self.console,
                refresh_per_second=1.0 / self.refresh_rate,
                screen=True,
            ) as live:
                while self.manager.is_any_running():
                    live.update(self._create_layout())
                    time.sleep(self.refresh_rate)

                # 最后更新一次显示停止状态
                live.update(self._create_layout())
                time.sleep(1)

        except KeyboardInterrupt:
            self.console.print("\n[yellow]⚠️ 收到停止信号，正在停止所有监控...[/]")
            self.manager.stop_all(timeout=10.0)
            self.console.print("[green]✅ 所有监控已停止[/]")
