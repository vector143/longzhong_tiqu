from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from monitor import adapter as adapter_module
from monitor import adapters as module
from monitor.adapter import MonitorStatus


class _FakeThread:
    def __init__(self, target=None, daemon=None):
        self.target = target
        self.daemon = daemon
        self._alive = False

    def start(self) -> None:
        self._alive = True

    def is_alive(self) -> bool:
        return self._alive

    def join(self, timeout=None) -> None:
        del timeout
        self._alive = False


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


def test_wallstreetcn_adapter_records_standard_runtime_state_for_channel_poll() -> None:
    adapter = module.WallStreetCNAdapter(
        channels=["oil-channel", "gold-channel"],
        interval=30,
    )
    started_at = datetime(2026, 3, 15, 9, 30, 0)
    finished_at = datetime(2026, 3, 15, 9, 30, 2)
    next_run_at = datetime(2026, 3, 15, 9, 30, 32)

    adapter._record_channel_poll_result(
        channel="oil-channel",
        started_at=started_at,
        finished_at=finished_at,
        new_count=2,
        next_run_at=next_run_at,
    )

    state = adapter.get_state()
    assert state.last_run == finished_at
    assert state.extra["last_success_at"] == finished_at
    assert state.extra["last_poll_started_at"] == started_at
    assert state.extra["last_poll_finished_at"] == finished_at
    assert state.extra["last_round_duration_seconds"] == 2.0
    assert state.extra["last_round_new"] == 2
    assert state.extra["next_run_at"] == next_run_at
    assert state.extra["channel_statuses"]["oil-channel"] == "running"
    assert state.extra["failed_channels"] == []


def test_wallstreetcn_adapter_run_now_broadcasts_to_all_channels() -> None:
    adapter = module.WallStreetCNAdapter(
        channels=["oil-channel", "gold-channel"],
        interval=30,
    )

    assert adapter._consume_run_now_broadcast(0) is None

    adapter.run_now()

    assert adapter._consume_run_now_broadcast(0) == 1
    assert adapter._consume_run_now_broadcast(0) == 1
    assert adapter._consume_run_now_broadcast(1) is None


def test_wallstreetcn_adapter_on_new_items_updates_state_under_lock() -> None:
    class _CountingLock:
        def __init__(self) -> None:
            self.enter_count = 0

        def __enter__(self):
            self.enter_count += 1
            return self

        def __exit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

    adapter = module.WallStreetCNAdapter(
        channels=["oil-channel", "gold-channel"],
        interval=30,
    )
    counting_lock = _CountingLock()
    adapter._state_lock = counting_lock

    adapter._on_new_items(
        "oil-channel",
        [
            {"title": "快讯A", "display_time_str": "2026-03-16 10:00:00"},
            {"title": "快讯B", "display_time_str": "2026-03-16 10:01:00"},
        ],
    )

    assert counting_lock.enter_count >= 1
    state = adapter.get_state()
    assert state.total_items == 2
    assert state.extra["channel_stats"]["oil-channel"] == 2


def test_wallstreetcn_adapter_tracks_runtime_lifecycle_on_start_and_stop(
    monkeypatch,
) -> None:
    adapter = module.WallStreetCNAdapter(
        channels=["oil-channel", "gold-channel"],
        interval=30,
    )

    monkeypatch.setattr(adapter_module, "Thread", _FakeThread)

    adapter.start()
    running_state = adapter.get_state()

    assert running_state.extra["runtime_mode"] == "multi-thread"
    assert running_state.extra["runtime_status"] == "starting"
    assert running_state.extra["runtime_worker_count"] == 2
    assert running_state.extra["runtime_active_workers"] == 2
    assert running_state.extra["runtime_restarts"] == 0
    assert running_state.extra["runtime_controller_ready"] is True

    adapter.stop()
    stopped_state = adapter.get_state()

    assert stopped_state.status == MonitorStatus.STOPPED
    assert stopped_state.extra["runtime_status"] == "stopped"
    assert stopped_state.extra["runtime_active_workers"] == 0
    assert stopped_state.extra["runtime_last_stopped_at"] is not None


def test_investing_adapter_marks_interval_unit_as_seconds() -> None:
    adapter = module.InvestingAdapter(channels=["economy"], interval=30)

    assert adapter.get_state().extra["interval_unit"] == "seconds"


def test_investing_adapter_passes_workers_and_rate_limit_to_monitor_constructor(
    monkeypatch,
) -> None:
    captured = {}

    class _DummyInvestingMonitor:
        def __init__(
            self,
            output_dir=None,
            proxy=None,
            max_workers=5,
            rate_limit=1.0,
        ) -> None:
            captured.update(
                {
                    "output_dir": output_dir,
                    "proxy": proxy,
                    "max_workers": max_workers,
                    "rate_limit": rate_limit,
                }
            )

    monkeypatch.setattr(module, "InvestingMonitor", _DummyInvestingMonitor)
    adapter = module.InvestingAdapter(
        channels=["economy"],
        interval=30,
        proxy="http://127.0.0.1:7897",
        delay=1.5,
        max_pages=5,
        workers=2,
    )

    assert captured["proxy"] == "http://127.0.0.1:7897"
    assert captured["max_workers"] == 2
    assert captured["rate_limit"] == 1.5
    assert adapter.get_state().extra["workers"] == 2


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


def test_investing_adapter_tracks_standard_runtime_state_on_success(
    monkeypatch,
) -> None:
    started_at = datetime(2026, 3, 15, 9, 30, 0)
    finished_at = datetime(2026, 3, 15, 9, 30, 2)

    class _FakeDatetime:
        values = [started_at, finished_at]

        @classmethod
        def now(cls):
            if cls.values:
                return cls.values.pop(0)
            return finished_at

    adapter = module.InvestingAdapter(
        channels=["commodities", "economy"],
        interval=30,
        delay=1.5,
        max_pages=5,
    )

    monkeypatch.setattr(module, "datetime", _FakeDatetime)
    monkeypatch.setattr(
        adapter,
        "wait_interval",
        lambda _seconds, poll_interval=0.2: False,
    )
    monkeypatch.setattr(
        adapter._monitor,
        "crawl_incremental",
        lambda channels, delay, max_pages: {
            "commodities": 2,
            "economy": 0,
        },
    )

    adapter._run()

    state = adapter.get_state()
    assert state.last_run == finished_at
    assert state.extra["last_poll_started_at"] == started_at
    assert state.extra["last_poll_finished_at"] == finished_at
    assert state.extra["last_success_at"] == finished_at
    assert state.extra["last_round_duration_seconds"] == 2.0
    assert state.extra["last_round_new"] == 2
    assert state.extra["next_run_at"] == finished_at + timedelta(seconds=30)
    assert state.extra["channel_stats"] == {"commodities": 2, "economy": 0}
    assert state.extra["active_channels"] == ["commodities"]
    assert state.extra["consecutive_failures"] == 0
    assert state.extra["backoff_seconds"] == 0


def test_investing_adapter_uses_adaptive_interval_when_idle(monkeypatch) -> None:
    started_at = datetime(2026, 3, 16, 9, 30, 0)
    finished_at = datetime(2026, 3, 16, 9, 30, 2)
    wait_calls = []

    class _FakeDatetime:
        values = [started_at, finished_at]

        @classmethod
        def now(cls):
            if cls.values:
                return cls.values.pop(0)
            return finished_at

    adapter = module.InvestingAdapter(
        channels=["economy"],
        interval=30,
        delay=1.5,
        max_pages=5,
        adaptive_interval=True,
        max_interval=120,
    )

    monkeypatch.setattr(module, "datetime", _FakeDatetime)
    monkeypatch.setattr(
        adapter,
        "wait_interval",
        lambda seconds, poll_interval=0.2: wait_calls.append(seconds) or False,
    )
    monkeypatch.setattr(
        adapter._monitor,
        "crawl_incremental",
        lambda channels, delay, max_pages: {"economy": 0},
    )

    adapter._run()

    state = adapter.get_state()
    assert wait_calls == [60]
    assert state.extra["adaptive_interval"] is True
    assert state.extra["adaptive_idle_rounds"] == 1
    assert state.extra["adaptive_next_interval"] == 60
    assert state.extra["next_run_at"] == finished_at + timedelta(seconds=60)


def test_investing_adapter_resets_adaptive_interval_after_new_items(
    monkeypatch,
) -> None:
    first_started_at = datetime(2026, 3, 16, 9, 30, 0)
    first_finished_at = datetime(2026, 3, 16, 9, 30, 2)
    second_started_at = datetime(2026, 3, 16, 9, 31, 2)
    second_finished_at = datetime(2026, 3, 16, 9, 31, 4)
    wait_calls = []
    wait_results = iter([True, False])
    stats_results = iter([{"economy": 0}, {"economy": 2}])

    class _FakeDatetime:
        values = [
            first_started_at,
            first_finished_at,
            second_started_at,
            second_finished_at,
        ]

        @classmethod
        def now(cls):
            if cls.values:
                return cls.values.pop(0)
            return second_finished_at

    adapter = module.InvestingAdapter(
        channels=["economy"],
        interval=30,
        delay=1.5,
        max_pages=5,
        adaptive_interval=True,
        max_interval=120,
    )

    monkeypatch.setattr(module, "datetime", _FakeDatetime)
    monkeypatch.setattr(
        adapter,
        "wait_interval",
        lambda seconds, poll_interval=0.2: wait_calls.append(seconds)
        or next(wait_results),
    )
    monkeypatch.setattr(
        adapter._monitor,
        "crawl_incremental",
        lambda channels, delay, max_pages: next(stats_results),
    )

    adapter._run()

    state = adapter.get_state()
    assert wait_calls == [60, 30]
    assert state.extra["adaptive_idle_rounds"] == 0
    assert state.extra["adaptive_next_interval"] == 30
    assert state.extra["next_run_at"] == second_finished_at + timedelta(seconds=30)


def test_investing_adapter_tracks_backoff_state_on_failure(monkeypatch) -> None:
    failed_at = datetime(2026, 3, 15, 9, 30, 5)

    class _FakeDatetime:
        values = [failed_at, failed_at]

        @classmethod
        def now(cls):
            if cls.values:
                return cls.values.pop(0)
            return failed_at

    adapter = module.InvestingAdapter(
        channels=["economy"],
        interval=30,
        delay=1.5,
        max_pages=5,
    )

    monkeypatch.setattr(module, "datetime", _FakeDatetime)
    monkeypatch.setattr(
        adapter,
        "wait_interval",
        lambda _seconds, poll_interval=0.2: False,
    )

    def _raise_error(channels, delay, max_pages):
        del channels, delay, max_pages
        raise RuntimeError("boom")

    monkeypatch.setattr(adapter._monitor, "crawl_incremental", _raise_error)

    adapter._run()

    state = adapter.get_state()
    assert state.status == MonitorStatus.ERROR
    assert state.last_error == "Investing: boom"
    assert state.extra["last_poll_started_at"] == failed_at
    assert state.extra["last_poll_finished_at"] == failed_at
    assert state.extra["next_run_at"] == failed_at + timedelta(seconds=10)
    assert state.extra["consecutive_failures"] == 1
    assert state.extra["backoff_seconds"] == 10


def test_investing_adapter_restart_resets_runtime_and_failure_state(
    monkeypatch,
) -> None:
    adapter = module.InvestingAdapter(
        channels=["economy"],
        interval=30,
        delay=1.5,
        max_pages=5,
    )

    adapter._state.status = MonitorStatus.ERROR
    adapter._state.last_error = "Investing: boom"
    adapter._state.extra["next_run_at"] = datetime(2026, 3, 15, 9, 40, 0)
    adapter._state.extra["consecutive_failures"] = 3
    adapter._state.extra["backoff_seconds"] = 10
    adapter._state.extra["channel_stats"] = {"economy": 2}
    adapter._state.extra["recent_items"] = [{"time": "09:39:00", "title": "旧数据"}]

    monkeypatch.setattr(adapter_module, "Thread", _FakeThread)

    adapter.start()
    first_start = adapter.get_state()
    assert first_start.extra["runtime_mode"] == "single-loop"
    assert first_start.extra["runtime_status"] == "starting"
    assert first_start.extra["runtime_restarts"] == 0
    assert first_start.last_error is None
    assert first_start.extra["next_run_at"] is None
    assert first_start.extra["consecutive_failures"] == 0
    assert first_start.extra["backoff_seconds"] == 0
    assert first_start.extra["channel_stats"] == {}
    assert first_start.extra["recent_items"] == []

    adapter.stop()
    adapter.start()
    second_start = adapter.get_state()

    assert second_start.extra["runtime_restarts"] == 1
    assert second_start.extra["runtime_active_workers"] == 1


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
