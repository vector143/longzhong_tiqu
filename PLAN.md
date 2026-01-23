# PR 计划：实时监控爬取系统

## 需求概述

为隆众资讯爬虫项目添加实时监控功能：
1. **定时轮询爬取**：每 10 分钟自动检查新文章，基于 article_id 去重
2. **Rich 监控界面**：实时显示爬取状态、统计信息、最近爬取的文章

---

## 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| 定时调度 | APScheduler | 稳定、支持 next_run_time、易集成 |
| 实时界面 | Rich (Live + Layout + Table) | 功能强大、美观、Python 原生 |
| 去重机制 | 现有 article_id + CSV | 复用已有逻辑 |

---

## 文件变更清单

### 新增文件

| 文件路径 | 说明 |
|----------|------|
| `monitor/__init__.py` | 监控模块包 |
| `monitor/state.py` | 监控状态管理（统计、最近文章列表） |
| `monitor/scheduler.py` | APScheduler 调度器封装 |
| `monitor/ui.py` | Rich 实时界面 |
| `monitor/runner.py` | 监控主入口，整合调度和 UI |

### 修改文件

| 文件路径 | 修改内容 |
|----------|----------|
| `crawl/pipeline.py` | 抽取增量爬取函数，返回爬取结果结构 |
| `config/settings.py` | 新增监控相关配置项 |
| `requirements.txt` | 添加 `apscheduler`, `rich` 依赖 |

---

## 详细实现计划

### Phase 1: 基础设施 (监控状态模块)

**文件**: `monitor/state.py`

```
MonitorState 类:
├── 运行状态 (idle/running/error)
├── 当前轮询信息
│   ├── 开始时间
│   ├── 处理文章数
│   └── 错误信息
├── 今日统计
│   ├── 总爬取数
│   ├── 成功数
│   └── 失败数
├── 最近爬取文章列表 (最多20条)
│   ├── 标题
│   ├── 发布时间
│   ├── 爬取时间
│   └── 状态 (成功/失败)
├── 轮询历史 (最近10次)
│   ├── 时间
│   ├── 新增文章数
│   └── 耗时
└── 下次轮询时间
```

### Phase 2: 增量爬取逻辑重构

**文件**: `crawl/pipeline.py`

修改 `crawl_articles_async_multithread`:
- 新增 `skip_existing=True` 参数
- 返回结构化结果 `CrawlResult`:
  ```python
  @dataclass
  class CrawlResult:
      new_articles: List[Dict]      # 新爬取的文章
      skipped_count: int            # 跳过的已存在文章数
      success_count: int            # 成功数
      failed_count: int             # 失败数
      elapsed_time: float           # 耗时
  ```

新增函数 `incremental_crawl`:
- 加载已有 article_id 集合
- 只爬取新文章
- 提前停止优化（连续 N 篇旧文章则停止翻页）

### Phase 3: 调度器模块

**文件**: `monitor/scheduler.py`

```
CrawlScheduler 类:
├── __init__(interval_minutes, state, crawl_func)
├── start() - 启动调度器
├── stop() - 停止调度器
├── run_now() - 立即执行一次
├── get_next_run_time() - 获取下次执行时间
└── _job() - 定时任务回调
    ├── 更新状态为 running
    ├── 调用 incremental_crawl
    ├── 更新统计信息
    └── 更新状态为 idle
```

### Phase 4: Rich 监控界面

**文件**: `monitor/ui.py`

界面布局设计:
```
┌─────────────────────────────────────────────────────────────────┐
│  🔍 隆众资讯爬虫监控  │  状态: ● 运行中  │  下次轮询: 08:32   │
├─────────────────────────────────────────────────────────────────┤
│                        📊 今日统计                              │
│  ┌──────────┬──────────┬──────────┬──────────┐                 │
│  │ 总爬取   │ 成功     │ 失败     │ 跳过     │                 │
│  │   42     │   40     │    2     │   128    │                 │
│  └──────────┴──────────┴──────────┴──────────┘                 │
├─────────────────────────────────────────────────────────────────┤
│                      📰 最近爬取文章                            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 时间     │ 标题                              │ 状态         ││
│  ├─────────────────────────────────────────────────────────────┤│
│  │ 10:23:45 │ 2024年1月15日原油市场日报        │ ✅ 成功      ││
│  │ 10:23:42 │ OPEC最新产量数据分析             │ ✅ 成功      ││
│  │ 10:23:38 │ 布伦特原油期货走势               │ ❌ 失败      ││
│  │ ...      │ ...                              │ ...          ││
│  └─────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────┤
│                      📈 轮询历史                                │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 时间     │ 新增文章 │ 耗时     │ 状态                       ││
│  ├─────────────────────────────────────────────────────────────┤│
│  │ 10:20    │    3     │  12.5s   │ ✅ 完成                    ││
│  │ 10:10    │    0     │   2.1s   │ ✅ 无新文章                ││
│  │ 10:00    │    5     │  18.2s   │ ✅ 完成                    ││
│  └─────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────┤
│  [Q] 退出  [R] 立即运行  [P] 暂停/继续                          │
└─────────────────────────────────────────────────────────────────┘
```

组件结构:
```
MonitorUI 类:
├── __init__(state, scheduler)
├── build_layout() - 构建界面布局
├── render_header() - 渲染顶部状态栏
├── render_stats() - 渲染今日统计
├── render_recent_articles() - 渲染最近文章表格
├── render_poll_history() - 渲染轮询历史
├── render_footer() - 渲染底部快捷键
├── handle_input() - 处理键盘输入
└── run() - 启动 Live 循环
```

### Phase 5: 主入口整合

**文件**: `monitor/runner.py`

```python
def run_monitor(keyword: str = "原油", interval: int = 10):
    """启动监控模式"""
    state = MonitorState()
    scheduler = CrawlScheduler(interval, state, incremental_crawl)
    ui = MonitorUI(state, scheduler)

    scheduler.start()
    ui.run()  # 阻塞运行
```

### Phase 6: 配置扩展

**文件**: `config/settings.py`

新增配置:
```python
@dataclass
class MonitorConfig:
    """监控配置"""
    poll_interval_minutes: int = 10        # 轮询间隔
    ui_refresh_interval: float = 1.0       # UI 刷新频率
    recent_articles_limit: int = 20        # 最近文章显示数量
    poll_history_limit: int = 10           # 轮询历史保留数量
    early_stop_threshold: int = 10         # 连续旧文章数，触发提前停止
```

---

## 依赖添加

```
# requirements.txt 新增
apscheduler>=3.10.0
rich>=13.0.0
```

---

## 实现顺序

```
Step 1: 添加依赖 (requirements.txt)
    │
    ▼
Step 2: 配置扩展 (config/settings.py)
    │
    ▼
Step 3: 监控状态模块 (monitor/state.py)
    │
    ▼
Step 4: 增量爬取重构 (crawl/pipeline.py)
    │
    ▼
Step 5: 调度器模块 (monitor/scheduler.py)
    │
    ▼
Step 6: Rich UI (monitor/ui.py)
    │
    ▼
Step 7: 主入口 (monitor/runner.py)
    │
    ▼
Step 8: 测试与调优
```

---

## 风险点与应对

| 风险 | 应对措施 |
|------|----------|
| 调度器与 Rich Live 线程冲突 | 使用 BackgroundScheduler，UI 主线程运行 |
| CSV 并发写入问题 | 复用现有 threading.Lock 机制 |
| UI 刷新性能 | 控制刷新频率，使用增量更新 |
| 长时间运行内存泄漏 | 限制历史记录数量，定期清理 |

---

## 测试计划

1. 单元测试
   - MonitorState 状态更新测试
   - CrawlScheduler 调度逻辑测试
   - 去重逻辑测试

2. 集成测试
   - 完整轮询流程测试
   - UI 渲染测试
   - 键盘交互测试

3. 手动验收
   - 10 分钟轮询验证
   - 新文章检测验证
   - 界面显示正确性

---

## Commit 计划

```
1. chore(deps): add apscheduler and rich dependencies
2. feat(config): add monitor configuration options
3. feat(monitor): add MonitorState for tracking crawl status
4. refactor(pipeline): extract incremental crawl with CrawlResult
5. feat(monitor): add CrawlScheduler with APScheduler
6. feat(monitor): add Rich-based monitoring UI
7. feat(monitor): add runner entry point
8. docs: update README with monitor usage
```

---

## 使用方式

```bash
# 启动监控模式
python -m monitor.runner

# 或添加 CLI 命令
python main.py --monitor

# 自定义参数
python -m monitor.runner --keyword "原油" --interval 5
```
