# 华尔街见闻爬虫 - 频道列表与使用指南

## 📋 完整频道列表

华尔街见闻共有 **13个频道**，涵盖全球市场各个领域：

| 频道代码 | 中文名称 | 说明 | 使用频率 |
|---------|---------|------|---------|
| `global-channel` | 全球快讯 | 全球市场综合快讯 | ⭐⭐⭐⭐⭐ 最常用 |
| `commodity-channel` | 大宗商品 | 商品市场（原油、金属、农产品等） | ⭐⭐⭐⭐ |
| `forex-channel` | 外汇市场 | 外汇、汇率相关 | ⭐⭐⭐⭐⭐ |
| `a-stock-channel` | A股市场 | 中国A股市场 | ⭐⭐⭐⭐ |
| `us-stock-channel` | 美股市场 | 美国股市 | ⭐⭐⭐ |
| `hk-stock-channel` | 港股市场 | 香港股市 | ⭐⭐⭐ |
| `bond-channel` | 债券市场 | 债券、利率相关 | ⭐⭐⭐⭐ |
| `gold-channel` | 黄金市场 | 黄金相关 | ⭐⭐ |
| `oil-channel` | 原油市场 | 原油、能源相关 | ⭐⭐⭐ |
| `financing-channel` | 融资市场 | 融资、投资相关 | ⭐⭐ |
| `xgb-channel` | 新股宝 | 新股、IPO相关 | ⭐⭐ |
| `gold-forex-channel` | 黄金外汇 | 黄金+外汇综合 | ⭐ |
| `goldc-channel` | 黄金C | 黄金相关（细分） | ⭐ |

---

## 🎯 商品频道 (commodity-channel)

### 快速开始

```bash
# 抓取商品频道最新快讯
python -m crawl.wallstreetcn_runner --fetch --limit 20 --channel commodity-channel

# 实时监控商品频道
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel

# 只监控商品频道的重要快讯
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel --important
```

### 商品频道内容示例

**1. 碳酸锂价格**
```
上海钢联发布数据显示，今日MMLC电池级碳酸锂（早盘）中间价报136800元/吨，
较上日16:30价格上涨100元/吨。
```

**2. 稀土价格**
```
镨钕系价格大幅上涨
百川盈孚数据显示，稀土产品价格加速上涨。2月9日，氧化镨钕、金属镨钕
分别大涨7.59%和6.27%。氧化镨钕今年以来累计涨幅达34%。
```

**3. 贵金属行情**
```
现货白银涨6.98%，报83.2699美元/盎司。
COMEX白银期货涨7.67%，报82.795美元/盎司。
COMEX铜期货涨1.31%，报5.9590美元/磅。
```

**4. 黄金ETF**
```
黄金ETF收涨超2.4%，领跑美股大类资产类ETF
```

---

## 🚀 各频道使用示例

### 1. 全球快讯（默认）

```bash
# 最常用，包含所有重要市场动态
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel global-channel
```

### 2. 大宗商品（推荐）

```bash
# 监控商品市场：原油、金属、农产品等
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel
```

### 3. 外汇市场

```bash
# 监控外汇、汇率变动
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel forex-channel
```

### 4. A股市场

```bash
# 监控中国A股市场
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel a-stock-channel
```

### 5. 美股市场

```bash
# 监控美国股市
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel us-stock-channel
```

### 6. 港股市场

```bash
# 监控香港股市
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel hk-stock-channel
```

### 7. 债券市场

```bash
# 监控债券、利率市场
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel bond-channel
```

### 8. 原油市场

```bash
# 专注原油、能源市场
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel oil-channel
```

### 9. 黄金市场

```bash
# 专注黄金市场
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel gold-channel
```

---

## 💡 多频道监控策略

### 策略1：单频道精准监控

```bash
# 只监控商品频道的重要快讯
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel --important
```

**优势**：
- 专注特定市场
- 减少噪音
- 节省资源

### 策略2：多频道并行监控

```bash
# 终端1：监控商品频道
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel

# 终端2：监控外汇频道
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel forex-channel

# 终端3：监控A股频道
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel a-stock-channel
```

**优势**：
- 全面覆盖多个市场
- 独立监控，互不干扰
- 可以设置不同的轮询间隔

### 策略3：全球+专项组合

```bash
# 终端1：监控全球重要快讯（高频）
python -m crawl.wallstreetcn_runner --monitor --interval 15 --channel global-channel --important

# 终端2：监控商品频道全部快讯（低频）
python -m crawl.wallstreetcn_runner --monitor --interval 60 --channel commodity-channel
```

**优势**：
- 全局重要信息实时获取
- 专项市场全面覆盖
- 平衡实时性和完整性

---

## 📊 频道内容分析

### 商品频道 (commodity-channel) 内容分类

根据实际抓取的数据，商品频道包含：

| 类别 | 示例 | 占比 |
|------|------|------|
| 金属价格 | 碳酸锂、镨钕、铜、白银 | ~40% |
| 能源市场 | 原油、天然气 | ~20% |
| 农产品 | 种业、农业投资 | ~15% |
| 贵金属 | 黄金、白银ETF | ~15% |
| 综合快讯 | 市场综述、早餐 | ~10% |

### 频道重叠情况

很多快讯会同时出现在多个频道：

```json
{
  "channels": [
    "global-channel",      // 全球快讯
    "commodity-channel",   // 商品频道
    "forex-channel"        // 外汇频道
  ]
}
```

**说明**：
- 重要快讯通常会出现在多个频道
- 使用 `content_digest` 可以去重
- 选择主频道监控即可

---

## 🔧 在代码中使用

### 监控特定频道

```python
from crawl.wallstreetcn import WallStreetCNLiveCrawler, WallStreetCNMonitor

# 创建爬虫
crawler = WallStreetCNLiveCrawler()

# 获取商品频道快讯
commodity_items = crawler.fetch_incremental(
    channel="commodity-channel",
    limit=20
)

print(f"商品频道快讯: {len(commodity_items)} 条")

# 监控商品频道
monitor = WallStreetCNMonitor(
    crawler=crawler,
    poll_interval=30,
    channel="commodity-channel"
)

def on_commodity_news(items):
    for item in items:
        print(f"[商品] {item['title'] or '快讯'}")
        print(f"  {item['content_text'][:100]}...")

monitor.start(callback=on_commodity_news)
```

### 监控多个频道

```python
import threading
from crawl.wallstreetcn import WallStreetCNLiveCrawler, WallStreetCNMonitor

def monitor_channel(channel_name, interval=30):
    """监控单个频道"""
    crawler = WallStreetCNLiveCrawler()
    monitor = WallStreetCNMonitor(
        crawler=crawler,
        poll_interval=interval,
        channel=channel_name
    )

    def callback(items):
        print(f"[{channel_name}] 收到 {len(items)} 条新快讯")

    monitor.start(callback=callback)

# 创建多个监控线程
channels = [
    "commodity-channel",
    "forex-channel",
    "a-stock-channel"
]

threads = []
for channel in channels:
    t = threading.Thread(target=monitor_channel, args=(channel,))
    t.daemon = True
    t.start()
    threads.append(t)

# 等待所有线程
for t in threads:
    t.join()
```

### 按频道分类保存

```python
from pathlib import Path
import json

def save_by_channel(items, base_dir="articles/wallstreetcn"):
    """按频道分类保存"""
    for item in items:
        channels = item.get('channels', ['unknown'])

        # 使用第一个频道作为目录
        channel = channels[0] if channels else 'unknown'
        channel_dir = Path(base_dir) / channel
        channel_dir.mkdir(parents=True, exist_ok=True)

        # 保存文件
        filename = f"WSJ_{item['display_time_str'].replace(' ', '_').replace(':', '')}_{item['id']}.json"
        filepath = channel_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(item, f, ensure_ascii=False, indent=2)

        print(f"保存到 {channel}/{filename}")

# 使用示例
crawler = WallStreetCNLiveCrawler()
items = crawler.fetch_incremental(channel="commodity-channel", limit=10)
save_by_channel(items)
```

---

## 📁 按频道组织文件

### 目录结构

```
articles/wallstreetcn/
├── commodity-channel/
│   ├── WSJ_2026-02-10_103100_3052664.json
│   └── WSJ_2026-02-10_094556_3052640.json
├── forex-channel/
│   ├── WSJ_2026-02-10_102340_3052659.json
│   └── WSJ_2026-02-10_101607_3052658.json
├── a-stock-channel/
│   └── WSJ_2026-02-10_102604_3052662.json
└── global-channel/
    └── WSJ_2026-02-10_085731_3052600.json
```

---

## 🎯 推荐配置

### 商品交易者

```bash
# 监控商品频道 + 外汇频道
# 终端1
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel --important

# 终端2
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel forex-channel --important
```

### 股票交易者

```bash
# 监控A股 + 港股 + 美股
# 终端1
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel a-stock-channel

# 终端2
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel hk-stock-channel

# 终端3
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel us-stock-channel
```

### 宏观分析师

```bash
# 监控全球 + 债券 + 外汇
# 终端1
python -m crawl.wallstreetcn_runner --monitor --interval 15 --channel global-channel --important

# 终端2
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel bond-channel

# 终端3
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel forex-channel
```

---

## 📊 频道数据统计

### 实测数据（50条全球快讯）

| 频道 | 出现次数 | 占比 |
|------|---------|------|
| global-channel | 50 | 100% |
| forex-channel | 23 | 46% |
| bond-channel | 8 | 16% |
| hk-stock-channel | 7 | 14% |
| a-stock-channel | 6 | 12% |
| xgb-channel | 6 | 12% |
| financing-channel | 3 | 6% |
| oil-channel | 3 | 6% |
| commodity-channel | 1 | 2% |
| us-stock-channel | 1 | 2% |
| gold-channel | 1 | 2% |
| gold-forex-channel | 1 | 2% |
| goldc-channel | 1 | 2% |

**说明**：
- `global-channel` 包含所有快讯
- 其他频道是专项分类
- 一条快讯可能属于多个频道

---

## 💡 使用技巧

### 1. 选择合适的频道

- **需要全面信息** → `global-channel`
- **专注商品市场** → `commodity-channel`
- **专注外汇市场** → `forex-channel`
- **专注股票市场** → `a-stock-channel` / `us-stock-channel` / `hk-stock-channel`

### 2. 组合使用过滤

```bash
# 商品频道 + 重要快讯过滤
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel --important
```

### 3. 调整轮询频率

- **高频市场**（外汇、商品）：15-30秒
- **中频市场**（股票）：30-60秒
- **低频市场**（债券）：60-120秒

---

## 📚 相关文档

1. **快速开始**: `README_WALLSTREETCN.md`
2. **完整指南**: `docs/WALLSTREETCN_COMPLETE_GUIDE.md`
3. **重要过滤**: `docs/WALLSTREETCN_IMPORTANT_FILTER.md`
4. **JSON格式**: `docs/WALLSTREETCN_JSON_FORMAT.md`
5. **快速参考**: `docs/WALLSTREETCN_QUICK_REFERENCE.md`
6. **频道指南**: `docs/WALLSTREETCN_CHANNELS.md`（本文档）

---

## 🎉 总结

华尔街见闻提供 **13个专业频道**，覆盖全球市场各个领域：

✅ **全球快讯** - 最全面，包含所有重要信息
✅ **大宗商品** - 原油、金属、农产品等
✅ **外汇市场** - 汇率、外汇动态
✅ **股票市场** - A股、美股、港股
✅ **债券市场** - 债券、利率相关
✅ **专项市场** - 黄金、原油、新股等

**推荐配置（商品交易者）**：
```bash
# 监控商品频道的重要快讯
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel --important
```

这样可以：
- 专注商品市场动态
- 只获取重要快讯
- 节省资源和存储空间
- 提高信息质量

---

**最后更新**: 2026-02-10
**频道数量**: 13个
**状态**: ✅ 已测试可用
