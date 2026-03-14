from __future__ import annotations

import builtins
import io
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from crawl import multi_commodity_monitor as module


def test_save_to_json_uses_runtime_project_relative_output_dir(monkeypatch) -> None:
    assert module.save_to_json.__defaults__ == (None,)

    captured_paths: List[Path] = []

    class _DummyFormatter:
        def format_to_standard(self, item: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "article_id": str(item["id"]),
                "date": "20260314",
                "title": item.get("title", "快讯"),
            }

    def fake_open(path: str | Path, mode: str = "r", *args: Any, **kwargs: Any):
        captured_paths.append(Path(path))
        return io.StringIO()

    monkeypatch.setattr(module, "WallStreetCNFormatter", _DummyFormatter)
    monkeypatch.setattr(builtins, "open", fake_open)

    module.save_to_json([{"id": 123, "title": "测试快讯"}])

    expected_dir = (
        Path(module.__file__).resolve().parent.parent / "output" / "report" / "cleaned"
    )
    assert captured_paths == [expected_dir / "WSJ_20260314_123.json"]


@pytest.mark.parametrize(
    ("argv", "invalid_option"),
    [
        (["multi_commodity_monitor.py", "--fetch", "--interval", "0"], "--interval"),
        (["multi_commodity_monitor.py", "--fetch", "--limit", "0"], "--limit"),
        (["multi_commodity_monitor.py", "--fetch", "--interval", "-1"], "--interval"),
        (["multi_commodity_monitor.py", "--fetch", "--limit", "-1"], "--limit"),
    ],
)
def test_main_rejects_non_positive_cli_values(
    monkeypatch, argv: List[str], invalid_option: str
) -> None:
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(
        module, "fetch_mode", lambda *args, **kwargs: pytest.fail("parse_args 不应成功")
    )

    with pytest.raises(SystemExit) as exc_info:
        module.main()

    assert exc_info.value.code == 2


def test_main_stops_created_monitors_on_keyboard_interrupt(monkeypatch) -> None:
    created_monitors: List[_DummyMonitor] = []

    class _DummyMonitor:
        def __init__(
            self,
            crawler: object,
            poll_interval: int = 30,
            channel: str = "global-channel",
            important_only: bool = False,
        ) -> None:
            self.crawler = crawler
            self.poll_interval = poll_interval
            self.channel = channel
            self.important_only = important_only
            self.stop_called = False
            created_monitors.append(self)

        def start(self, callback=None) -> None:
            return None

        def stop(self) -> None:
            self.stop_called = True

    class _DummyThread:
        def __init__(self, target=None, args=(), daemon=False) -> None:
            self._target = target
            self._args = args
            self.daemon = daemon
            self.started = False

        def start(self) -> None:
            self.started = True
            if self._target is not None:
                self._target(*self._args)

        def join(self) -> None:
            raise KeyboardInterrupt

    monkeypatch.setattr(
        sys, "argv", ["multi_commodity_monitor.py", "--channels", "oil-channel"]
    )
    monkeypatch.setattr(module, "WallStreetCNLiveCrawler", lambda: object())
    monkeypatch.setattr(module, "WallStreetCNMonitor", _DummyMonitor)
    monkeypatch.setattr(module.threading, "Thread", _DummyThread)
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)

    with pytest.raises(SystemExit) as exc_info:
        module.main()

    assert exc_info.value.code == 0
    assert [monitor.channel for monitor in created_monitors] == ["oil-channel"]
    assert all(monitor.stop_called for monitor in created_monitors)
