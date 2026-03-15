from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import unified_monitor as module


def test_main_passes_investing_runtime_args_from_unified_entry(monkeypatch) -> None:
    captured = {}

    class _DummyManager:
        def __init__(self):
            self.adapters = []

        def register(self, adapter):
            self.adapters.append(adapter)

        def start_all(self):
            return None

        def stop_all(self, timeout: float = 10.0):
            return None

    class _DummyInvestingAdapter:
        name = "Investing.com"

        def __init__(self, **kwargs):
            captured.update(kwargs)

    class _DummyUI:
        def __init__(self, manager, refresh_rate: float = 0.2):
            self.manager = manager
            self.refresh_rate = refresh_rate

        def run(self):
            return None

    monkeypatch.setattr(module, "MonitorManager", _DummyManager)
    monkeypatch.setattr(module, "InvestingAdapter", _DummyInvestingAdapter)
    monkeypatch.setattr(module, "UnifiedMonitorUI", _DummyUI)
    monkeypatch.setattr(module.signal, "signal", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "unified_monitor.py",
            "--disable-lz",
            "--disable-wsj",
            "--inv-delay",
            "1.5",
            "--inv-max-pages",
            "5",
            "--inv-workers",
            "2",
        ],
    )

    assert module.main() == 0
    assert captured["delay"] == 1.5
    assert captured["max_pages"] == 5
    assert captured["workers"] == 2
