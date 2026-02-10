# 华尔街见闻实时爬虫 - 快速开始

## ✅ 已验证可用

爬虫已经过测试，可以直接使用！API 接口已确认：
- **API地址**: `https://api-one-wscn.awtmt.com/apiv1/content/lives`
- **频道参数**: `global-channel`（全球快讯）
- **响应格式**: JSON，包含完整的快讯数据

## 🚀 立即使用

### 1. 单次抓取（测试用）

```bash
# 抓取最新3条快讯
python -m crawl.wallstreetcn_runner --fetch --limit 3

# 抓取最新20条快讯
python -m crawl.wallstreetcn_runner --fetch --limit 20
```

### 2. 实时监控（推荐）

```bash
# 每30秒轮询一次，自动抓取新快讯
python -m crawl.wallstreetcn_runner --monitor --interval 30

# 每60秒轮询一次
python -m crawl.wallstreetcn_runner --monitor --interval 60

# 只保存JSON格式
python -m crawl.wallstreetcn_runner --monitor --interval 30 --format json

# 只保存Markdown格式
python -m crawl.wallstreetcn_runner --monitor --interval 30 --format markdown
```

## 📁 输出文件

所有快讯保存在 `articles/wallstreetcn/` 目录：

```
articles/wallstreetcn/
├── wsj_3052662_2026-02-10_102604.json    # JSON格式（完整数据）
├── wsj_3052662_2026-02-10_102604.md      # Markdown格式（易读）
├── wsj_3052660_2026-02-10_102513.json
└── wsj_3052660_2026-02-10_102513.md
```

### JSON 数据结构

```json
{
  "id": 3052660,
  "title": "云深处科技新专利可提高人形机器人跌倒恢复能力",
  "content": "<p>企查查APP显示...</p>",
  "content_text": "企查查APP显示...",
  "display_time": 1770690313,
  "display_time_str": "2026-02-10 10:25:13",
  "uri": "https://wallstreetcn.com/livenews/3052660",
  "url": "https://wallstreetcn.com/livenews/3052660",
  "source": "华尔街见闻",
  "channels": ["global-channel"],
  "score": 1,
  "author_name": "石惠",
  "author_id": 6029,
  "has_image": false,
  "images": [],
  "comment_count": 0,
  "type": "live"
}
```

## 🎯 实际测试结果

```bash
$ python -m crawl.wallstreetcn_runner --fetch --limit 3

🔍 开始抓取华尔街见闻 global-channel 频道最新 3 条快讯...
✅ 成功获取 3 条快讯

============================================================
📰 收到 3 条新快讯
============================================================

1. [2026-02-10 10:26:04] 快讯
   AI应用端涨势扩大，读客文化冲击20cm涨停...
   🔗 https://wallstreetcn.com/livenews/3052662

2. [2026-02-10 10:25:13] 云深处科技新专利可提高人形机器人跌倒恢复能力
   企查查APP显示，近日，杭州云深处科技股份有限公司...
   🔗 https://wallstreetcn.com/livenews/3052660

3. [2026-02-10 10:23:40] 快讯
   日本财务大臣片山皋月：日本一直以来都在将外汇特别账户资金...
   🔗 https://wallstreetcn.com/livenews/3052659

💾 保存快讯...
   ✅ 已保存: wsj_3052662_2026-02-10_102604.json
   ✅ 已保存: wsj_3052662_2026-02-10_102604.md
   ...
```

## 🔧 高级用法

### 监控其他频道

华尔街见闻有多个频道，可以通过 `--channel` 参数指定：

```bash
# 外汇频道
python -m crawl.wallstreetcn_runner --monitor --channel forex-channel

# 美股频道
python -m crawl.wallstreetcn_runner --monitor --channel us-stock-channel

# A股频道
python -m crawl.wallstreetcn_runner --monitor --channel a-stock-channel
```

### 在代码中使用

```python
from crawl.wallstreetcn import WallStreetCNLiveCrawler, WallStreetCNMonitor

# 创建爬虫实例
crawler = WallStreetCNLiveCrawler()

# 获取最新快讯
items = crawler.fetch_incremental(channel="global-channel", limit=20)

for item in items:
    print(f"[{item['display_time_str']}] {item['title']}")
    print(f"内容: {item['content_text'][:100]}...")
    print(f"链接: {item['url']}\n")

# 启动实时监控
def on_new_news(items):
    print(f"收到 {len(items)} 条新快讯")
    for item in items:
        # 自定义处理逻辑
        # 例如：发送通知、保存到数据库等
        pass

monitor = WallStreetCNMonitor(crawler, poll_interval=30)
monitor.start(callback=on_new_news)
```

## 📊 核心特性

✅ **真实API验证** - 已确认可用的API接口
✅ **增量抓取** - 自动记录最后ID，只获取新内容
✅ **自动去重** - 基于ID和时间戳，避免重复保存
✅ **双格式输出** - JSON（完整数据）+ Markdown（易读）
✅ **实时监控** - 可配置轮询间隔，持续监控新快讯
✅ **错误处理** - 自动重试，异常不中断
✅ **多频道支持** - 可监控全球、外汇、美股、A股等频道

## ⚙️ 配置说明

### 轮询间隔建议

- **测试阶段**: 60秒（避免频繁请求）
- **生产环境**: 30秒（平衡实时性和请求频率）
- **高频监控**: 15-20秒（需注意反爬虫风险）
- **低频监控**: 5-10分钟（适合非实时场景）

### 反爬虫策略

爬虫已内置以下反爬虫措施：
- 合理的 User-Agent
- 正确的 Referer 和 Origin
- 适当的请求间隔
- 标准的 Accept 头

如遇到限制，可以：
1. 降低轮询频率
2. 添加随机延迟
3. 使用代理IP（如需要）

## 🔍 故障排查

### 问题1: 无法获取数据

**可能原因**:
- 网络连接问题
- API接口变化
- 被反爬虫拦截

**解决方法**:
```bash
# 测试网络连接
curl -I https://api-one-wscn.awtmt.com/apiv1/content/lives

# 查看详细错误信息
python -m crawl.wallstreetcn_runner --fetch --limit 1
```

### 问题2: 数据格式错误

**可能原因**: API响应结构变化

**解决方法**: 检查 `crawl/wallstreetcn.py` 中的 `parse_live_item()` 方法，根据实际响应调整字段映射

### 问题3: 重复抓取

**可能原因**: `last_id` 未正确更新

**解决方法**: 检查 `WallStreetCNMonitor` 的 `start()` 方法中的 ID 更新逻辑

## 📝 文件说明

- `crawl/wallstreetcn.py` - 核心爬虫类
- `crawl/wallstreetcn_runner.py` - 命令行工具
- `docs/WALLSTREETCN_GUIDE.md` - 详细使用文档
- `articles/wallstreetcn/` - 输出目录

## 🎉 成功案例

已验证可以成功抓取：
- ✅ 全球快讯（global-channel）
- ✅ 完整的快讯内容（标题、正文、作者、时间）
- ✅ 自动保存为 JSON 和 Markdown 格式
- ✅ 增量抓取，避免重复

## 📞 技术支持

如有问题，请查看：
1. `docs/WALLSTREETCN_GUIDE.md` - 详细文档
2. 项目 Issues
3. API 响应示例：`/tmp/wsj_api_response.json`

---

**最后更新**: 2026-02-10
**状态**: ✅ 已验证可用
