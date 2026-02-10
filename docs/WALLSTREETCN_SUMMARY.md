# 华尔街见闻爬虫 - 完整功能总结

## 🎉 项目概览

华尔街见闻实时爬虫已完成开发，支持全功能监控和数据采集。

---

## ✅ 核心功能

### 1. 实时监控
- ✅ 自动轮询获取最新快讯
- ✅ 增量抓取，智能去重
- ✅ 可配置轮询间隔（15-120秒）

### 2. 重要过滤
- ✅ 支持"只看重要的"功能
- ✅ 基于官方评分系统（Score 1/2）
- ✅ 过滤94%的普通快讯

### 3. 多频道支持
- ✅ 13个专业频道
- ✅ 全球、商品、外汇、股票、债券等
- ✅ 支持多频道并行监控

### 4. 标准JSON格式
- ✅ 兼容隆众资讯格式
- ✅ 统一数据结构
- ✅ 便于批量处理和分析

### 5. 灵活配置
- ✅ 命令行参数丰富
- ✅ 支持后台运行
- ✅ 可自定义保存格式

---

## 🚀 快速开始

### 最简单的用法

```bash
# 监控全球重要快讯（推荐）
python -m crawl.wallstreetcn_runner --monitor --interval 30 --important
```

### 监控商品频道

```bash
# 监控商品市场（原油、金属、农产品等）
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel
```

### 监控商品频道的重要快讯

```bash
# 专注商品市场的重要信息
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel --important
```

---

## 📋 完整命令参数

```bash
python -m crawl.wallstreetcn_runner [选项]

必选参数（二选一）:
  --monitor, -m          启动实时监控模式
  --fetch, -f            单次抓取模式

基础参数:
  --channel, -c          频道名称 (默认: global-channel)
                         可选: commodity-channel, forex-channel,
                               a-stock-channel, us-stock-channel,
                               hk-stock-channel, bond-channel,
                               oil-channel, gold-channel 等
  --interval, -i         监控轮询间隔（秒） (默认: 30)
  --limit, -l            单次抓取数量 (默认: 20)
  --format               保存格式: json/markdown/both (默认: json)

过滤参数:
  --important            只抓取重要快讯 (Score >= 2)
  --min-score            最低评分过滤: 1=全部, 2=重要 (默认: 1)
```

---

## 🎯 使用场景示例

### 场景1：商品交易者

```bash
# 监控商品频道的重要快讯
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel --important
```

**获取内容**：
- 碳酸锂、镨钕等金属价格
- 原油、天然气市场动态
- 黄金、白银行情
- 农产品市场信息

### 场景2：外汇交易者

```bash
# 监控外汇频道
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel forex-channel --important
```

**获取内容**：
- 主要货币对汇率变动
- 央行政策动态
- 外汇市场分析

### 场景3：股票投资者

```bash
# 终端1：监控A股
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel a-stock-channel

# 终端2：监控美股
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel us-stock-channel

# 终端3：监控港股
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel hk-stock-channel
```

### 场景4：全面监控

```bash
# 监控全球所有重要快讯
python -m crawl.wallstreetcn_runner --monitor --interval 15 --channel global-channel --important
```

### 场景5：多市场组合

```bash
# 终端1：全球重要快讯（高频）
python -m crawl.wallstreetcn_runner --monitor --interval 15 --channel global-channel --important

# 终端2：商品市场全部快讯（中频）
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel

# 终端3：外汇市场全部快讯（中频）
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel forex-channel
```

---

## 📊 13个专业频道

| 频道代码 | 中文名称 | 适用场景 |
|---------|---------|---------|
| `global-channel` | 全球快讯 | 全面监控，包含所有重要信息 |
| `commodity-channel` | 大宗商品 | 商品交易者、能源分析师 |
| `forex-channel` | 外汇市场 | 外汇交易者、汇率分析 |
| `a-stock-channel` | A股市场 | A股投资者 |
| `us-stock-channel` | 美股市场 | 美股投资者 |
| `hk-stock-channel` | 港股市场 | 港股投资者 |
| `bond-channel` | 债券市场 | 债券投资者、利率分析 |
| `oil-channel` | 原油市场 | 能源交易者 |
| `gold-channel` | 黄金市场 | 贵金属交易者 |
| `financing-channel` | 融资市场 | 投融资分析 |
| `xgb-channel` | 新股宝 | 新股、IPO关注者 |
| `gold-forex-channel` | 黄金外汇 | 黄金+外汇综合 |
| `goldc-channel` | 黄金C | 黄金细分市场 |

---

## 📁 输出文件格式

### 标准JSON格式（默认）

**文件名**: `WSJ_2026-02-10_103100_3052664.json`

**内容示例**:
```json
{
  "articleId": "3052664",
  "title": "快讯_3052664",
  "publishTime": "2026-02-10 10:31:00",
  "url": "https://wallstreetcn.com/livenews/3052664",
  "columnName": "大宗商品",
  "source": "华尔街见闻",
  "content": "上海钢联发布数据显示，今日MMLC电池级碳酸锂（早盘）中间价报136800元/吨...",
  "tables": [],
  "date": "2026-02-10",
  "institution": "华尔街见闻",
  "period": "realtime",
  "category": "大宗商品",
  "researchers": [],
  "content_type": "资讯",
  "content_digest": "abc123...",
  "score": 1,
  "channels": ["commodity-channel"],
  "is_important": false
}
```

**优势**:
- ✅ 兼容隆众资讯格式
- ✅ 统一数据结构
- ✅ 便于批量处理
- ✅ 支持内容去重

---

## 💡 实用技巧

### 1. 后台运行

```bash
# 使用 nohup 后台运行
nohup python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel --important > commodity.log 2>&1 &

# 查看日志
tail -f commodity.log

# 停止运行
ps aux | grep wallstreetcn_runner
kill <进程ID>
```

### 2. 定时启动（使用crontab）

```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每天早上8点启动）
0 8 * * * cd /home/yztrade/PycharmProjects/longzhong_tiqu && nohup python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel --important > logs/commodity_$(date +\%Y\%m\%d).log 2>&1 &
```

### 3. 查看最新快讯

```bash
# 查看最新的5个JSON文件
ls -lt articles/wallstreetcn/WSJ_*.json | head -5

# 查看最新快讯的内容
ls -t articles/wallstreetcn/WSJ_*.json | head -1 | xargs cat | python3 -m json.tool
```

### 4. 统计快讯数量

```bash
# 统计总数
ls articles/wallstreetcn/WSJ_*.json | wc -l

# 统计今天的快讯
ls articles/wallstreetcn/WSJ_$(date +%Y-%m-%d)_*.json 2>/dev/null | wc -l

# 统计重要快讯
grep -l '"is_important": true' articles/wallstreetcn/WSJ_*.json | wc -l
```

### 5. 按分类统计

```bash
# 统计各分类的快讯数量
python3 << 'EOF'
import json
from pathlib import Path
from collections import Counter

json_files = Path('articles/wallstreetcn').glob('WSJ_*.json')
categories = []

for f in json_files:
    with open(f) as file:
        data = json.load(file)
        categories.append(data.get('columnName', '未分类'))

category_count = Counter(categories)

print('分类统计:')
for category, count in category_count.most_common():
    print(f'  {category}: {count} 条')
EOF
```

---

## 🔧 在代码中使用

### 基础用法

```python
from crawl.wallstreetcn import WallStreetCNLiveCrawler

# 创建爬虫
crawler = WallStreetCNLiveCrawler()

# 获取商品频道快讯
items = crawler.fetch_incremental(
    channel="commodity-channel",
    limit=20,
    important_only=True  # 只获取重要快讯
)

for item in items:
    print(f"[{item['display_time_str']}] {item['title'] or '快讯'}")
    print(f"  分类: {item['channels']}")
    print(f"  评分: {item['score']}")
    print(f"  内容: {item['content_text'][:100]}...")
    print()
```

### 实时监控

```python
from crawl.wallstreetcn import WallStreetCNLiveCrawler, WallStreetCNMonitor

crawler = WallStreetCNLiveCrawler()

def on_new_news(items):
    print(f"📰 收到 {len(items)} 条新快讯")
    for item in items:
        # 自定义处理逻辑
        if '涨停' in item['content_text']:
            print(f"⚠️ 涨停快讯: {item['content_text'][:100]}")

        # 保存到数据库
        # save_to_database(item)

        # 发送通知
        # send_notification(item)

monitor = WallStreetCNMonitor(
    crawler=crawler,
    poll_interval=30,
    channel="commodity-channel",
    important_only=True
)

monitor.start(callback=on_new_news)
```

---

## 📊 数据统计

### 重要性分布（实测）

| Score | 类型 | 占比 | 说明 |
|-------|------|------|------|
| 1 | 普通快讯 | ~94% | 常规市场动态 |
| 2 | 重要快讯 | ~6% | 重大市场事件 |

**测试数据**: 50条快讯中，3条为重要快讯

### 商品频道内容分类

| 类别 | 占比 | 示例 |
|------|------|------|
| 金属价格 | ~40% | 碳酸锂、镨钕、铜、白银 |
| 能源市场 | ~20% | 原油、天然气 |
| 农产品 | ~15% | 种业、农业投资 |
| 贵金属 | ~15% | 黄金、白银ETF |
| 综合快讯 | ~10% | 市场综述 |

---

## 📚 完整文档

1. **快速开始**: `README_WALLSTREETCN.md`
2. **完整指南**: `docs/WALLSTREETCN_COMPLETE_GUIDE.md`
3. **重要过滤**: `docs/WALLSTREETCN_IMPORTANT_FILTER.md`
4. **JSON格式**: `docs/WALLSTREETCN_JSON_FORMAT.md`
5. **快速参考**: `docs/WALLSTREETCN_QUICK_REFERENCE.md`
6. **频道指南**: `docs/WALLSTREETCN_CHANNELS.md`
7. **功能总结**: `docs/WALLSTREETCN_SUMMARY.md`（本文档）

---

## 🎉 核心优势

### 1. 功能完整
✅ 实时监控、增量抓取、智能去重
✅ 重要过滤、多频道支持
✅ 标准JSON格式、兼容隆众资讯

### 2. 易于使用
✅ 命令行工具简单直观
✅ 参数配置灵活丰富
✅ 文档完善详细

### 3. 性能优秀
✅ 增量抓取，避免重复
✅ 重要过滤，减少94%噪音
✅ 可配置轮询间隔

### 4. 数据标准
✅ 兼容隆众资讯格式
✅ 统一数据结构
✅ 便于批量处理和分析

### 5. 已验证可用
✅ 真实API测试通过
✅ 多频道测试成功
✅ 重要过滤功能正常

---

## 🚀 推荐配置

### 商品交易者（推荐）

```bash
# 监控商品频道的重要快讯
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel --important
```

**优势**:
- 专注商品市场
- 只获取重要信息
- 过滤94%噪音
- 节省资源

### 全面监控

```bash
# 监控全球所有重要快讯
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel global-channel --important
```

### 多市场组合

```bash
# 终端1：全球重要快讯
python -m crawl.wallstreetcn_runner --monitor --interval 15 --channel global-channel --important

# 终端2：商品市场
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel

# 终端3：外汇市场
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel forex-channel
```

---

## 🔍 故障排查

### 问题1：无法获取数据

```bash
# 测试网络连接
curl -I https://api-one-wscn.awtmt.com/apiv1/content/lives

# 测试API
curl -s "https://api-one-wscn.awtmt.com/apiv1/content/lives?channel=commodity-channel&client=pc&limit=5" | python3 -m json.tool
```

### 问题2：频道参数错误

确保使用正确的频道代码：
- ✅ `commodity-channel`（正确）
- ❌ `commodity`（错误）
- ❌ `商品频道`（错误）

### 问题3：文件保存失败

```bash
# 检查目录
ls -la articles/wallstreetcn/

# 创建目录
mkdir -p articles/wallstreetcn/

# 检查磁盘空间
df -h
```

---

## 📞 技术支持

- **项目目录**: `/home/yztrade/PycharmProjects/longzhong_tiqu`
- **核心代码**: `crawl/wallstreetcn.py`
- **格式化器**: `crawl/wallstreetcn_formatter.py`
- **命令行工具**: `crawl/wallstreetcn_runner.py`

---

## 🎯 下一步

1. **测试运行**: 先用 `--fetch` 模式测试
2. **选择频道**: 根据需求选择合适的频道
3. **配置过滤**: 决定是否只看重要快讯
4. **后台运行**: 使用 nohup 或 screen 保持运行
5. **数据分析**: 使用 Python 脚本分析采集的数据

---

**最后更新**: 2026-02-10
**版本**: v1.0
**状态**: ✅ 已完成，可投入使用

---

## 🎉 开始使用

现在你可以立即开始监控商品频道了：

```bash
# 推荐配置：监控商品频道的重要快讯
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel --important
```

祝你使用愉快！📈
