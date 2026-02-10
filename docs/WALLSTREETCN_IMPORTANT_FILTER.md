# 华尔街见闻爬虫 - 重要快讯过滤功能

## ✅ 新功能：只看重要的

现在支持过滤重要快讯，就像网页上的"只看重要的"选项！

### 📊 重要性评分说明

华尔街见闻的快讯有评分系统：
- **Score 1** = 普通快讯（大部分）
- **Score 2** = 重要快讯（约占 6%，50条中有3条）

### 🚀 使用方法

#### 方式一：使用 `--important` 标志

```bash
# 只抓取重要快讯
python -m crawl.wallstreetcn_runner --fetch --limit 50 --important

# 实时监控重要快讯
python -m crawl.wallstreetcn_runner --monitor --interval 30 --important
```

#### 方式二：使用 `--min-score` 参数

```bash
# 只抓取 Score >= 2 的快讯
python -m crawl.wallstreetcn_runner --fetch --limit 50 --min-score 2

# 监控重要快讯
python -m crawl.wallstreetcn_runner --monitor --interval 30 --min-score 2
```

### 📈 实测效果

**测试1：抓取全部快讯**
```bash
$ python -m crawl.wallstreetcn_runner --fetch --limit 50
✅ 成功获取 50 条快讯
```

**测试2：只抓取重要快讯**
```bash
$ python -m crawl.wallstreetcn_runner --fetch --limit 50 --min-score 2
✅ 成功获取 3 条快讯

1. [2026-02-10 10:26:04] 传媒板块涨势扩大，读客文化冲击20cm涨停...
2. [2026-02-10 09:48:24] 恒指日内涨幅扩大至1%，恒生生物科技指数涨超2%...
3. [2026-02-10 08:57:31] 日经225指数涨幅扩大至2%...
```

从50条快讯中筛选出3条重要快讯，过滤率 94%！

### 🎯 推荐使用场景

#### 场景1：高频监控 + 重要快讯
```bash
# 每15秒监控一次，只关注重要快讯
python -m crawl.wallstreetcn_runner --monitor --interval 15 --important
```
**优势**：减少噪音，专注重要信息

#### 场景2：低频监控 + 全部快讯
```bash
# 每60秒监控一次，获取所有快讯
python -m crawl.wallstreetcn_runner --monitor --interval 60
```
**优势**：全面覆盖，不遗漏任何信息

#### 场景3：双模式并行
```bash
# 终端1：监控重要快讯（高频）
python -m crawl.wallstreetcn_runner --monitor --interval 15 --important

# 终端2：监控全部快讯（低频）
python -m crawl.wallstreetcn_runner --monitor --interval 60
```
**优势**：重要信息实时获取，全部信息定期备份

### 📝 完整命令参数

```bash
python -m crawl.wallstreetcn_runner [选项]

必选参数（二选一）:
  --monitor, -m          启动实时监控模式
  --fetch, -f            单次抓取模式

可选参数:
  --channel, -c          频道名称 (默认: global-channel)
  --interval, -i         监控轮询间隔（秒） (默认: 30)
  --limit, -l            单次抓取数量 (默认: 20)
  --format               保存格式: json/markdown/both (默认: both)
  --important            只抓取重要快讯 (Score >= 2)
  --min-score            最低评分过滤: 1=全部, 2=重要 (默认: 1)
```

### 💡 使用技巧

1. **测试阶段**：先用 `--fetch --limit 50 --min-score 2` 看看重要快讯的质量
2. **生产环境**：根据需求选择合适的过滤级别
3. **存储优化**：只保存重要快讯可以大幅减少存储空间
4. **通知集成**：重要快讯更适合触发实时通知

### 🔧 在代码中使用

```python
from crawl.wallstreetcn import WallStreetCNLiveCrawler, WallStreetCNMonitor

# 创建爬虫
crawler = WallStreetCNLiveCrawler()

# 只获取重要快讯
important_items = crawler.fetch_incremental(
    channel="global-channel",
    limit=50,
    important_only=True,  # 方式1
    min_score=2           # 方式2
)

print(f"获取到 {len(important_items)} 条重要快讯")

# 监控重要快讯
def handle_important_news(items):
    for item in items:
        print(f"⚠️ 重要快讯: {item['title']}")
        # 发送通知、触发交易等

monitor = WallStreetCNMonitor(
    crawler=crawler,
    poll_interval=30,
    important_only=True,
    min_score=2
)

monitor.start(callback=handle_important_news)
```

### 📊 数据对比

| 模式 | 50条中筛选结果 | 过滤率 | 适用场景 |
|------|---------------|--------|----------|
| 全部快讯 (min_score=1) | 50条 | 0% | 全面监控 |
| 重要快讯 (min_score=2) | 3条 | 94% | 精准监控 |

### ⚙️ 监控输出示例

```bash
$ python -m crawl.wallstreetcn_runner --monitor --interval 30 --important

🚀 启动华尔街见闻实时监控
   频道: global-channel
   轮询间隔: 30 秒
   过滤模式: 重要快讯 (min_score=2)  ← 显示过滤模式
   保存格式: both
   按 Ctrl+C 停止监控

✅ 初始化完成，当前最新ID: 3052662
⏳ 暂无新快讯
⏳ 暂无新快讯
📰 发现 1 条新快讯  ← 只有重要快讯才会触发
```

### 🎉 功能特点

✅ **智能过滤** - 基于华尔街见闻官方评分系统
✅ **双重模式** - 支持 `--important` 和 `--min-score` 两种方式
✅ **实时显示** - 监控时会显示当前过滤模式
✅ **灵活配置** - 可以随时切换过滤级别
✅ **性能优化** - 减少94%的数据处理量
✅ **存储节省** - 只保存重要快讯，节省磁盘空间

### 🔍 如何判断快讯是否重要？

查看保存的 JSON 文件中的 `score` 字段：

```json
{
  "id": 3052662,
  "title": "传媒板块涨势扩大...",
  "score": 2,  ← 重要快讯
  ...
}
```

或者查看 Markdown 文件中的 **评分** 字段：

```markdown
**评分**: 2  ← 重要快讯
```

---

**更新时间**: 2026-02-10
**功能状态**: ✅ 已测试可用
