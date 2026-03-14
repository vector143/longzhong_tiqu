# Lessons

- `python -m monitor.runner` 当前会因 [monitor/__init__.py](/home/yztrade/PycharmProjects/longzhong_tiqu/monitor/__init__.py#L12) 预先导入 `runner` 而触发 `RuntimeWarning`；包级 `__init__` 不应回导入口模块。
- [crawl/investing_monitor.py](/home/yztrade/PycharmProjects/longzhong_tiqu/crawl/investing_monitor.py#L314) 不能在列表态用 `content_digest` 判重，因为 [crawl/investing_formatter.py](/home/yztrade/PycharmProjects/longzhong_tiqu/crawl/investing_formatter.py#L41) 会在无正文时退回 `summary`，与正文态 digest 不一致。
- [crawl/investing_monitor.py](/home/yztrade/PycharmProjects/longzhong_tiqu/crawl/investing_monitor.py#L372) 和 [monitor/runner.py](/home/yztrade/PycharmProjects/longzhong_tiqu/monitor/runner.py#L310) 都存在共享 `requests.Session` / 共享状态跨并发任务复用的风险；多关键词或多 worker 入口要优先检查会话隔离和全局限流。
- [crawl/wallstreetcn.py](/home/yztrade/PycharmProjects/longzhong_tiqu/crawl/wallstreetcn.py#L182) 的增量轮询不能只盯住单页固定窗口；高频快讯源必须在单轮内继续 drain，直到命中旧 `last_id` 或无下一页。
- [monitor/runner.py](/home/yztrade/PycharmProjects/longzhong_tiqu/monitor/runner.py#L290) 里 CLI 显式传入的 `--keyword/--keywords` 应覆盖配置默认值，不能和 `default_keyword` 混合；否则监控范围会悄悄放大。
- [crawl/multi_commodity_monitor.py](/home/yztrade/PycharmProjects/longzhong_tiqu/crawl/multi_commodity_monitor.py#L38) 不应硬编码绝对输出目录；监控脚本要优先使用项目相对路径或显式 CLI 参数。
- `tests/` 下直接 `from crawl ...` 的测试需要统一补项目根路径或通过 `conftest.py` 提供路径注入，否则单独跑 `pytest -q` 时会出现 `ModuleNotFoundError: crawl`。
