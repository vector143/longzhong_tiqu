# 华尔街见闻实时爬虫使用指南

## 概述

本项目新增了华尔街见闻全球快讯的实时爬虫功能，可以自动监控并保存最新的快讯内容。

## 功能特点

- ✅ 实时监控华尔街见闻全球快讯
- ✅ 增量抓取，避免重复
- ✅ 支持多种保存格式（JSON、Markdown）
- ✅ 自动重试和错误处理
- ✅ 可配置轮询间隔
- ✅ 支持多频道监控

## 快速开始

### 1. 确认 API 接口

**重要：首次使用前必须完成此步骤！**

由于华尔街见闻的 API 接口可能变化，需要先通过浏览器确认实际的接口地址：

1. 打开浏览器，访问 https://wallstreetcn.com/live/global
2. 按 F12 打开开发者工具
3. 切换到 Network（网络）标签
4. 刷新页面，观察 XHR/Fetch 请求
5. 找到类似 `/apiv1/content/lives` 或 `/api/v1/lives` 的接口
6. 记录完整的接口路径和参数

### 2. 更新配置

编辑 `crawl/wallstreetcn.py` 文件，更新以下内容：

```python
class WallStreetCNLiveCrawler:
    BASE_URL = "https://wallstreetcn.com"
    API_ENDPOINT = "/apiv1/content/lives"  # 👈 更新为实际的接口路径
```

同时根据实际的 API 响应结构，调整 `fetch_lives()` 和 `parse_live_item()` 方法中的字段映射。

### 3. 运行爬虫

#### 方式一：实时监控模式（推荐）

```bash
# 每30秒轮询一次
python -m crawl.wallstreetcn_runner --monitor --interval 30

# 每60秒轮询一次
python -m crawl.wallstreetcn_runner --monitor --interval 60

# 只保存JSON格式
python -m crawl.wallstreetcn_runner --monitor --interval 30 --format json

# 只保存Markdown格式
python -m crawl.wallstreetcn_runner --monitor --interval 30 --format markdown
```

#### 方式二：单次抓取模式

```bash
# 抓取最新20条快讯
python -m crawl.wallstreetcn_runner --fetch --limit 20

# 抓取最新50条快讯
python -m crawl.wallstreetcn_runner --fetch --limit 50
```

## 输出文件

爬取的内容会保存到 `articles/wallstreetcn/` 目录：

```
articles/wallstreetcn/
├── wsj_123456_20260210_143022.json      # JSON格式
├── wsj_123456_20260210_143022.md        # Markdown格式
├── wsj_123457_20260210_143045.json
└── wsj_123457_20260210_143045.md
```

### JSON 格式示例

```json
{
  "id": 123456,
  "title": "美联储宣布维持利率不变",
  "content": "<p>美联储今日宣布...</p>",
  "content_text": "美联储今日宣布...",
  "created_at": "2026-02-10T14:30:00Z",
  "updated_at": "2026-02-10T14:30:00Z",
  "uri": "/live/123456",
  "url": "https://wallstreetcn.com/live/123456",
  "source": "华尔街见闻",
  "channel": "global",
  "importance": 5,
  "has_image": false,
  "images": []
}
```

### Markdown 格式示例

```markdown
# 美联储宣布维持利率不变

**来源**: 华尔街见闻
**频道**: global
**发布时间**: 2026-02-10T14:30:00Z
**重要性**: 5
**链接**: https://wallstreetcn.com/live/123456

---

## 内容

美联储今日宣布维持利率不变...

---

*抓取时间: 2026-02-10 14:30:22*
```

## 高级配置

### 调整轮询策略

编辑 `crawl/wallstreetcn.py`，修改 `WallStreetCNMonitor` 类：

```python
class WallStreetCNMonitor:
    def __init__(
        self,
        crawler: WallStreetCNLiveCrawler,
        poll_interval: int = 30,  # 轮询间隔（秒）
        channel: str = "global"   # 监控频道
    ):
        # ...
```

### 自定义请求头

如果遇到反爬虫限制，可以在 `_setup_headers()` 方法中添加更多请求头：

```python
def _setup_headers(self):
    self.session.headers.update({
        'User-Agent': '...',
        'Accept': '...',
        'Cookie': '...',  # 如果需要登录
        # 添加其他必要的请求头
    })
```

### 集成到现有监控系统

如果想将华尔街见闻爬虫集成到现有的 `monitor` 模块：

```python
from crawl.wallstreetcn import WallStreetCNLiveCrawler, WallStreetCNMonitor

# 在你的监控代码中
crawler = WallStreetCNLiveCrawler()
monitor = WallStreetCNMonitor(crawler, poll_interval=30)

def handle_new_items(items):
    # 自定义处理逻辑
    for item in items:
        print(f"新快讯: {item['title']}")
        # 保存到数据库、发送通知等

monitor.start(callback=handle_new_items)
```

## 常见问题

### Q1: 如何找到正确的 API 接口？

A: 按照"快速开始"第1步的说明，使用浏览器开发者工具抓包。常见的接口路径包括：
- `/apiv1/content/lives`
- `/api/v1/lives`
- `/api/lives`

### Q2: 爬虫返回空数据怎么办？

A: 可能的原因：
1. API 接口地址不正确 → 重新确认接口
2. 需要登录或 Cookie → 在 `_setup_headers()` 中添加 Cookie
3. API 响应结构变化 → 调整 `parse_live_item()` 中的字段映射
4. 被反爬虫拦截 → 降低请求频率，添加随机延迟

### Q3: 如何避免重复抓取？

A: 爬虫已实现增量抓取机制：
- 使用 `last_id` 记录最后一条快讯的ID
- 每次只获取比 `last_id` 更新的内容
- 文件名包含ID和时间戳，自动去重

### Q4: 如何调整抓取频率？

A: 使用 `--interval` 参数：
```bash
# 每10秒抓取一次（高频）
python -m crawl.wallstreetcn_runner --monitor --interval 10

# 每5分钟抓取一次（低频）
python -m crawl.wallstreetcn_runner --monitor --interval 300
```

建议：
- 测试阶段：60秒
- 生产环境：30秒
- 避免低于10秒，可能触发反爬虫

### Q5: 如何监控多个频道？

A: 启动多个进程，每个监控不同频道：

```bash
# 终端1：监控全球频道
python -m crawl.wallstreetcn_runner --monitor --channel global --interval 30

# 终端2：监控A股频道
python -m crawl.wallstreetcn_runner --monitor --channel a-stock --interval 30
```

## 技术架构

```
crawl/wallstreetcn.py
├── WallStreetCNLiveCrawler    # 爬虫核心类
│   ├── fetch_lives()          # 获取快讯列表
│   ├── parse_live_item()      # 解析单条快讯
│   └── fetch_incremental()    # 增量获取
│
└── WallStreetCNMonitor        # 监控器类
    ├── start()                # 启动监控
    └── stop()                 # 停止监控

crawl/wallstreetcn_runner.py  # 命令行入口
├── fetch_mode()               # 单次抓取模式
├── monitor_mode()             # 实时监控模式
├── save_to_json()             # 保存为JSON
└── save_to_markdown()         # 保存为Markdown
```

## 注意事项

1. **合规使用**：请遵守华尔街见闻的服务条款，合理控制抓取频率
2. **API 变化**：网站可能随时调整 API，需要定期检查和更新
3. **反爬虫**：如遇到限制，请降低频率或添加更多请求头
4. **数据存储**：长期运行会产生大量文件，建议定期清理或归档
5. **错误处理**：监控模式下遇到错误会自动重试，但建议添加日志监控

## 后续优化建议

- [ ] 添加数据库存储支持
- [ ] 实现 WebSocket 实时推送（如果API支持）
- [ ] 添加重要性过滤（只保存高重要性快讯）
- [ ] 集成通知系统（邮件、钉钉、企业微信）
- [ ] 添加数据分析和可视化
- [ ] 支持多账号轮换（避免限流）

## 联系与反馈

如有问题或建议，请提交 Issue 或 Pull Request。
