# 统一监控系统使用指南

## 概述

统一监控系统集成了三个独立的监控源，提供美观的 Rich 终端界面实时展示所有监控状态。

### 集成的监控源

1. **隆众资讯监控** - 基于关键词搜索的资讯监控
2. **华尔街见闻监控** - 多频道商品快讯监控
3. **Investing.com 监控** - 国际财经新闻监控

## 快速开始

### 基本使用

```bash
# 使用默认配置启动所有监控
python unified_monitor.py
```

### 自定义配置

```bash
# 自定义隆众关键词
python unified_monitor.py --lz-keywords "原油,甲醇,PTA,乙二醇"

# 自定义华尔街见闻频道
python unified_monitor.py --wsj-channels commodity-channel oil-channel

# 自定义 Investing 代理
python unified_monitor.py --inv-proxy http://127.0.0.1:7897

# 自定义轮询间隔
python unified_monitor.py --lz-interval 60 --wsj-interval 30 --inv-interval 300
```

### 禁用特定监控源

```bash
# 只启动华尔街见闻和 Investing
python unified_monitor.py --disable-lz

# 只启动隆众资讯
python unified_monitor.py --disable-wsj --disable-inv
```

## 命令行参数

### 隆众资讯配置

- `--lz-keywords`: 关键词列表（逗号分隔），默认: "原油,甲醇,PTA,乙二醇,铜,白银,橡胶,天然橡胶"
- `--lz-interval`: 轮询间隔（分钟），默认: 30
- `--disable-lz`: 禁用隆众资讯监控

### 华尔街见闻配置

- `--wsj-channels`: 频道列表，默认: commodity-channel oil-channel gold-channel gold-forex-channel goldc-channel
- `--wsj-interval`: 轮询间隔（秒），默认: 30
- `--wsj-important`: 只监控重要快讯
- `--disable-wsj`: 禁用华尔街见闻监控

### Investing.com 配置

- `--inv-channels`: 频道列表，默认: commodities economic-indicators economy
- `--inv-interval`: 轮询间隔（秒），默认: 30
- `--inv-proxy`: 代理地址，默认: http://127.0.0.1:7897
- `--disable-inv`: 禁用 Investing.com 监控

### UI 配置

- `--refresh-rate`: UI 刷新间隔（秒），默认: 0.2（5 FPS）

## Rich 界面说明

### 界面布局

```
┌─────────────────────────────────────────────────────────┐
│ 🎯 统一监控系统 | 运行时间 | 监控源 | 运行中 | 总采集   │  ← 头部
├─────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
│ │ 隆众资讯    │ │ 华尔街见闻  │ │ Investing   │       │  ← 监控面板
│ │ 状态: 🟢    │ │ 状态: 🟢    │ │ 状态: 🟢    │       │
│ │ 运行时间    │ │ 运行时间    │ │ 运行时间    │       │
│ │ 本轮采集    │ │ 本轮采集    │ │ 本轮采集    │       │
│ │ 总计采集    │ │ 总计采集    │ │ 总计采集    │       │
│ └─────────────┘ └─────────────┘ └─────────────┘       │
├─────────────────────────────────────────────────────────┤
│ 💡 提示: 按 Ctrl+C 停止所有监控                         │  ← 底部
└─────────────────────────────────────────────────────────┘
```

### 状态指示

- 🟢 运行中 (RUNNING)
- 🟡 空闲/暂停 (IDLE/PAUSED)
- 🔴 错误 (ERROR)
- ⚫ 已停止 (STOPPED)

### 面板边框颜色

- 绿色边框: 正常运行
- 红色边框: 发生错误
- 黄色边框: 空闲状态
- 灰色边框: 已停止

## 架构说明

### 设计模式

采用**适配器模式 + 注册表**的架构：

```
unified_monitor.py (入口)
    ↓
MonitorManager (管理器)
    ↓
MonitorAdapter (适配器基类)
    ├── LongZhongAdapter (隆众适配器)
    ├── WallStreetCNAdapter (华尔街见闻适配器)
    └── InvestingAdapter (Investing 适配器)
    ↓
UnifiedMonitorUI (Rich 界面)
```

### 核心组件

1. **MonitorAdapter** (`monitor/adapter.py`)
   - 定义统一接口: `start()`, `stop()`, `get_state()`
   - 提供线程安全的状态管理
   - 支持优雅停止

2. **MonitorManager** (`monitor/manager.py`)
   - 管理多个监控适配器
   - 提供统一的启动/停止接口
   - 汇总所有监控状态

3. **UnifiedMonitorUI** (`monitor/unified_ui.py`)
   - Rich 界面展示
   - 实时刷新（默认 5 FPS）
   - 动态布局适配

4. **具体适配器** (`monitor/adapters.py`)
   - `LongZhongAdapter`: 封装隆众监控
   - `WallStreetCNAdapter`: 封装华尔街见闻监控
   - `InvestingAdapter`: 封装 Investing 监控

## 性能优化

### UI 刷新控制

- 默认刷新率: 5 FPS (0.2 秒)
- 可通过 `--refresh-rate` 调整
- 建议范围: 4-10 FPS

### 并发管理

- 每个监控在独立线程中运行
- 使用 `threading.Event` 实现优雅停止
- 线程安全的状态更新

### 资源清理

- 捕获 `Ctrl+C` 信号
- 自动停止所有监控线程
- 等待线程完成（超时 10 秒）

## 故障排查

### 监控无法启动

检查依赖是否安装：
```bash
pip install rich
```

### 代理连接失败

确保代理服务正在运行：
```bash
# 检查代理
curl -x http://127.0.0.1:7897 https://www.investing.com
```

### UI 显示异常

确保终端支持 Rich：
```bash
# 检查终端类型
echo $TERM

# 尝试降低刷新率
python unified_monitor.py --refresh-rate 0.5
```

## 扩展开发

### 添加新的监控源

1. 创建新的适配器类继承 `MonitorAdapter`
2. 实现 `_run()` 方法
3. 在 `unified_monitor.py` 中注册

示例：
```python
class NewMonitorAdapter(MonitorAdapter):
    def __init__(self, config):
        super().__init__(name="新监控源")
        self.config = config

    def _run(self):
        while not self.should_stop():
            # 监控逻辑
            self._state.items_count += 1
            time.sleep(self.config.interval)
```

## 注意事项

1. 隆众资讯监控需要有效的 Cookie 配置
2. Investing.com 监控建议使用代理
3. 建议在 tmux/screen 中运行以保持后台运行
4. 监控数据保存在 `output/report/cleaned` 目录

## 相关命令

### 原始命令对比

```bash
# 原命令 1: 隆众资讯
python -m monitor.runner --keywords "原油,甲醇" --no-history

# 原命令 2: 华尔街见闻
python -m crawl.multi_commodity_monitor --interval 30

# 原命令 3: Investing
python crawl/investing_monitor.py --monitor --interval 30 --proxy http://127.0.0.1:7897

# 统一命令（等效）
python unified_monitor.py \
  --lz-keywords "原油,甲醇" \
  --wsj-interval 30 \
  --inv-interval 30 \
  --inv-proxy http://127.0.0.1:7897
```
