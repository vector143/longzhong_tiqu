import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from monitor import runner


class _DummyPidManager:
    def create(self) -> None:
        return None

    def cleanup(self) -> None:
        return None


class _DummyCookiesManager:
    def __init__(self, cookies_file: str) -> None:
        self.cookies_file = cookies_file


class _DummyNamingSystem:
    def __init__(self, project_code: str) -> None:
        self.project_code = project_code

    def load_existing_article_ids(self):
        return set()


class _DummyConverter:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs


class _DummyState:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    def set_error(self, _message: str) -> None:
        return None


def _make_settings(default_keyword: str = "原油") -> SimpleNamespace:
    monitor_cfg = SimpleNamespace(
        default_keyword=default_keyword,
        poll_interval_minutes=10,
        interactive=False,
        recent_articles_limit=20,
        poll_history_limit=10,
        max_pages_per_poll=3,
        early_stop_threshold=10,
        validate_session_before_poll=False,
        max_retries=0,
        retry_base_delay=0.0,
        ui_refresh_interval=1.0,
    )
    crawler_cfg = SimpleNamespace(
        cookies_file="cookies.json",
        project_code="demo",
        base_dir="output",
        max_upload_workers=1,
    )
    output_cfg = SimpleNamespace(
        upload_to_qiniu=False,
        save_locally=True,
        default_formats=["json"],
    )
    return SimpleNamespace(
        monitor=monitor_cfg,
        crawler=crawler_cfg,
        output=output_cfg,
        get_qiniu_config=lambda: None,
    )


def _run_with_patched_runner(monkeypatch, argv, default_keyword="原油"):
    created_keywords = []
    request_gates = []
    rate_limiters = []

    class _DummyScheduler:
        def __init__(self, _state, **kwargs) -> None:
            created_keywords.append(kwargs["keyword"])
            request_gates.append(kwargs.get("request_gate"))
            rate_limiters.append(kwargs.get("rate_limiter"))
            self.is_running = False

        def start(self) -> None:
            self.is_running = True

        def stop(self, wait_for_job: bool = False, timeout: float = 60.0) -> None:
            self.is_running = False

    class _DummyMultiScheduler:
        def __init__(self, schedulers, _state) -> None:
            self.schedulers = schedulers
            self.is_running = False

        def start(self) -> None:
            self.is_running = True

        def stop(self, wait_for_job: bool = False, timeout: float = 60.0) -> None:
            self.is_running = False

    monkeypatch.setattr(runner, "get_settings", lambda: _make_settings(default_keyword))
    monkeypatch.setattr(runner, "PidFileManager", _DummyPidManager)
    monkeypatch.setattr(runner, "OilChemCookiesManager", _DummyCookiesManager)
    monkeypatch.setattr(runner, "UniversalNamingSystem", _DummyNamingSystem)
    monkeypatch.setattr(runner, "AsyncFormatConverter", _DummyConverter)
    monkeypatch.setattr(runner, "MonitorState", _DummyState)
    monkeypatch.setattr(runner, "ThreadSafeSet", lambda items: set(items))
    monkeypatch.setattr(runner, "CrawlScheduler", _DummyScheduler)
    monkeypatch.setattr(runner, "MultiCrawlScheduler", _DummyMultiScheduler)
    monkeypatch.setattr(runner, "_preflight_check", lambda _cookies: (True, [], []))
    monkeypatch.setattr(runner, "_print_preflight", lambda errors, warnings: None)
    monkeypatch.setattr(runner.signal, "signal", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        runner.time,
        "sleep",
        lambda _seconds: (_ for _ in ()).throw(KeyboardInterrupt()),
    )

    exit_code = runner.run_monitor(argv)
    return exit_code, created_keywords, request_gates, rate_limiters


def test_run_monitor_uses_default_keyword_when_cli_keywords_missing(monkeypatch):
    exit_code, created_keywords, _request_gates, _rate_limiters = (
        _run_with_patched_runner(
            monkeypatch,
            ["--no-history", "--no-interactive"],
            default_keyword="原油",
        )
    )

    assert exit_code == 0
    assert created_keywords == ["原油"]


def test_run_monitor_does_not_merge_default_keyword_when_cli_keywords_provided(
    monkeypatch,
):
    exit_code, created_keywords, _request_gates, _rate_limiters = (
        _run_with_patched_runner(
            monkeypatch,
            ["--keywords", "甲醇,PTA", "--no-history", "--no-interactive"],
            default_keyword="原油",
        )
    )

    assert exit_code == 0
    assert created_keywords == ["甲醇", "PTA"]


def test_run_monitor_shares_request_gate_across_multiple_keywords(monkeypatch):
    exit_code, created_keywords, request_gates, rate_limiters = (
        _run_with_patched_runner(
            monkeypatch,
            ["--keywords", "甲醇,PTA", "--no-history", "--no-interactive"],
            default_keyword="原油",
        )
    )

    assert exit_code == 0
    assert created_keywords == ["甲醇", "PTA"]
    assert len(request_gates) == 2
    assert request_gates[0] is not None
    assert request_gates[0] is request_gates[1]
    assert len(rate_limiters) == 2
    assert rate_limiters[0] is not None
    assert rate_limiters[0] is rate_limiters[1]


def test_run_monitor_warns_about_cold_start_gap_when_no_history(monkeypatch, capsys):
    exit_code, _created_keywords, _request_gates, _rate_limiters = (
        _run_with_patched_runner(
            monkeypatch,
            ["--keywords", "甲醇,PTA", "--no-history", "--no-interactive"],
            default_keyword="原油",
        )
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "冷启动" in captured.out
    assert "漏数" in captured.out


def test_run_monitor_warns_about_overlapping_keywords(monkeypatch, capsys):
    exit_code, _created_keywords, _request_gates, _rate_limiters = (
        _run_with_patched_runner(
            monkeypatch,
            ["--keywords", "橡胶,天然橡胶", "--no-history", "--no-interactive"],
            default_keyword="原油",
        )
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "关键词存在重叠" in captured.out
    assert "橡胶" in captured.out
    assert "天然橡胶" in captured.out
