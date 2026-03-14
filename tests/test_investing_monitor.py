from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from crawl import investing_monitor as module


@pytest.mark.parametrize(
    "argv",
    [
        ["investing_monitor.py", "--monitor", "--interval", "0"],
        ["investing_monitor.py", "--monitor", "--interval", "-1"],
        ["investing_monitor.py", "--workers", "0"],
        ["investing_monitor.py", "--workers", "-1"],
        ["investing_monitor.py", "--history", "0"],
        ["investing_monitor.py", "--delay", "-0.1"],
    ],
)
def test_main_rejects_invalid_cli_values(monkeypatch, argv: List[str]) -> None:
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(
        module,
        "InvestingMonitor",
        lambda *args, **kwargs: pytest.fail("parse_args 不应成功"),
    )

    with pytest.raises(SystemExit) as exc_info:
        module.main()

    assert exc_info.value.code == 2


def test_main_passes_max_pages_to_monitor_loop(monkeypatch) -> None:
    captured: Dict[str, Any] = {}

    class _DummyMonitor:
        def __init__(
            self,
            output_dir: str | None = None,
            proxy: str | None = None,
            max_workers: int = 5,
            rate_limit: float = 1.0,
        ) -> None:
            captured["init"] = {
                "output_dir": output_dir,
                "proxy": proxy,
                "max_workers": max_workers,
                "rate_limit": rate_limit,
            }

        def monitor_loop(
            self,
            channels: List[str],
            interval: int = 300,
            delay: float = 3.0,
            max_pages: int = 3,
        ) -> None:
            captured["monitor_loop"] = {
                "channels": channels,
                "interval": interval,
                "delay": delay,
                "max_pages": max_pages,
            }

    monkeypatch.setattr(module, "InvestingMonitor", _DummyMonitor)
    monkeypatch.setattr(
        sys,
        "argv",
        ["investing_monitor.py", "--monitor", "--max-pages", "1"],
    )

    module.main()

    assert captured["monitor_loop"]["max_pages"] == 1
