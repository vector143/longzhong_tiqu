from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_python_m_monitor_runner_help_has_no_preload_runtime_warning() -> None:
    project_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONWARNINGS"] = "default"

    result = subprocess.run(
        [sys.executable, "-m", "monitor.runner", "--help"],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "RuntimeWarning" not in result.stderr
    assert "found in sys.modules" not in result.stderr
