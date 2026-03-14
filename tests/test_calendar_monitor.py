from __future__ import annotations

import builtins
import io
import sys
from pathlib import Path
from typing import Any, List

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from crawl import calendar_monitor as module


def test_save_to_json_uses_runtime_project_relative_output_dir(monkeypatch) -> None:
    assert module.save_to_json.__defaults__ == (None,)

    captured_paths: List[Path] = []

    class _FixedNow:
        def strftime(self, _fmt: str) -> str:
            return "20260314"

    class _FixedDatetime:
        @staticmethod
        def now() -> _FixedNow:
            return _FixedNow()

    def fake_open(path: str | Path, mode: str = "r", *args: Any, **kwargs: Any):
        captured_paths.append(Path(path))
        return io.StringIO()

    monkeypatch.setattr(module, "datetime", _FixedDatetime)
    monkeypatch.setattr(builtins, "open", fake_open)

    module.save_to_json([{"id": 123, "country_id": "CN"}])

    expected_dir = Path(module.__file__).resolve().parent.parent / "output" / "calendar"
    assert captured_paths == [expected_dir / "Calendar_CN_20260314_123.json"]


def test_on_new_items_passes_output_dir_to_save(monkeypatch, tmp_path) -> None:
    captured_output_dirs: List[str | None] = []

    def fake_save_to_json(items, output_dir=None) -> None:
        captured_output_dirs.append(output_dir)

    monkeypatch.setattr(module, "save_to_json", fake_save_to_json)

    module.on_new_items(
        [
            {
                "title": "测试事件",
                "country": "中国",
                "importance": 2,
            }
        ],
        output_dir=str(tmp_path),
    )

    assert captured_output_dirs == [str(tmp_path)]


@pytest.mark.parametrize(
    "argv",
    [
        ["calendar_monitor.py", "--monitor", "--interval", "0"],
        ["calendar_monitor.py", "--monitor", "--interval", "-1"],
    ],
)
def test_main_rejects_non_positive_interval(monkeypatch, argv: List[str]) -> None:
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(
        module,
        "monitor_mode",
        lambda *args, **kwargs: pytest.fail("parse_args 不应成功"),
    )

    with pytest.raises(SystemExit) as exc_info:
        module.main()

    assert exc_info.value.code == 2
