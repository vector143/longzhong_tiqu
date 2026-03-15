from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from monitor import adapters as module
from monitor.adapter import MonitorStatus


def test_wallstreetcn_adapter_uses_runtime_project_relative_output_dir() -> None:
    adapter = module.WallStreetCNAdapter(channels=["oil-channel"])

    expected_dir = (
        Path(module.__file__).resolve().parent.parent / "output" / "report" / "cleaned"
    )
    assert Path(adapter.output_dir) == expected_dir


def test_wallstreetcn_adapter_exposes_detail_metadata() -> None:
    adapter = module.WallStreetCNAdapter(
        channels=["oil-channel", "gold-channel"],
        important_only=True,
    )

    state = adapter.get_state()
    assert state.extra["important_only"] is True
    assert state.extra["output_dir"] == adapter.output_dir
    assert state.extra["channel_stats"] == {}


def test_investing_adapter_marks_interval_unit_as_seconds() -> None:
    adapter = module.InvestingAdapter(channels=["economy"], interval=30)

    assert adapter.get_state().extra["interval_unit"] == "seconds"


def test_investing_adapter_uses_configurable_delay_and_max_pages(monkeypatch) -> None:
    captured = {}
    adapter = module.InvestingAdapter(
        channels=["economy"],
        interval=30,
        delay=1.5,
        max_pages=5,
    )

    monkeypatch.setattr(
        adapter,
        "wait_interval",
        lambda _seconds, poll_interval=0.2: False,
    )
    monkeypatch.setattr(
        adapter._monitor,
        "crawl_incremental",
        lambda channels, delay, max_pages: captured.update(
            {
                "channels": channels,
                "delay": delay,
                "max_pages": max_pages,
            }
        )
        or {"economy": 2},
    )

    adapter._run()

    assert captured == {
        "channels": ["economy"],
        "delay": 1.5,
        "max_pages": 5,
    }
    state = adapter.get_state()
    assert state.extra["delay"] == 1.5
    assert state.extra["max_pages"] == 5


def test_longzhong_adapter_marks_interval_unit_as_minutes() -> None:
    adapter = module.LongZhongAdapter(keywords=["原油"], interval=30)

    assert adapter.get_state().extra["interval_unit"] == "minutes"


def test_longzhong_adapter_delegates_control_to_embedded_runtime() -> None:
    class _DummyController:
        def __init__(self) -> None:
            self.pause_calls = 0
            self.resume_calls = 0
            self.run_now_calls = 0
            self.is_paused = False
            self.is_running = True

        def pause(self) -> None:
            self.pause_calls += 1
            self.is_paused = True

        def resume(self) -> None:
            self.resume_calls += 1
            self.is_paused = False

        def run_now(self) -> None:
            self.run_now_calls += 1

    controller = _DummyController()
    adapter = module.LongZhongAdapter(keywords=["原油"], interval=30)
    adapter._runtime = type("Runtime", (), {"controller": controller})()

    adapter.pause()
    adapter.resume()
    adapter.run_now()

    assert controller.pause_calls == 1
    assert controller.resume_calls == 1
    assert controller.run_now_calls == 1


def test_longzhong_adapter_maps_embedded_runtime_snapshot_to_unified_state() -> None:
    snapshot = {
        "status": "running",
        "last_error": None,
        "next_poll_time": datetime(2026, 3, 15, 9, 45, 0),
        "today_total": 7,
        "today_success": 5,
        "today_failed": 1,
        "today_skipped": 1,
        "total_polls": 3,
        "uptime_seconds": 120.0,
        "recent_articles": [
            type(
                "Article",
                (),
                {
                    "keyword": "原油",
                    "title": "测试文章",
                    "crawl_time": datetime(2026, 3, 15, 9, 31, 0),
                    "publish_time": "2026-03-15 09:30:00",
                },
            )()
        ],
        "poll_history": [
            type(
                "Poll",
                (),
                {
                    "keyword": "原油",
                    "poll_time": datetime(2026, 3, 15, 9, 32, 0),
                    "new_count": 4,
                    "success_count": 4,
                    "failed_count": 0,
                    "skipped_count": 1,
                    "elapsed_seconds": 2.5,
                },
            )()
        ],
    }

    class _DummyState:
        def get_snapshot(self):
            return snapshot

    adapter = module.LongZhongAdapter(keywords=["原油"], interval=30)
    adapter._runtime = type(
        "Runtime", (), {"state": _DummyState(), "controller": None}
    )()

    state = adapter.get_state()

    assert state.status == MonitorStatus.RUNNING
    assert state.items_count == 4
    assert state.total_items == 5
    assert state.last_run == datetime(2026, 3, 15, 9, 32, 0)
    assert state.extra["recent_items"][0]["title"] == "测试文章"
