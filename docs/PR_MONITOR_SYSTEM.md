# PR: 实时监控爬取系统

## Summary

- 新增实时监控模块，支持定时轮询爬取新文章
- 基于 article_id 去重，避免重复爬取
- 提供 Rich 实时监控界面，展示爬取状态和统计信息

## 动机与背景

当前爬虫为手动触发的一次性执行模式，无法自动监控新文章发布。用户需要：
1. 自动定时检测新文章
2. 实时查看爬取进度和统计
3. 避免重复爬取已处理的文章

---

## 技术方案

### 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| 定时调度 | APScheduler (BackgroundScheduler) | 稳定、支持 next_run_time、线程型调度器与同步代码兼容 |
| 实时界面 | Rich (Live + Layout + Table) | 功能强大、美观、Python 原生 |
| 键盘输入 | pynput / select + stdin | 非阻塞输入监听，独立线程处理 |
| 去重机制 | article_id 集合 + CSV 持久化 | 从现有 CSV 加载 article_id 列 |

### 架构设计

```
┌─────────────────────────────────────────────────────┐
│                   monitor/runner.py                 │
│                    (主入口整合)                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────┐      ┌─────────────────────┐  │
│  │ monitor/        │      │ monitor/ui.py       │  │
│  │ scheduler.py    │◄────►│ (Rich 实时界面)     │  │
│  │ (APScheduler)   │      │                     │  │
│  └────────┬────────┘      └─────────────────────┘  │
│           │                         ▲              │
│           ▼                         │              │
│  ┌─────────────────┐                │              │
│  │ monitor/        │────────────────┘              │
│  │ state.py        │                               │
│  │ (状态管理)      │                               │
│  └────────┬────────┘                               │
│           │                                        │
└───────────┼────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────┐
│              crawl/pipeline.py                      │
│         (增量爬取 incremental_crawl)                │
└─────────────────────────────────────────────────────┘
```

---

## 文件变更清单

### 新增文件 (5个)

| 文件路径 | 行数(估) | 说明 |
|----------|----------|------|
| `monitor/__init__.py` | ~20 | 监控模块包，导出公共 API |
| `monitor/state.py` | ~150 | 监控状态管理（统计、文章列表、轮询历史） |
| `monitor/scheduler.py` | ~100 | APScheduler 调度器封装 |
| `monitor/ui.py` | ~250 | Rich 实时监控界面 |
| `monitor/runner.py` | ~80 | 监控主入口，整合调度和 UI |

### 修改文件 (3个)

| 文件路径 | 变更类型 | 说明 |
|----------|----------|------|
| `requirements.txt` | 追加 | 添加 `apscheduler>=3.10.0`, `rich>=13.0.0` |
| `config/settings.py` | 新增类 | 添加 `MonitorConfig` 配置类 |
| `crawl/pipeline.py` | 新增函数 | 添加 `incremental_crawl()` 和 `CrawlResult` |

---

## 详细设计

### 1. 监控状态模块 (`monitor/state.py`)

```python
@dataclass
class ArticleRecord:
    """单篇文章记录"""
    article_id: str
    title: str
    publish_time: str
    crawl_time: datetime
    status: str  # "success" | "failed"

@dataclass
class PollRecord:
    """单次轮询记录"""
    poll_time: datetime
    new_count: int
    success_count: int
    failed_count: int
    elapsed_seconds: float

class MonitorState:
    """监控状态管理器（线程安全）"""

    # 运行状态
    status: str  # "idle" | "running" | "paused" | "error"

    # 今日统计
    today_total: int
    today_success: int
    today_failed: int
    today_skipped: int

    # 最近爬取文章 (最多20条)
    recent_articles: List[ArticleRecord]

    # 轮询历史 (最近10次)
    poll_history: List[PollRecord]

    # 下次轮询时间
    next_poll_time: Optional[datetime]
```

### 2. 增量爬取函数 (`crawl/pipeline.py`)

```python
@dataclass
class CrawlResult:
    """爬取结果"""
    new_articles: List[Dict]      # 新爬取的文章
    skipped_count: int            # 跳过的已存在文章数
    success_count: int            # 成功数
    failed_count: int             # 失败数
    elapsed_time: float           # 耗时(秒)

def incremental_crawl(
    keyword: str,
    existing_ids: Set[str],
    max_pages: int = 3,
    early_stop_threshold: int = 10
) -> CrawlResult:
    """
    增量爬取 - 只爬取新文章

    Args:
        keyword: 搜索关键词
        existing_ids: 已存在的文章ID集合
        max_pages: 最大爬取页数
        early_stop_threshold: 连续遇到多少篇旧文章后停止

    Returns:
        CrawlResult: 爬取结果
    """
```

**去重逻辑**:
```
for each page:
    articles = get_article_list(keyword, page)
    for article in articles:
        if article.id in existing_ids:
            consecutive_old += 1
            if consecutive_old >= threshold:
                return early  # 提前停止
        else:
            crawl(article)
            existing_ids.add(article.id)
            consecutive_old = 0
```

### 3. 调度器模块 (`monitor/scheduler.py`)

```python
class CrawlScheduler:
    """爬取调度器"""

    def __init__(
        self,
        interval_minutes: int,
        state: MonitorState,
        crawl_func: Callable
    ):
        self.scheduler = BackgroundScheduler()
        self.state = state
        self.crawl_func = crawl_func
        self.interval = interval_minutes

    def start(self) -> None:
        """启动调度器"""
        self.scheduler.add_job(
            self._poll_job,
            'interval',
            minutes=self.interval,
            next_run_time=datetime.now()  # 立即执行第一次
        )
        self.scheduler.start()

    def stop(self) -> None:
        """停止调度器"""
        self.scheduler.shutdown()

    def run_now(self) -> None:
        """立即执行一次"""
        threading.Thread(target=self._poll_job).start()

    def get_next_run_time(self) -> Optional[datetime]:
        """获取下次执行时间"""
        job = self.scheduler.get_job('crawl_job')
        return job.next_run_time if job else None

    def _poll_job(self) -> None:
        """轮询任务"""
        self.state.set_status("running")
        try:
            result = self.crawl_func()
            self.state.record_poll(result)
        except Exception as e:
            self.state.set_error(str(e))
        finally:
            self.state.set_status("idle")
```

### 4. Rich 监控界面 (`monitor/ui.py`)

**界面布局**:
```
┌─────────────────────────────────────────────────────────────────┐
│  隆众资讯爬虫监控  │  状态: ● 运行中  │  下次轮询: 08:32:15    │
├─────────────────────────────────────────────────────────────────┤
│                         今日统计                                │
│  ┌────────────┬────────────┬────────────┬────────────┐         │
│  │  总爬取    │   成功     │   失败     │   跳过     │         │
│  │    42      │    40      │     2      │    128     │         │
│  └────────────┴────────────┴────────────┴────────────┘         │
├─────────────────────────────────────────────────────────────────┤
│                       最近爬取文章                              │
│  ┌──────────┬────────────────────────────────────┬──────────┐  │
│  │ 时间     │ 标题                               │ 状态     │  │
│  ├──────────┼────────────────────────────────────┼──────────┤  │
│  │ 10:23:45 │ 2024年1月15日原油市场日报         │ 成功     │  │
│  │ 10:23:42 │ OPEC最新产量数据分析              │ 成功     │  │
│  │ 10:23:38 │ 布伦特原油期货走势                │ 失败     │  │
│  └──────────┴────────────────────────────────────┴──────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                        轮询历史                                 │
│  ┌──────────┬──────────┬──────────┬──────────────────────────┐ │
│  │ 时间     │ 新增     │ 耗时     │ 状态                     │ │
│  ├──────────┼──────────┼──────────┼──────────────────────────┤ │
│  │ 10:20    │    3     │  12.5s   │ 完成                     │ │
│  │ 10:10    │    0     │   2.1s   │ 无新文章                 │ │
│  │ 10:00    │    5     │  18.2s   │ 完成                     │ │
│  └──────────┴──────────┴──────────┴──────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  [Q] 退出  [R] 立即运行  [P] 暂停/继续  [C] 清除统计            │
└─────────────────────────────────────────────────────────────────┘
```

**组件实现**:
```python
class MonitorUI:
    def __init__(self, state: MonitorState, scheduler: CrawlScheduler):
        self.state = state
        self.scheduler = scheduler
        self.console = Console()

    def run(self) -> None:
        """启动实时界面"""
        with Live(self.build_layout(), refresh_per_second=1) as live:
            while True:
                live.update(self.build_layout())
                if self.handle_input():
                    break

    def build_layout(self) -> Layout:
        """构建界面布局"""
        layout = Layout()
        layout.split_column(
            Layout(self.render_header(), size=3),
            Layout(self.render_stats(), size=5),
            Layout(self.render_recent_articles(), ratio=2),
            Layout(self.render_poll_history(), ratio=1),
            Layout(self.render_footer(), size=3)
        )
        return layout
```

### 5. 配置扩展 (`config/settings.py`)

```python
@dataclass
class MonitorConfig:
    """监控配置"""
    poll_interval_minutes: int = 10        # 轮询间隔(分钟)
    ui_refresh_interval: float = 1.0       # UI刷新频率(秒)
    recent_articles_limit: int = 20        # 最近文章显示数量
    poll_history_limit: int = 10           # 轮询历史保留数量
    early_stop_threshold: int = 10         # 连续旧文章数触发提前停止
    default_keyword: str = "原油"          # 默认搜索关键词
    max_pages_per_poll: int = 3            # 每次轮询最大页数
```

---

## 使用方式

### 命令行启动

```bash
# 默认启动（关键词: 原油，间隔: 10分钟）
python -m monitor.runner

# 自定义参数
python -m monitor.runner --keyword "成品油" --interval 5

# 查看帮助
python -m monitor.runner --help
```

### 代码调用

```python
from monitor import run_monitor

# 启动监控
run_monitor(keyword="原油", interval_minutes=10)
```

### 键盘快捷键

| 按键 | 功能 |
|------|------|
| `Q` | 退出监控 |
| `R` | 立即执行一次爬取 |
| `P` | 暂停/继续定时轮询 |
| `C` | 清除今日统计 |

---

## 依赖变更

```diff
# requirements.txt

+ # 定时任务调度
+ apscheduler>=3.10.0
+
+ # 终端富文本界面
+ rich>=13.0.0
```

---

## 测试计划

### 单元测试

| 测试项 | 说明 |
|--------|------|
| `test_monitor_state.py` | MonitorState 状态更新、线程安全 |
| `test_scheduler.py` | 调度器启动/停止/立即执行 |
| `test_incremental_crawl.py` | 去重逻辑、提前停止 |

### 集成测试

| 测试项 | 说明 |
|--------|------|
| 完整轮询流程 | 定时触发 → 增量爬取 → 状态更新 |
| UI 渲染 | 界面正确显示统计和文章列表 |
| 键盘交互 | 快捷键响应正确 |

### 手动验收

- [ ] 启动后立即执行第一次爬取
- [ ] 10分钟后自动执行第二次爬取
- [ ] 新文章被正确检测和爬取
- [ ] 已爬取文章被正确跳过
- [ ] 界面实时更新统计信息
- [ ] 按 R 立即执行有效
- [ ] 按 Q 正常退出

---

## 风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 调度器与 Rich Live 线程冲突 | UI 卡顿或崩溃 | 使用 BackgroundScheduler，UI 在主线程 |
| CSV 并发写入冲突 | 数据损坏 | 复用现有 threading.Lock 机制 |
| 长时间运行内存泄漏 | 内存持续增长 | 限制历史记录数量，定期清理 |
| 网络异常导致爬取失败 | 轮询中断 | 异常捕获，记录错误，继续下次轮询 |

---

## Commit 计划

```
1. chore(deps): add apscheduler and rich dependencies
2. feat(config): add MonitorConfig for monitoring settings
3. feat(monitor): add MonitorState for tracking crawl status
4. refactor(pipeline): add incremental_crawl with CrawlResult
5. feat(monitor): add CrawlScheduler with APScheduler
6. feat(monitor): add Rich-based real-time monitoring UI
7. feat(monitor): add runner entry point and CLI
8. test(monitor): add unit tests for monitor modules
```

---

## 后续迭代

- [ ] 支持多关键词同时监控
- [ ] 添加邮件/微信通知新文章
- [ ] 支持 Web 界面（可选）
- [ ] 持久化统计数据到数据库

---

## 补充说明：关键问题与解决方案

### 问题 1: 去重数据源

**现状分析**：
- 现有 `UniversalNamingSystem._load_existing_mappings()` 加载的是 `new_filename` 集合
- CSV 中有 `article_id` 列但未用于去重

**解决方案**：
```python
# 在 core/naming.py 新增方法
def load_existing_article_ids(self) -> Set[str]:
    """加载已存在的 article_id 集合（用于增量爬取去重）"""
    ids: Set[str] = set()
    if os.path.exists(self.mapping_file):
        df = pd.read_csv(self.mapping_file)
        if 'article_id' in df.columns:
            ids = set(df['article_id'].dropna().astype(str).tolist())
    return ids
```

**去重流程**：
```
启动时: existing_ids = naming_system.load_existing_article_ids()
    ↓
每篇文章: if article['articleId'] in existing_ids → 跳过
    ↓
爬取成功后: existing_ids.add(article['articleId'])  # 内存更新
            save_mapping(...)  # CSV 持久化
```

---

### 问题 2: Cookie 会话管理

**风险**：长时间运行（几小时/几天）cookie 可能过期

**解决方案**：
```python
class CrawlScheduler:
    def _poll_job(self):
        # 每次轮询前验证 session
        if not self.cookies_manager.validate_session():
            self.state.set_error("Cookie 已过期，请重新导入")
            self.state.set_status("error")
            return

        # 继续正常爬取...
```

**配置项**：
```python
@dataclass
class MonitorConfig:
    validate_session_before_poll: bool = True  # 每次轮询前验证会话
```

**告警机制**：
- Cookie 失效时在 UI 显示红色错误状态
- 可选：发送通知（后续迭代）

---

### 问题 3: 七牛云上传

**决策**：监控模式默认继承现有配置（`upload_to_qiniu` 设置）

**生命周期管理**：
```python
# monitor/runner.py
def run_monitor():
    # 启动上传器
    if settings.output.upload_to_qiniu:
        qiniu_uploader = AsyncMemoryQiniuUploader(...)
        qiniu_uploader.start_upload_workers()

    try:
        # 运行监控...
    finally:
        # 退出时清理
        if qiniu_uploader:
            qiniu_uploader.wait_for_completion()  # 等待队列清空
            qiniu_uploader.stop_upload_workers()
```

---

### 问题 4: 状态持久化

**决策**：MVP 阶段不持久化，重启后统计清零

**理由**：
- 简化实现复杂度
- 去重依赖 CSV 已有持久化，不会重复爬取
- 统计仅用于观察，非关键数据

**后续迭代**：
- 可选方案：每日统计写入 JSON 文件
- 格式：`monitor_stats_YYYYMMDD.json`

---

### 问题 5: Rich Live 键盘输入

**方案**：独立线程 + 非阻塞读取

```python
import sys
import select
import threading

class KeyboardListener:
    """非阻塞键盘监听器"""

    def __init__(self):
        self._running = True
        self._queue = queue.Queue()
        self._thread = threading.Thread(target=self._listen, daemon=True)

    def start(self):
        self._thread.start()

    def _listen(self):
        while self._running:
            # Linux/macOS: select 非阻塞读取
            if select.select([sys.stdin], [], [], 0.1)[0]:
                key = sys.stdin.read(1).lower()
                self._queue.put(key)

    def get_key(self) -> Optional[str]:
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None
```

**UI 集成**：
```python
class MonitorUI:
    def run(self):
        keyboard = KeyboardListener()
        keyboard.start()

        with Live(...) as live:
            while self._running:
                key = keyboard.get_key()
                if key == 'q':
                    break
                elif key == 'r':
                    self.scheduler.run_now()
                # ...
                live.update(self.build_layout())
                time.sleep(0.1)
```

---

### 问题 6: 调度重叠与回压

**风险**：上一轮未完成就开始下一轮

**解决方案**：
```python
self.scheduler.add_job(
    self._poll_job,
    'interval',
    minutes=self.interval,
    id='crawl_job',
    max_instances=1,           # 最多 1 个实例
    coalesce=True,             # 错过的任务合并执行
    misfire_grace_time=60      # 60秒内的错过任务仍执行
)
```

**互斥锁**：
```python
class CrawlScheduler:
    def __init__(self):
        self._poll_lock = threading.Lock()

    def _poll_job(self):
        if not self._poll_lock.acquire(blocking=False):
            print("上一轮任务仍在执行，跳过本轮")
            return
        try:
            # 执行爬取...
        finally:
            self._poll_lock.release()
```

---

### 问题 7: 与现有代码的集成

**策略**：复用核心逻辑，不重写

```python
# crawl/pipeline.py

def incremental_crawl(
    keyword: str,
    existing_ids: Set[str],
    cookies_manager: OilChemCookiesManager,
    converter: AsyncFormatConverter,
    max_pages: int = 3,
    early_stop_threshold: int = 10
) -> CrawlResult:
    """
    增量爬取 - 复用现有爬取逻辑
    """
    new_articles = []
    skipped_count = 0
    consecutive_old = 0

    session = cookies_manager.session if cookies_manager else None

    for page in range(1, max_pages + 1):
        list_data = get_article_list(keyword, page_no=page, session=session)
        if not list_data:
            break

        articles = list_data['response']['list']

        for article in articles:
            article_id = article.get('articleId', '')

            if article_id in existing_ids:
                skipped_count += 1
                consecutive_old += 1
                if consecutive_old >= early_stop_threshold:
                    # 提前停止
                    return CrawlResult(...)
            else:
                # 复用现有的 worker 处理逻辑
                result = crawl_article_worker_async(
                    {'article': article, 'index': 0, 'total': 0},
                    session, output_formats, converter
                )
                if result:
                    new_articles.append(result)
                    existing_ids.add(article_id)
                consecutive_old = 0

    return CrawlResult(
        new_articles=new_articles,
        skipped_count=skipped_count,
        success_count=len(new_articles),
        ...
    )
```

---

### 问题 8: 资源清理与退出流程

**退出顺序**：
```
用户按 Q
    ↓
1. 设置 running = False，UI 循环退出
    ↓
2. scheduler.stop() - 停止调度器
    ↓
3. 等待当前任务完成（如果有）
    ↓
4. qiniu_uploader.wait_for_completion() - 等待上传队列清空
    ↓
5. qiniu_uploader.stop_upload_workers() - 停止上传线程
    ↓
6. 关闭 cookies session
    ↓
7. 打印退出统计，程序结束
```

**代码实现**：
```python
def run_monitor():
    # ...初始化...

    try:
        ui.run()  # 主循环
    except KeyboardInterrupt:
        print("\n收到中断信号...")
    finally:
        print("正在清理资源...")
        scheduler.stop()

        if qiniu_uploader:
            print("等待上传队列清空...")
            qiniu_uploader.wait_for_completion()
            qiniu_uploader.stop_upload_workers()

        if cookies_manager and cookies_manager.session:
            cookies_manager.session.close()

        print("监控已退出")
```

---

### 问题 9: 日志与可观测性

**结构化日志**：
```python
# 每次轮询结束写入日志
logger.log_poll_result({
    'timestamp': datetime.now().isoformat(),
    'type': 'POLL_COMPLETE',
    'keyword': keyword,
    'new_count': result.success_count,
    'skipped_count': result.skipped_count,
    'failed_count': result.failed_count,
    'elapsed_seconds': result.elapsed_time
})
```

**关键指标（在 UI 展示）**：
- 总运行时长
- 累计轮询次数
- 累计爬取/跳过/失败数
- 平均每次轮询耗时

---

### 问题 10: 时区处理

**决策**：使用系统本地时区

```python
from datetime import datetime

# 今日统计边界
def is_today(dt: datetime) -> bool:
    return dt.date() == datetime.now().date()

# 每日零点重置统计
class MonitorState:
    def check_daily_reset(self):
        now = datetime.now()
        if now.date() != self._last_reset_date:
            self._reset_today_stats()
            self._last_reset_date = now.date()
```

---

## 修订后的文件变更清单

### 新增文件 (6个)

| 文件路径 | 行数(估) | 说明 |
|----------|----------|------|
| `monitor/__init__.py` | ~20 | 监控模块包，导出公共 API |
| `monitor/state.py` | ~200 | 监控状态管理（含日期重置逻辑） |
| `monitor/scheduler.py` | ~120 | APScheduler 调度器（含互斥锁） |
| `monitor/ui.py` | ~300 | Rich 界面 + 键盘监听 |
| `monitor/runner.py` | ~100 | 主入口（含资源清理） |
| `monitor/keyboard.py` | ~50 | 非阻塞键盘监听器 |

### 修改文件 (4个)

| 文件路径 | 变更类型 | 说明 |
|----------|----------|------|
| `requirements.txt` | 追加 | 添加 `apscheduler>=3.10.0`, `rich>=13.0.0` |
| `config/settings.py` | 新增类 | 添加 `MonitorConfig` |
| `crawl/pipeline.py` | 新增函数 | 添加 `incremental_crawl()` 和 `CrawlResult` |
| `core/naming.py` | 新增方法 | 添加 `load_existing_article_ids()` |

---

## 修订后的风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 调度重叠 | 资源耗尽、重复爬取 | `max_instances=1` + 互斥锁 |
| Cookie 过期 | 爬取失败 | 每次轮询前验证，失效时显示错误状态 |
| CSV 并发写入 | 数据损坏 | 复用现有 `threading.Lock` |
| 上传队列未清空就退出 | 文件丢失 | `wait_for_completion()` 阻塞等待 |
| 内存泄漏 | 长时间运行崩溃 | 限制历史记录数量，每日重置统计 |
| 键盘输入阻塞 | UI 卡死 | 独立线程 + 非阻塞读取 |
| 增量判断失误 | 漏抓/重抓 | 依赖 article_id 唯一性 + 提前停止阈值可配置 |

---

## 修订后的 Commit 计划

```
1. chore(deps): add apscheduler and rich dependencies
2. feat(config): add MonitorConfig with validation and polling settings
3. feat(naming): add load_existing_article_ids for deduplication
4. feat(pipeline): add incremental_crawl with CrawlResult and early stop
5. feat(monitor): add MonitorState with thread-safe stats tracking
6. feat(monitor): add CrawlScheduler with overlap protection
7. feat(monitor): add KeyboardListener for non-blocking input
8. feat(monitor): add MonitorUI with Rich live display
9. feat(monitor): add runner entry point with graceful shutdown
10. test(monitor): add unit tests for core monitor components
```

---

## 补充说明：第二轮 Review 问题

### 问题 11: 启动前置检查

**需求**：启动时应检查必要条件，避免无感失败

**启动检查清单**：
```python
def preflight_check() -> Tuple[bool, List[str]]:
    """启动前置检查"""
    errors = []
    warnings = []

    # 1. 配置文件检查
    settings = get_settings()
    if not settings.qiniu.is_configured and settings.output.upload_to_qiniu:
        errors.append("七牛云上传已启用但未配置 access_key/secret_key")

    # 2. Cookie 文件检查
    if not os.path.exists(settings.crawler.cookies_file):
        errors.append(f"Cookie 文件不存在: {settings.crawler.cookies_file}")

    # 3. CSV 文件检查（可选，允许不存在）
    mapping_file = f"{settings.crawler.project_code}_filename_mapping.csv"
    if os.path.exists(mapping_file):
        try:
            pd.read_csv(mapping_file)
        except Exception as e:
            warnings.append(f"映射文件可能损坏: {e}")

    # 4. 网络连通性检查（可选）
    try:
        requests.head("https://www.oilchem.net", timeout=5)
    except:
        warnings.append("无法连接目标网站，请检查网络")

    # 5. 磁盘空间检查
    if settings.output.save_locally:
        free_space = shutil.disk_usage('.').free
        if free_space < 100 * 1024 * 1024:  # < 100MB
            warnings.append(f"磁盘空间不足: {free_space // 1024 // 1024}MB")

    return (len(errors) == 0, errors, warnings)
```

**启动时展示**：
```
┌─────────────────────────────────────────┐
│          启动前置检查                   │
├─────────────────────────────────────────┤
│ ✅ 配置文件加载成功                     │
│ ✅ Cookie 文件存在                      │
│ ✅ Cookie 会话有效                      │
│ ⚠️  磁盘空间较低 (剩余 200MB)           │
│ ✅ 网络连接正常                         │
│ ✅ 已加载 1,234 个已爬取文章ID          │
├─────────────────────────────────────────┤
│ 按 Enter 开始监控，按 Q 退出            │
└─────────────────────────────────────────┘
```

---

### 问题 12: 错误分类与处理

**错误分类**：
```python
class ErrorCategory(Enum):
    RETRYABLE = "retryable"       # 可自动重试（网络超时、临时错误）
    NEED_MANUAL = "need_manual"   # 需人工介入（Cookie 过期、权限问题）
    CONFIG_ERROR = "config_error" # 配置错误（缺少必要配置）
    FATAL = "fatal"               # 致命错误（磁盘满、内存不足）
```

**错误提示规范**：
```
❌ [需人工介入] Cookie 已过期
   请重新导出 Cookie 文件到: cookies_tang.json
   操作步骤: 登录网站 → 浏览器开发者工具 → 导出 Cookie

⚠️ [自动重试] 网络请求失败 (第2/3次重试)
   原因: Connection timeout
   下次重试: 30秒后

🔴 [配置错误] 七牛云配置不完整
   缺少: QINIU_SECRET_KEY
   请在 .env 文件中配置
```

---

### 问题 13: 网络重试策略

**重试配置**：
```python
@dataclass
class RetryConfig:
    max_retries: int = 3                    # 最大重试次数
    base_delay: float = 5.0                 # 基础延迟(秒)
    max_delay: float = 60.0                 # 最大延迟(秒)
    exponential_base: float = 2.0           # 指数退避基数
    retryable_exceptions: tuple = (         # 可重试的异常
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
    )
```

**重试逻辑**：
```python
def with_retry(func, config: RetryConfig):
    for attempt in range(config.max_retries):
        try:
            return func()
        except config.retryable_exceptions as e:
            if attempt == config.max_retries - 1:
                raise
            delay = min(
                config.base_delay * (config.exponential_base ** attempt),
                config.max_delay
            )
            logger.warning(f"重试 {attempt+1}/{config.max_retries}，{delay}秒后...")
            time.sleep(delay)
```

---

### 问题 14: CSV 文件损坏恢复

**检测与恢复策略**：
```python
def load_existing_article_ids_safe(self) -> Set[str]:
    """安全加载 article_id，带损坏检测与恢复"""
    try:
        df = pd.read_csv(self.mapping_file)
        if 'article_id' not in df.columns:
            logger.warning("CSV 缺少 article_id 列，将从空集合开始")
            return set()
        return set(df['article_id'].dropna().astype(str).tolist())

    except pd.errors.EmptyDataError:
        logger.warning("CSV 文件为空，将从空集合开始")
        return set()

    except pd.errors.ParserError as e:
        logger.error(f"CSV 文件损坏: {e}")
        # 备份损坏文件
        backup_path = f"{self.mapping_file}.corrupted.{int(time.time())}"
        shutil.copy(self.mapping_file, backup_path)
        logger.info(f"已备份损坏文件到: {backup_path}")
        # 从空开始（会导致重新爬取，但不会丢数据）
        return set()

    except FileNotFoundError:
        logger.info("CSV 文件不存在，将创建新文件")
        return set()
```

---

### 问题 15: Windows 兼容性

**问题**：`select.select([sys.stdin], ...)` 在 Windows 上不支持

**解决方案**：平台检测 + 降级处理

```python
import platform

class KeyboardListener:
    def __init__(self):
        self._is_windows = platform.system() == "Windows"
        if self._is_windows:
            self._init_windows()
        else:
            self._init_unix()

    def _init_windows(self):
        """Windows: 使用 msvcrt"""
        import msvcrt
        self._msvcrt = msvcrt

    def _init_unix(self):
        """Unix: 使用 select + termios"""
        import termios
        import tty
        self._old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())

    def _listen(self):
        if self._is_windows:
            while self._running:
                if self._msvcrt.kbhit():
                    key = self._msvcrt.getch().decode('utf-8', errors='ignore').lower()
                    self._queue.put(key)
                time.sleep(0.1)
        else:
            # Unix select 实现
            ...
```

**无交互模式**：
```bash
# 禁用键盘交互（适合后台运行）
python -m monitor.runner --no-interactive

# 或通过环境变量
MONITOR_NO_INTERACTIVE=1 python -m monitor.runner
```

---

### 问题 16: 速率限制与限流

**配置**：
```python
@dataclass
class RateLimitConfig:
    requests_per_minute: int = 30           # 每分钟最大请求数
    min_request_interval: float = 0.5       # 最小请求间隔(秒)
    burst_limit: int = 5                    # 突发请求限制
```

**限流器实现**：
```python
class RateLimiter:
    def __init__(self, config: RateLimitConfig):
        self._config = config
        self._tokens = config.burst_limit
        self._last_refill = time.time()
        self._lock = threading.Lock()

    def acquire(self) -> bool:
        """获取一个令牌，返回是否成功"""
        with self._lock:
            self._refill()
            if self._tokens > 0:
                self._tokens -= 1
                return True
            return False

    def wait_and_acquire(self):
        """等待直到获取令牌"""
        while not self.acquire():
            time.sleep(0.1)
```

---

### 问题 17: 安全与隐私

**日志脱敏**：
```python
def sanitize_log(message: str) -> str:
    """脱敏日志中的敏感信息"""
    # Cookie 值脱敏
    message = re.sub(r'(cookie[s]?\s*[:=]\s*)[^\s;]+', r'\1***', message, flags=re.I)
    # API Key 脱敏
    message = re.sub(r'(access_key\s*[:=]\s*)[^\s]+', r'\1***', message, flags=re.I)
    message = re.sub(r'(secret_key\s*[:=]\s*)[^\s]+', r'\1***', message, flags=re.I)
    return message
```

**文件权限**：
```python
# Cookie 文件权限检查（Unix）
import stat
cookie_mode = os.stat(settings.crawler.cookies_file).st_mode
if cookie_mode & (stat.S_IRGRP | stat.S_IROTH):
    logger.warning("Cookie 文件权限过于宽松，建议设置为 600")
```

---

### 问题 18: 无交互/后台运行模式

**用例**：
- 服务器后台运行
- Docker 容器
- CI/CD 环境

**CLI 参数**：
```bash
python -m monitor.runner \
    --no-interactive \        # 禁用键盘交互
    --log-file monitor.log \  # 输出到文件而非终端
    --quiet                   # 最小化输出
```

**配置**：
```python
@dataclass
class MonitorConfig:
    # ... 现有配置 ...
    interactive: bool = True           # 是否启用交互模式
    log_to_file: bool = False          # 是否输出到文件
    log_file_path: str = "monitor.log" # 日志文件路径
```

**无交互模式行为**：
- 不显示 Rich 界面
- 使用标准日志输出
- 通过信号（SIGINT/SIGTERM）控制退出

---

## 更新后的配置项完整列表

```python
@dataclass
class MonitorConfig:
    """监控配置"""
    # 轮询设置
    poll_interval_minutes: int = 10
    max_pages_per_poll: int = 3
    early_stop_threshold: int = 10
    default_keyword: str = "原油"

    # UI 设置
    ui_refresh_interval: float = 1.0
    recent_articles_limit: int = 20
    poll_history_limit: int = 10
    interactive: bool = True

    # 会话管理
    validate_session_before_poll: bool = True

    # 重试设置
    max_retries: int = 3
    retry_base_delay: float = 5.0

    # 速率限制
    requests_per_minute: int = 30
    min_request_interval: float = 0.5

    # 日志设置
    log_to_file: bool = False
    log_file_path: str = "monitor.log"

    # 磁盘检查
    min_disk_space_mb: int = 100
```

---

## 更新后的测试计划

### 新增测试项

| 测试项 | 说明 |
|--------|------|
| `test_preflight_check.py` | 启动前置检查逻辑 |
| `test_retry_logic.py` | 重试策略、指数退避 |
| `test_rate_limiter.py` | 速率限制器 |
| `test_csv_recovery.py` | CSV 损坏检测与恢复 |
| `test_keyboard_windows.py` | Windows 键盘监听 |
| `test_no_interactive.py` | 无交互模式 |

### 新增手动验收

- [ ] 启动时显示前置检查结果
- [ ] Cookie 过期时显示友好错误提示
- [ ] 网络断开后自动重试
- [ ] CSV 损坏后能自动恢复
- [ ] Windows 系统能正常运行
- [ ] `--no-interactive` 模式正常工作
- [ ] 后台运行能通过 Ctrl+C 正常退出

---

## 补充说明：第三轮 Review 问题

### 问题 19: 防止重复启动（PID 文件）

**需求**：避免同时启动多个监控实例导致重复爬取

**实现**：
```python
import os
import sys
import atexit

PID_FILE = "monitor.pid"

def check_already_running() -> bool:
    """检查是否已有实例运行"""
    if os.path.exists(PID_FILE):
        with open(PID_FILE, 'r') as f:
            old_pid = int(f.read().strip())
        # 检查进程是否存在
        try:
            os.kill(old_pid, 0)  # 信号0不发送，仅检查
            return True  # 进程存在
        except OSError:
            # 进程不存在，清理残留 PID 文件
            os.remove(PID_FILE)
    return False

def write_pid_file():
    """写入当前进程 PID"""
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    atexit.register(lambda: os.remove(PID_FILE) if os.path.exists(PID_FILE) else None)

# 使用
if check_already_running():
    print("错误: 监控进程已在运行中")
    sys.exit(1)
write_pid_file()
```

---

### 问题 20: 信号处理（优雅退出）

**需求**：支持 SIGTERM/SIGINT 信号优雅退出

**实现**：
```python
import signal

class GracefulShutdown:
    """优雅退出处理器"""

    def __init__(self):
        self._shutdown_requested = False
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum, frame):
        sig_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
        print(f"\n收到 {sig_name} 信号，正在优雅退出...")
        self._shutdown_requested = True

    @property
    def should_shutdown(self) -> bool:
        return self._shutdown_requested
```

**集成到 UI 循环**：
```python
shutdown = GracefulShutdown()

while not shutdown.should_shutdown:
    # 主循环...
    pass

# 执行清理
```

---

### 问题 21: 日志级别控制

**需求**：支持运行时调整日志级别，减少不必要输出

**配置**：
```python
@dataclass
class MonitorConfig:
    # ... 现有配置 ...
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
```

**实现**：
```python
import logging

def setup_logging(level: str = "INFO"):
    """配置日志级别"""
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 减少第三方库日志
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
```

**CLI 参数**：
```bash
python -m monitor.runner --log-level DEBUG
python -m monitor.runner --quiet  # 等同于 --log-level WARNING
```

---

### 问题 22: 中断恢复与 Checkpoint

**需求**：爬取中断后能从断点恢复，避免重复工作

**策略**：依赖现有 CSV 去重机制（article_id）

**分析**：
- 每篇文章爬取成功后立即写入 CSV
- 中断重启后，加载 CSV 中的 article_id 作为已完成集合
- 天然支持断点续爬，无需额外 checkpoint

**边界情况处理**：
```
场景: 文章 A 正在爬取时中断
  └─ 结果: article_id 未写入 CSV
  └─ 重启后: 重新爬取文章 A（幂等操作，不会造成数据问题）

场景: 文章 A 爬取成功，但上传七牛云时中断
  └─ 结果: CSV 已记录（本地文件已保存）
  └─ 解决: 后续可增加"补传"功能（MVP 暂不实现）
```

---

### 问题 23: 部分成功的处理

**场景**：HTML 成功但 Word 转换失败，或本地成功但上传失败

**策略**：
```python
@dataclass
class ArticleResult:
    article_id: str
    title: str
    html_success: bool = False
    word_success: bool = False
    upload_success: bool = False
    error_message: Optional[str] = None

# 记录部分成功状态
def record_partial_success(result: ArticleResult):
    if result.html_success and not result.word_success:
        logger.warning(f"文章 {result.title}: HTML成功, Word失败")
    if result.html_success and not result.upload_success:
        logger.warning(f"文章 {result.title}: 本地成功, 上传失败")
```

**UI 展示**：
```
最近爬取文章:
时间     | 标题                    | HTML | Word | 上传
10:23:45 | 原油市场日报            | ✅   | ✅   | ✅
10:23:42 | OPEC产量分析            | ✅   | ❌   | -
10:23:38 | 布伦特期货走势          | ✅   | ✅   | ❌
```

---

### 问题 24: Python 版本与依赖兼容

**Python 版本要求**：
```
Python >= 3.8 (与现有项目保持一致)
```

**依赖版本检查**：
```python
# requirements.txt 更新
apscheduler>=3.10.0,<4.0.0    # 限制大版本避免 breaking change
rich>=13.0.0,<14.0.0
```

**CI 检查建议** (可选)：
```bash
# 检查依赖冲突
pip check

# 检查版本兼容
pip install pipdeptree && pipdeptree --warn fail
```

**文档说明**：
```markdown
## 环境要求

- Python 3.8+
- 操作系统: Linux, macOS, Windows
- 终端: 支持 ANSI 颜色（Rich UI 需要）
```

---

### 问题 25: 用户文档与故障排查

**README 更新内容**：
```markdown
## 监控模式

### 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 启动监控
python -m monitor.runner
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--keyword` | 监控关键词 | 原油 |
| `--interval` | 轮询间隔(分钟) | 10 |
| `--no-interactive` | 禁用交互界面 | False |
| `--log-level` | 日志级别 | INFO |
| `--log-file` | 日志输出文件 | None |

### 故障排查

| 问题 | 可能原因 | 解决方法 |
|------|----------|----------|
| 启动报错"进程已运行" | 上次异常退出残留 PID 文件 | 删除 `monitor.pid` |
| Cookie 过期 | 登录会话失效 | 重新导出 Cookie |
| 无法连接网站 | 网络问题或被封 IP | 检查网络/更换 IP |
| 文章重复爬取 | CSV 文件损坏 | 检查 CSV 文件格式 |
| UI 显示异常 | 终端不支持 Rich | 使用 `--no-interactive` |
```

---

## MVP vs 后续迭代 划分

### MVP 必须实现 ✅

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 定时轮询爬取 | P0 | 核心功能 |
| article_id 去重 | P0 | 防止重复 |
| Rich 监控界面 | P0 | 核心需求 |
| 基础键盘交互 (Q/R/P) | P0 | 用户体验 |
| 启动前置检查 | P0 | 避免无感失败 |
| Cookie 验证 | P0 | 登录态保障 |
| 优雅退出 (SIGINT/SIGTERM) | P1 | 数据安全 |
| PID 文件防重复启动 | P1 | 运行安全 |
| 网络重试 (3次) | P1 | 稳定性 |
| 日志级别控制 | P1 | 可调试性 |
| CSV 损坏检测 | P1 | 健壮性 |
| Windows 基础兼容 | P1 | 跨平台 |
| `--no-interactive` 模式 | P1 | 后台部署 |
| 用户文档 | P1 | 可用性 |

### 后续迭代 📋

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 多关键词监控 | P2 | 扩展需求 |
| 日志轮转 | P2 | 长期运行 |
| 健康检查接口 | P2 | 运维监控 |
| Prometheus 指标导出 | P3 | 企业级监控 |
| 配置热更新 | P3 | 运维便利 |
| 守护进程模式 | P3 | 服务化部署 |
| 邮件/微信通知 | P3 | 告警通知 |
| Web 管理界面 | P4 | 可选增强 |
| 上传失败补传 | P2 | 数据完整性 |

---

## 最终文件变更清单

### 新增文件 (7个)

| 文件路径 | 行数(估) | 说明 |
|----------|----------|------|
| `monitor/__init__.py` | ~30 | 监控模块包，导出公共 API |
| `monitor/state.py` | ~250 | 监控状态管理（含日期重置） |
| `monitor/scheduler.py` | ~150 | APScheduler 调度器（含互斥锁、信号处理） |
| `monitor/ui.py` | ~350 | Rich 界面 + 键盘监听 |
| `monitor/runner.py` | ~150 | 主入口（含前置检查、资源清理） |
| `monitor/keyboard.py` | ~80 | 跨平台键盘监听器 |
| `monitor/utils.py` | ~100 | 工具函数（重试、限流、PID） |

### 修改文件 (5个)

| 文件路径 | 变更类型 | 说明 |
|----------|----------|------|
| `requirements.txt` | 追加 | 添加 `apscheduler`, `rich` |
| `config/settings.py` | 新增类 | 添加 `MonitorConfig` |
| `crawl/pipeline.py` | 新增函数 | 添加 `incremental_crawl()` |
| `core/naming.py` | 新增方法 | 添加 `load_existing_article_ids()` |
| `README.md` | 追加章节 | 监控模式使用说明 |

---

## 最终 Commit 计划 (12个)

```
1.  chore(deps): add apscheduler and rich dependencies
2.  feat(config): add MonitorConfig with all settings
3.  feat(naming): add load_existing_article_ids for deduplication
4.  feat(pipeline): add incremental_crawl with CrawlResult
5.  feat(monitor): add MonitorState with thread-safe tracking
6.  feat(monitor): add utils (retry, rate-limit, pid-file)
7.  feat(monitor): add CrawlScheduler with signal handling
8.  feat(monitor): add cross-platform KeyboardListener
9.  feat(monitor): add MonitorUI with Rich display
10. feat(monitor): add runner with preflight check
11. docs: add monitor usage guide to README
12. test(monitor): add unit tests for monitor modules
```
