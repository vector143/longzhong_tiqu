# PR 计划：监控系统代码审查问题修复

## 概述

本 PR 用于修复监控系统代码审查中发现的 16 个问题，涵盖稳定性、线程安全、配置正确性、UI 一致性等方面。

---

## 问题清单与修复方案

### 🔴 中优先级问题（6 个）

#### M1. converter 允许为 None 但实际必需

**问题描述**
- 位置：`crawl/pipeline.py:382`, `monitor/scheduler.py:46`
- `incremental_crawl` 的 `converter` 参数声明为 `Optional`，但 `crawl_article_worker_async` 内部强依赖其方法
- 若外部复用 `CrawlScheduler` 未注入转换器，将在首次处理文章时抛异常

**修复方案**
```python
# 方案 A：改为必需参数（推荐）
def incremental_crawl(
    keyword: str,
    existing_ids: Set[str],
    cookies_manager: OilChemCookiesManager,
    converter: AsyncFormatConverter,  # 移除 Optional
    ...
) -> CrawlResult:

# 方案 B：函数开头检查
def incremental_crawl(..., converter: Optional[AsyncFormatConverter] = None, ...):
    if converter is None:
        raise ValueError("converter 参数不能为空，请提供 AsyncFormatConverter 实例")
```

**影响范围**
- `crawl/pipeline.py`
- `monitor/scheduler.py`
- 所有调用 `incremental_crawl` 的地方

---

#### M2. 限流配置未生效

**问题描述**
- 位置：`config/settings.py:87-89`, `monitor/utils.py`
- 配置了 `requests_per_minute` 和 `min_request_interval`
- 实现了 `TokenBucketRateLimiter` 类
- 但调度/爬取流程仅使用固定 `delay`，未实际应用限流器

**修复方案**
```python
# 在 CrawlScheduler 中集成限流器
class CrawlScheduler:
    def __init__(self, ...):
        ...
        # 初始化限流器
        self._rate_limiter = TokenBucketRateLimiter(
            requests_per_minute=monitor_cfg.requests_per_minute,
            min_interval=monitor_cfg.min_request_interval,
        )

    def _run_incremental_with_retry(self) -> CrawlResult:
        # 在每次请求前获取令牌
        self._rate_limiter.acquire(blocking=True)
        return incremental_crawl(...)

# 或在 incremental_crawl 内部集成
def incremental_crawl(..., rate_limiter: Optional[TokenBucketRateLimiter] = None):
    for article in articles:
        if rate_limiter:
            rate_limiter.acquire(blocking=True)
        # 处理文章...
```

**影响范围**
- `monitor/scheduler.py`
- `crawl/pipeline.py`（可选）

---

#### M3. 磁盘检查异常时误判通过

**问题描述**
- 位置：`monitor/utils.py:374-378`
- `check_disk_space` 在 OSError 时返回 `(True, float("inf"))`
- 预检可能误放行无效路径或无权限情况

**修复方案**
```python
def check_disk_space(
    path: Union[str, Path] = ".",
    threshold_mb: float = 100.0
) -> Tuple[bool, float, Optional[str]]:  # 增加错误信息返回
    """
    Returns:
        (是否满足阈值, 剩余空间MB, 错误信息或None)
    """
    try:
        usage = shutil.disk_usage(path)
        free_mb = usage.free / (1024 * 1024)
        return free_mb >= threshold_mb, free_mb, None
    except OSError as e:
        # 返回失败而非假设通过
        return False, 0.0, f"检查失败: {e}"

# 调用方更新
ok, free_mb, error = check_disk_space(...)
if error:
    warnings.append(f"磁盘检查异常: {error}")
elif not ok:
    errors.append(f"磁盘空间不足: {free_mb:.1f}MB")
```

**影响范围**
- `monitor/utils.py`
- `monitor/runner.py`

---

#### M4. 信号注册在非主线程会崩溃

**问题描述**
- 位置：`monitor/runner.py:203`
- `signal.signal()` 只能在主线程调用
- 若 `run_monitor` 被作为库在非主线程调用会抛 `ValueError`

**修复方案**
```python
import threading

def run_monitor(argv: Optional[List[str]] = None) -> int:
    ...
    # 仅在主线程注册信号
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGINT, _handle_signal)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _handle_signal)
    else:
        print("⚠️ 非主线程运行，信号处理已禁用")
```

**影响范围**
- `monitor/runner.py`

---

#### M5. graceful shutdown 可能丢失上传

**问题描述**
- 位置：`monitor/scheduler.py:166`, `monitor/runner.py:305`
- `scheduler.stop()` 使用 `shutdown(wait=False)` 不等待运行中的 job
- 如果轮询线程仍在产出上传任务，可能导致部分上传丢失

**修复方案**
```python
# scheduler.py
def stop(self, wait_for_job: bool = True, timeout: float = 30.0) -> None:
    """停止调度器

    Args:
        wait_for_job: 是否等待当前 job 完成
        timeout: 等待超时时间
    """
    if not self._running:
        return

    # 1. 停止接收新任务
    job = self._scheduler.get_job(self._job_id)
    if job:
        job.pause()

    # 2. 等待当前轮询完成
    if wait_for_job and self._poll_lock.locked():
        print("⏳ 等待当前轮询完成...")
        start = time.time()
        while self._poll_lock.locked() and (time.time() - start) < timeout:
            time.sleep(0.5)

    # 3. 关闭调度器
    try:
        self._scheduler.shutdown(wait=False)
    except Exception as e:
        print(f"⚠️ 停止调度器时发生错误: {e}")

    self._running = False
    ...

# runner.py - 调整清理顺序
finally:
    print("\n🧹 正在清理资源...")

    # 1. 先停止调度器（等待当前 job）
    if scheduler is not None and scheduler.is_running:
        scheduler.stop(wait_for_job=True, timeout=30.0)

    # 2. 等待上传队列
    if qiniu_uploader is not None:
        try:
            print("⏳ 等待上传队列完成...")
            qiniu_uploader.wait_for_completion(timeout=60.0)
        except Exception as exc:
            print(f"⚠️ 等待上传完成时异常: {exc}")
        qiniu_uploader.stop_upload_workers()

    # 3. 最后清理 PID
    pid_manager.cleanup()
```

**影响范围**
- `monitor/scheduler.py`
- `monitor/runner.py`

---

#### M6. existing_ids 原地修改的线程安全

**问题描述**
- 位置：`crawl/pipeline.py:390`
- `incremental_crawl` 原地修改传入的 `existing_ids` Set
- 虽然调度器内有 `_poll_lock` 串行化，但外部并发调用会有竞态

**修复方案**
```python
# 方案 A：使用线程安全的封装（推荐）
class ThreadSafeSet:
    """线程安全的集合封装"""
    def __init__(self, initial: Optional[Set[str]] = None):
        self._set: Set[str] = set(initial) if initial else set()
        self._lock = threading.Lock()

    def add(self, item: str) -> None:
        with self._lock:
            self._set.add(item)

    def __contains__(self, item: str) -> bool:
        with self._lock:
            return item in self._set

    def __len__(self) -> int:
        with self._lock:
            return len(self._set)

# 方案 B：返回新增 ID 而非原地修改
def incremental_crawl(...) -> CrawlResult:
    ...
    # 收集新增的 ID
    new_ids: Set[str] = set()
    for article in articles:
        if article_id not in existing_ids:
            # 处理文章
            new_ids.add(article_id)

    return CrawlResult(
        ...,
        new_article_ids=new_ids,  # 新增字段
    )

# 调用方负责更新
result = incremental_crawl(...)
existing_ids.update(result.new_article_ids)
```

**影响范围**
- `crawl/pipeline.py`
- `monitor/scheduler.py`
- `monitor/utils.py`（如果新增 ThreadSafeSet）

---

### 🟡 低优先级问题（10 个）

#### L1. UI 直接读取可变状态

**问题描述**
- 位置：`monitor/ui.py:245,270`
- UI 线程直接读取 `MonitorState` 的可变字段/列表
- 未使用 `get_snapshot()` 或锁保护，可能显示不一致

**修复方案**
```python
# ui.py
def _build_layout(self) -> Layout:
    # 获取状态快照
    snapshot = self._state.get_snapshot()

    layout["header"].update(self._render_header(snapshot))
    layout["stats"].update(self._render_stats(snapshot))
    layout["articles"].update(self._render_articles(snapshot))
    layout["polls"].update(self._render_polls(snapshot))
    ...

def _render_stats(self, snapshot: Dict[str, Any]) -> Panel:
    # 使用快照数据
    table.add_row(
        str(snapshot["today_total"]),
        str(snapshot["today_success"]),
        ...
    )
```

---

#### L2. get_snapshot 是浅拷贝

**问题描述**
- 位置：`monitor/state.py:232`
- 返回的列表元素（ArticleRecord/PollRecord）是共享对象
- 外部修改会影响内部状态

**修复方案**
```python
# 方案 A：使用 frozen dataclass
@dataclass(frozen=True)
class ArticleRecord:
    ...

@dataclass(frozen=True)
class PollRecord:
    ...

# 方案 B：深拷贝
import copy

def get_snapshot(self) -> Dict[str, Any]:
    with self._lock:
        return {
            ...
            "recent_articles": copy.deepcopy(self.recent_articles),
            "poll_history": copy.deepcopy(self.poll_history),
        }

# 方案 C：转换为字典（性能更好）
def get_snapshot(self) -> Dict[str, Any]:
    with self._lock:
        return {
            ...
            "recent_articles": [
                {
                    "article_id": r.article_id,
                    "title": r.title,
                    "publish_time": r.publish_time,
                    "crawl_time": r.crawl_time,
                    "status": r.status,
                }
                for r in self.recent_articles
            ],
            ...
        }
```

---

#### L3. 跨日重置的 print 破坏 UI

**问题描述**
- 位置：`monitor/state.py:92`
- 跨日重置时直接 `print`，在 Rich Live 界面中破坏屏幕

**修复方案**
```python
# 方案 A：使用回调通知
class MonitorState:
    def __init__(self, ..., on_daily_reset: Optional[Callable[[], None]] = None):
        self._on_daily_reset = on_daily_reset

    def _check_daily_reset(self, now: datetime) -> None:
        if now.date() != self._last_reset_date:
            self.today_total = 0
            ...
            self._last_reset_date = now.date()
            # 触发回调而非打印
            if self._on_daily_reset:
                self._on_daily_reset()

# 方案 B：使用 logging
import logging
logger = logging.getLogger(__name__)

def _check_daily_reset(self, now: datetime) -> None:
    if now.date() != self._last_reset_date:
        ...
        logger.info("已重置今日统计（跨日）")
```

---

#### L4. 后台线程 print 与 Rich Live 冲突

**问题描述**
- 位置：`monitor/scheduler.py:252`, `monitor/ui.py:102`
- APScheduler 后台线程的大量 print 输出与 Rich Live 屏幕刷新冲突

**修复方案**
```python
# 方案 A：统一使用 logging + RichHandler
import logging
from rich.logging import RichHandler

# 配置 logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, show_time=False)]
)
logger = logging.getLogger(__name__)

# 替换所有 print
logger.info("🚀 调度器已启动")

# 方案 B：使用 Rich console.log（需要共享 console 实例）
from rich.console import Console
console = Console()

# 在 Live 上下文中使用
with Live(..., console=console) as live:
    console.log("消息会正确渲染")

# 方案 C：静默模式 + 状态记录
class CrawlScheduler:
    def __init__(self, ..., verbose: bool = True):
        self._verbose = verbose

    def _log(self, message: str) -> None:
        if self._verbose:
            # 记录到状态而非打印
            self.state.add_log_message(message)
```

---

#### L5. 环境变量配置不完整

**问题描述**
- 位置：`config/settings.py:155`
- 仅加载了部分监控配置的环境变量
- 缺失：`ui_refresh_interval`, `poll_history_limit`, `retry_base_delay`, `requests_per_minute` 等

**修复方案**
```python
def _load_from_env(self) -> None:
    ...
    # 补充缺失的监控配置环境变量
    self.monitor.ui_refresh_interval = self._parse_float_env(
        'MONITOR_UI_REFRESH_INTERVAL', self.monitor.ui_refresh_interval)
    self.monitor.recent_articles_limit = self._parse_int_env(
        'MONITOR_RECENT_ARTICLES_LIMIT', self.monitor.recent_articles_limit)
    self.monitor.poll_history_limit = self._parse_int_env(
        'MONITOR_POLL_HISTORY_LIMIT', self.monitor.poll_history_limit)
    self.monitor.retry_base_delay = self._parse_float_env(
        'MONITOR_RETRY_BASE_DELAY', self.monitor.retry_base_delay)
    self.monitor.requests_per_minute = self._parse_int_env(
        'MONITOR_REQUESTS_PER_MINUTE', self.monitor.requests_per_minute)
    self.monitor.min_request_interval = self._parse_float_env(
        'MONITOR_MIN_REQUEST_INTERVAL', self.monitor.min_request_interval)
    self.monitor.min_disk_space_mb = self._parse_int_env(
        'MONITOR_MIN_DISK_SPACE_MB', self.monitor.min_disk_space_mb)

    log_to_file_env = os.getenv('MONITOR_LOG_TO_FILE', '').lower()
    if log_to_file_env:
        self.monitor.log_to_file = log_to_file_env in ('true', '1', 'yes')

    self.monitor.log_file_path = os.getenv(
        'MONITOR_LOG_FILE_PATH', self.monitor.log_file_path)
```

---

#### L6. Windows PID 检测不稳定

**问题描述**
- 位置：`monitor/utils.py:333`
- `os.kill(pid, 0)` 在 Windows 上语义不稳定

**修复方案**
```python
import os
import sys

@staticmethod
def _is_process_alive(pid: int) -> bool:
    """检查进程是否存活（跨平台）"""
    if pid <= 0:
        return False

    if sys.platform == "win32":
        # Windows: 使用 ctypes 检查进程
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        except Exception:
            # 降级方案：尝试 tasklist
            try:
                import subprocess
                result = subprocess.run(
                    ['tasklist', '/FI', f'PID eq {pid}', '/NH'],
                    capture_output=True, text=True, timeout=5
                )
                return str(pid) in result.stdout
            except Exception:
                return False
    else:
        # Unix: 使用 kill 信号 0
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return False
        return True
```

---

#### L7. --force 未重建 PID 文件

**问题描述**
- 位置：`monitor/runner.py:175`
- 使用 `--force` 跳过 PID 创建但未清理/重建 PID 文件

**修复方案**
```python
# runner.py
pid_manager = PidFileManager()
try:
    pid_manager.create()
except RuntimeError as exc:
    print(f"❌ {exc}")
    if not args.force:
        return 1
    # --force 模式：强制清理并重建
    print("⚠️ 使用 --force 强制启动，清理旧 PID 文件...")
    pid_manager.force_cleanup()
    pid_manager.create()

# utils.py - PidFileManager 新增方法
def force_cleanup(self) -> None:
    """强制清理 PID 文件（忽略进程检查）"""
    with self._lock:
        self._safe_unlink()
        print(f"🧹 已强制清理 PID 文件: {self._pid_file}")
```

---

#### L8. 非 TTY 环境快捷键失效但 UI 仍显示提示

**问题描述**
- 位置：`monitor/keyboard.py:224,255`
- 在 systemd/docker/CI 中 stdin 非 TTY，快捷键无效但 UI 仍显示提示

**修复方案**
```python
# keyboard.py - 新增检测方法
class KeyboardListener:
    @property
    def is_tty_available(self) -> bool:
        """检查 TTY 是否可用"""
        return sys.stdin.isatty()

# ui.py - 根据 TTY 状态调整提示
def _render_footer(self) -> Panel:
    if self._keyboard and self._keyboard.is_tty_available:
        text = Text()
        text.append("[Q] ", style="bold cyan")
        text.append("退出  ", style="white")
        text.append("[R] ", style="bold cyan")
        text.append("立即运行  ", style="white")
        text.append("[P] ", style="bold cyan")
        text.append("暂停/继续", style="white")
    else:
        text = Text("按 Ctrl+C 退出（快捷键不可用）", style="dim")

    return Panel(text, style="dim")
```

---

#### L9. 未使用的导入

**问题描述**
- 位置：`monitor/ui.py:27`
- 导入了 `ArticleRecord`/`PollRecord` 但未使用

**修复方案**
```python
# 删除未使用的导入
from monitor.state import MonitorState  # 移除 ArticleRecord, PollRecord

# 或使用 ruff 自动修复
# ruff check . --fix
```

---

#### L10. record_article 与 record_poll 潜在重复计数

**问题描述**
- 位置：`monitor/state.py:127,168`
- 两个方法都会累加 `today_total/today_success/today_failed`
- 当前只用 `record_poll`，但未来可能误用

**修复方案**
```python
# 方案 A：移除 record_article（如果不需要）
# 删除 record_article 方法，只保留 record_poll

# 方案 B：明确区分用途并添加文档
def record_article(self, ...) -> None:
    """
    记录单篇文章（用于手动/单独爬取场景）

    ⚠️ 注意：此方法会更新今日统计。
    如果使用 record_poll 记录轮询结果，请勿同时调用此方法，
    否则会导致重复计数。
    """
    ...

def record_poll(self, result: "CrawlResult") -> None:
    """
    记录一次轮询结果（用于定时轮询场景）

    ⚠️ 注意：此方法会更新今日统计并记录轮询历史。
    不要与 record_article 同时使用，否则会导致重复计数。
    """
    ...

# 方案 C：record_poll 不更新文章级统计，只更新轮询历史
def record_poll(self, result: "CrawlResult") -> None:
    with self._lock:
        self._check_daily_reset(now)

        # 只更新轮询级统计
        self.total_polls += 1

        # 记录轮询历史
        poll_record = PollRecord(...)
        self.poll_history.insert(0, poll_record)
        ...

        # 文章级统计由调用方通过 record_article 更新
```

---

## 提交计划

### 建议的 Commit 顺序

| 序号 | Commit 主题 | 包含问题 | 优先级 |
|------|------------|---------|--------|
| 1 | fix: 修复信号注册在非主线程崩溃问题 | M4 | 高 |
| 2 | fix: 修复 graceful shutdown 可能丢失上传 | M5 | 高 |
| 3 | fix: 修复 existing_ids 线程安全问题 | M6 | 高 |
| 4 | fix: converter 参数必需性校验 | M1 | 中 |
| 5 | feat: 集成限流器到爬取流程 | M2 | 中 |
| 6 | fix: 磁盘检查异常处理改进 | M3 | 中 |
| 7 | refactor: UI 使用状态快照渲染 | L1, L2 | 中 |
| 8 | refactor: 统一日志输出机制 | L3, L4 | 中 |
| 9 | feat: 补全环境变量配置支持 | L5 | 低 |
| 10 | fix: Windows PID 检测兼容性 | L6 | 低 |
| 11 | fix: --force 模式重建 PID 文件 | L7 | 低 |
| 12 | fix: 非 TTY 环境 UI 提示优化 | L8 | 低 |
| 13 | chore: 清理未使用的导入 | L9 | 低 |
| 14 | docs: 明确 record_article/record_poll 使用场景 | L10 | 低 |

### 可合并的 Commits

```
Commit A: 稳定性修复（M4 + M5 + M6）
  - fix: improve stability and thread safety

Commit B: 配置与校验（M1 + M2 + M3 + L5）
  - fix: improve configuration validation and rate limiting

Commit C: UI 与日志（L1 + L2 + L3 + L4 + L8）
  - refactor: improve UI rendering and logging

Commit D: 平台兼容性（L6 + L7）
  - fix: improve Windows compatibility

Commit E: 代码清理（L9 + L10）
  - chore: code cleanup and documentation
```

---

## 风险评估

### 高风险

| 问题 | 风险 | 缓解措施 |
|------|------|----------|
| M5 graceful shutdown | 可能引入死锁或退出卡住 | 添加超时机制，充分测试各种退出场景 |
| M6 线程安全 | 可能引入新的竞态条件 | 使用成熟的并发原语，添加并发测试 |
| M2 限流器集成 | 可能影响爬取性能 | 保留配置开关，允许禁用限流 |

### 中风险

| 问题 | 风险 | 缓解措施 |
|------|------|----------|
| L1/L2 快照机制 | 深拷贝可能影响性能 | 评估数据量，考虑使用轻量级方案 |
| L3/L4 日志重构 | 可能遗漏输出点 | 全局搜索 print，确保全部替换 |
| L5 环境变量 | 可能与现有配置冲突 | 文档说明优先级，保持向后兼容 |

### 低风险

| 问题 | 风险 | 缓解措施 |
|------|------|----------|
| L6 Windows PID | 可能在特殊 Windows 版本失效 | 添加降级方案 |
| L8 TTY 检测 | 某些环境检测不准确 | 提供手动覆盖选项 |

---

## 测试计划

### 单元测试

```python
# test_utils.py
def test_check_disk_space_exception():
    """测试磁盘检查异常处理"""
    ok, free_mb, error = check_disk_space("/nonexistent/path")
    assert not ok
    assert error is not None

def test_pid_manager_force_cleanup():
    """测试 PID 强制清理"""
    ...

def test_rate_limiter_blocking():
    """测试限流器阻塞模式"""
    ...

# test_state.py
def test_get_snapshot_isolation():
    """测试快照隔离性"""
    state = MonitorState()
    state.record_poll(...)
    snapshot = state.get_snapshot()
    # 修改快照不影响原状态
    snapshot["today_total"] = 999
    assert state.today_total != 999

# test_scheduler.py
def test_graceful_shutdown():
    """测试优雅退出"""
    ...
```

### 集成测试

```python
def test_concurrent_existing_ids():
    """测试 existing_ids 并发访问"""
    existing_ids = ThreadSafeSet()
    # 多线程并发添加
    ...

def test_shutdown_with_pending_uploads():
    """测试有未完成上传时的退出"""
    ...
```

### 手动测试

1. **信号处理测试**
   - 在主线程运行，发送 SIGINT/SIGTERM
   - 在非主线程运行，验证不崩溃

2. **非 TTY 测试**
   - 通过 pipe 运行：`echo "" | python -m monitor.runner`
   - 在 Docker 中运行

3. **Windows 测试**
   - PID 检测功能
   - 键盘监听功能

4. **长时间运行测试**
   - 跨日重置功能
   - 内存泄漏检测

---

## 文档更新

### 需要更新的文档

1. **README.md** - 添加环境变量配置说明
2. **监控使用说明** - 添加非 TTY 环境使用指南
3. **开发文档** - 添加 record_article/record_poll 使用说明

### 环境变量配置文档

```markdown
## 监控配置环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| MONITOR_POLL_INTERVAL | 10 | 轮询间隔（分钟） |
| MONITOR_MAX_PAGES | 3 | 每次轮询最大页数 |
| MONITOR_EARLY_STOP | 10 | 连续旧文章数触发提前停止 |
| MONITOR_KEYWORD | 原油 | 默认搜索关键词 |
| MONITOR_UI_REFRESH_INTERVAL | 1.0 | UI 刷新间隔（秒） |
| MONITOR_RECENT_ARTICLES_LIMIT | 20 | 最近文章显示数量 |
| MONITOR_POLL_HISTORY_LIMIT | 10 | 轮询历史保留数量 |
| MONITOR_MAX_RETRIES | 3 | 最大重试次数 |
| MONITOR_RETRY_BASE_DELAY | 5.0 | 重试基础延迟（秒） |
| MONITOR_REQUESTS_PER_MINUTE | 30 | 每分钟最大请求数 |
| MONITOR_MIN_REQUEST_INTERVAL | 0.5 | 最小请求间隔（秒） |
| MONITOR_MIN_DISK_SPACE_MB | 100 | 最小磁盘空间（MB） |
| MONITOR_LOG_LEVEL | INFO | 日志级别 |
| MONITOR_LOG_TO_FILE | false | 是否输出到文件 |
| MONITOR_LOG_FILE_PATH | monitor.log | 日志文件路径 |
| MONITOR_INTERACTIVE | true | 是否启用交互模式 |
```

---

## 时间线（建议）

| 阶段 | 内容 |
|------|------|
| Phase 1 | 稳定性修复（M4, M5, M6） |
| Phase 2 | 配置与校验（M1, M2, M3, L5） |
| Phase 3 | UI 与日志重构（L1-L4, L8） |
| Phase 4 | 平台兼容性与代码清理（L6, L7, L9, L10） |
| Phase 5 | 测试与文档 |
