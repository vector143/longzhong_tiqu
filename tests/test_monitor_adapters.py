from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from monitor import adapters as module


def test_wallstreetcn_adapter_uses_runtime_project_relative_output_dir() -> None:
    adapter = module.WallStreetCNAdapter(channels=["oil-channel"])

    expected_dir = (
        Path(module.__file__).resolve().parent.parent / "output" / "report" / "cleaned"
    )
    assert Path(adapter.output_dir) == expected_dir
