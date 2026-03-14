# 统一监控系统 - 快速开始

## 一键启动

现在运行 `python unified_monitor.py` 等价于同时运行以下三个命令：

```bash
# 原命令 1: 隆众资讯
python -m monitor.runner --keywords "原油,甲醇,PTA,乙二醇,铜,白银,橡胶,天然橡胶" --no-history

# 原命令 2: 华尔街见闻
python -m crawl.multi_commodity_monitor --interval 30

# 原命令 3: Investing.com
python crawl/investing_monitor.py --monitor --interval 30 --proxy http://127.0.0.1:7897
```

## 启动方式

### 方式 1: Python 脚本（推荐）
```bash
python unified_monitor.py
```

### 方式 2: Shell 脚本
```bash
./start_unified_monitor.sh
```

## 默认配置

| 监控源 | 配置项 | 默认值 |
|--------|--------|--------|
| **隆众资讯** | 关键词 | 原油,甲醇,PTA,乙二醇,铜,白银,橡胶,天然橡胶 |
| | 轮询间隔 | 30 分钟 |
| | 历史爬取 | 跳过（--no-history） |
| **华尔街见闻** | 频道 | commodity-channel, oil-channel, gold-channel, gold-forex-channel, goldc-channel |
| | 轮询间隔 | 30 秒 |
| **Investing.com** | 频道 | commodities, economic-indicators, economy |
| | 轮询间隔 | 30 秒 |
| | 代理 | http://127.0.0.1:7897 |

## Rich 界面

启动后会看到美观的终端界面：

```
┌────────────────────────────────────────────────────────────┐
│ 🎯 统一监控系统 | 运行时间 | 监控源: 3 | 运行中: 3      │
├────────────────────────────────────────────────────────────┤
│ ┌────────────┐ ┌────────────┐ ┌────────────┐             │
│ │ 隆众资讯   │ │ 华尔街见闻 │ │ Investing  │             │
│ │ 🟢 running │ │ 🟢 running │ │ 🟢 running │             │
│ └────────────┘ └────────────┘ └────────────┘             │
├────────────────────────────────────────────────────────────┤
│ 💡 按 Ctrl+C 停止所有监控                                  │
└────────────────────────────────────────────────────────────┘
```

## 自定义配置

```bash
# 修改关键词
python unified_monitor.py --lz-keywords "原油,甲醇"

# 禁用某个监控
python unified_monitor.py --disable-lz

# 修改代理
python unified_monitor.py --inv-proxy http://127.0.0.1:8888
```

## 详细文档

- **使用指南**: `UNIFIED_MONITOR_GUIDE.md`
- **配置对比**: `UNIFIED_MONITOR_CONFIG.md`

## 停止监控

按 `Ctrl+C` 即可优雅停止所有监控。
