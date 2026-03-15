from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from monitor.adapter import MonitorAdapter, MonitorStatus
from monitor.manager import MonitorManager
from monitor.unified_ui import UnifiedMonitorUI


class _DummyAdapter(MonitorAdapter):
    def __init__(
        self,
        name: str,
        *,
        status: MonitorStatus = MonitorStatus.IDLE,
        items_count: int = 0,
        total_items: int = 0,
        extra: dict | None = None,
    ) -> None:
        super().__init__(name=name)
        self.pause_calls = 0
        self.resume_calls = 0
        self.run_now_calls = 0
        self.start_calls = 0
        self.stop_calls = 0
        self._running = status == MonitorStatus.RUNNING
        self._state.status = status
        self._state.items_count = items_count
        self._state.total_items = total_items
        self._state.last_run = datetime(2026, 3, 15, 9, 30, 0)
        self._state.extra.update(extra or {})

    def _run(self):
        return None

    def start(self):
        self.start_calls += 1
        self._running = True
        self._state.status = MonitorStatus.RUNNING

    def stop(self, timeout: float = 10.0):
        del timeout
        self.stop_calls += 1
        self._running = False
        self._state.status = MonitorStatus.STOPPED

    def is_running(self) -> bool:
        return self._running

    def pause(self):
        self.pause_calls += 1
        self._state.status = MonitorStatus.PAUSED

    def resume(self):
        self.resume_calls += 1
        self._state.status = MonitorStatus.RUNNING

    def run_now(self):
        self.run_now_calls += 1
        self._state.last_run = datetime(2026, 3, 15, 9, 35, 0)


def test_monitor_manager_tracks_selected_source_and_controls_selected_adapter() -> None:
    manager = MonitorManager()
    longzhong = _DummyAdapter("隆众资讯", status=MonitorStatus.RUNNING)
    wallstreetcn = _DummyAdapter("华尔街见闻", status=MonitorStatus.IDLE)

    manager.register(longzhong)
    manager.register(wallstreetcn)

    assert manager.get_selected_name() == "隆众资讯"

    manager.select_next()
    assert manager.get_selected_name() == "华尔街见闻"

    manager.pause_selected()
    manager.run_selected_now()
    manager.resume_selected()
    manager.stop_selected(timeout=3.0)

    assert wallstreetcn.pause_calls == 1
    assert wallstreetcn.run_now_calls == 1
    assert wallstreetcn.resume_calls == 1
    assert wallstreetcn.stop_calls == 1

    manager.select_previous()
    assert manager.get_selected_name() == "隆众资讯"


def test_unified_ui_renders_summary_source_list_and_selected_details() -> None:
    manager = MonitorManager()
    manager.register(
        _DummyAdapter(
            "隆众资讯",
            status=MonitorStatus.RUNNING,
            items_count=3,
            total_items=10,
            extra={
                "keywords": ["原油", "甲醇", "PTA"],
                "interval": 30,
                "interval_unit": "minutes",
                "current_keyword": "原油",
            },
        )
    )
    manager.register(
        _DummyAdapter(
            "Investing.com",
            status=MonitorStatus.ERROR,
            items_count=2,
            total_items=8,
            extra={
                "channels": ["commodities", "economy"],
                "interval": 30,
                "interval_unit": "seconds",
                "proxy": "http://127.0.0.1:7897",
                "delay": 1.5,
                "max_pages": 5,
                "stats": {"commodities": 2, "economy": 0},
                "recent_items": [
                    {"title": "库存下降", "time": "09:31:00"},
                    {"title": "美元走强", "time": "09:32:00"},
                ],
            },
        )
    )

    manager.select_source("Investing.com")
    console = Console(record=True, width=120)
    ui = UnifiedMonitorUI(manager, refresh_rate=0.2, console=console)

    console.print(ui._create_layout())
    rendered = console.export_text()

    assert "统一监控控制台" in rendered
    assert "源列表" in rendered
    assert "当前选中" in rendered
    assert "Investing.com" in rendered
    assert "http://127.0.0.1:7897" in rendered
    assert "1.5" in rendered
    assert "5" in rendered
    assert "最近产出" in rendered
    assert "库存下降" in rendered


def test_unified_ui_renders_schedule_backoff_and_channel_stats_summary() -> None:
    manager = MonitorManager()
    manager.register(
        _DummyAdapter(
            "华尔街见闻",
            status=MonitorStatus.ERROR,
            items_count=1,
            total_items=12,
            extra={
                "channels": ["oil-channel", "gold-channel"],
                "interval": 30,
                "interval_unit": "seconds",
                "next_run_at": datetime(2026, 3, 15, 9, 31, 0),
                "last_success_at": datetime(2026, 3, 15, 9, 28, 15),
                "consecutive_failures": 2,
                "backoff_seconds": 10,
                "channel_stats": {
                    "oil-channel": 3,
                    "gold-channel": 1,
                },
                "recent_items": [
                    {"title": "油价拉升", "time": "09:30:58"},
                ],
            },
        )
    )

    console = Console(record=True, width=120)
    ui = UnifiedMonitorUI(manager, refresh_rate=0.2, console=console)

    console.print(ui._create_layout())
    rendered = console.export_text()

    assert "调度状态" in rendered
    assert "09:31:00" in rendered
    assert "09:28:15" in rendered
    assert "失败退避" in rendered
    assert "连续失败 2" in rendered
    assert "退避 10s" in rendered
    assert "频道统计" in rendered
    assert "oil-channel:3" in rendered
    assert "gold-channel:1" in rendered
