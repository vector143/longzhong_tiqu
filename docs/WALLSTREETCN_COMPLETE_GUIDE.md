# 华尔街见闻实时爬虫 - 完整使用指南

## 🎉 功能概览

✅ **实时监控** - 自动轮询获取最新快讯
✅ **增量抓取** - 智能去重，只获取新内容
✅ **重要过滤** - 支持"只看重要的"功能
✅ **双格式输出** - JSON + Markdown 自动保存
✅ **多频道支持** - 全球/外汇/美股/A股等
✅ **已验证可用** - 真实API测试通过

---

## 🚀 快速开始

### 1. 基础用法

```bash
# 单次抓取最新20条快讯
python -m crawl.wallstreetcn_runner --fetch --limit 20

# 实时监控（每30秒轮询）
python -m crawl.wallstreetcn_runner --monitor --interval 30
```

### 2. 只看重要的（推荐）

```bash
# 只抓取重要快讯（Score >= 2）
python -m crawl.wallstreetcn_runner --fetch --limit 50 --important

# 实时监控重要快讯
python -m crawl.wallstreetcn_runner --monitor --interval 30 --min-score 2
```

### 3. 后台运行

```bash
# 使用 nohup 后台运行
nohup python -m crawl.wallstreetcn_runner --monitor --interval 30 --important > wsj.log 2>&1 &

# 查看日志
tail -f wsj.log

# 停止运行
ps aux | grep wallstreetcn_runner
kill <进程ID>
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
  --interval, -i         监控轮询间隔（秒） (默认: 30)
  --limit, -l            单次抓取数量 (默认: 20)
  --format               保存格式: json/markdown/both (默认: both)

过滤参数:
  --important            只抓取重要快讯 (Score >= 2)
  --min-score            最低评分过滤: 1=全部, 2=重要 (默认: 1)
```

---

## 📊 使用场景

### 场景1：全面监控（默认）

```bash
python -m crawl.wallstreetcn_runner --monitor --interval 30
```

**特点**：
- 获取所有快讯（Score >= 1）
- 适合需要全面信息的场景
- 每30秒轮询一次

**输出**：50条快讯中获取全部50条

---

### 场景2：精准监控（推荐）

```bash
python -m crawl.wallstreetcn_runner --monitor --interval 30 --important
```

**特点**：
- 只获取重要快讯（Score >= 2）
- 过滤掉94%的普通快讯
- 专注高价值信息

**输出**：50条快讯中筛选出3条重要快讯

---

### 场景3：高频监控

```bash
python -m crawl.wallstreetcn_runner --monitor --interval 15 --important
```

**特点**：
- 每15秒轮询一次
- 只关注重要快讯
- 适合需要极速响应的场景

**注意**：高频轮询可能触发反爬虫，建议配合 `--important` 使用

---

### 场景4：双模式并行

```bash
# 终端1：高频监控重要快讯
python -m crawl.wallstreetcn_runner --monitor --interval 15 --important

# 终端2：低频备份全部快讯
python -m crawl.wallstreetcn_runner --monitor --interval 60
```

**特点**：
- 重要信息实时获取（15秒）
- 全部信息定期备份（60秒）
- 兼顾实时性和完整性

---

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
  "id": 3052662,
  "title": "传媒板块涨势扩大",
  "content": "<p>传媒板块涨势扩大...</p>",
  "content_text": "传媒板块涨势扩大...",
  "display_time": 1770690364,
  "display_time_str": "2026-02-10 10:26:04",
  "url": "https://wallstreetcn.com/livenews/3052662",
  "source": "华尔街见闻",
  "channels": ["global-channel"],
  "score": 2,  ← 重要性评分
  "author_name": "A股团队",
  "author_id": 110000000001,
  "has_image": false,
  "images": [],
  "comment_count": 0,
  "type": "live"
}
```

### Markdown 格式示例

```markdown
# 传媒板块涨势扩大

**来源**: 华尔街见闻
**作者**: A股团队
**频道**: global-channel
**发布时间**: 2026-02-10 10:26:04
**评分**: 2  ← 重要快讯
**链接**: https://wallstreetcn.com/livenews/3052662

---

## 内容

传媒板块涨势扩大，读客文化冲击20cm涨停...

---

*抓取时间: 2026-02-10 10:26:44*
```

---

## 🎯 重要性评分说明

华尔街见闻的快讯有评分系统：

| Score | 类型 | 占比 | 说明 |
|-------|------|------|------|
| 1 | 普通快讯 | ~94% | 常规市场动态 |
| 2 | 重要快讯 | ~6% | 重大市场事件 |

**实测数据**（50条快讯）：
- Score 1: 47条（94%）
- Score 2: 3条（6%）

**重要快讯示例**：
- 恒指日内涨幅扩大至1%
- 日经225指数涨幅扩大至2%
- 传媒板块涨势扩大，多股涨停

---

## 🔧 在代码中使用

### 基础用法

```python
from crawl.wallstreetcn import WallStreetCNLiveCrawler

# 创建爬虫实例
crawler = WallStreetCNLiveCrawler()

# 获取最新快讯
items = crawler.fetch_incremental(
    channel="global-channel",
    limit=20
)

for item in items:
    print(f"[{item['display_time_str']}] {item['title'] or '快讯'}")
    print(f"内容: {item['content_text'][:100]}...")
    print(f"评分: {item['score']}")
    print()
```

### 只获取重要快讯

```python
# 方式1：使用 important_only 参数
important_items = crawler.fetch_incremental(
    channel="global-channel",
    limit=50,
    important_only=True
)

# 方式2：使用 min_score 参数
important_items = crawler.fetch_incremental(
    channel="global-channel",
    limit=50,
    min_score=2
)

print(f"获取到 {len(important_items)} 条重要快讯")
```

### 实时监控

```python
from crawl.wallstreetcn import WallStreetCNLiveCrawler, WallStreetCNMonitor

crawler = WallStreetCNLiveCrawler()

def on_new_news(items):
    print(f"📰 收到 {len(items)} 条新快讯")
    for item in items:
        print(f"  [{item['display_time_str']}] {item['title'] or '快讯'}")
        print(f"  评分: {item['score']}")

        # 自定义处理逻辑
        if item['score'] >= 2:
            # 发送通知
            send_notification(item)

        # 保存到数据库
        save_to_database(item)

# 创建监控器
monitor = WallStreetCNMonitor(
    crawler=crawler,
    poll_interval=30,
    channel="global-channel",
    important_only=True,  # 只监控重要快讯
    min_score=2
)

# 启动监控
monitor.start(callback=on_new_news)
```

---

## 💡 最佳实践

### 1. 轮询间隔建议

| 场景 | 间隔 | 说明 |
|------|------|------|
| 测试阶段 | 60秒 | 避免频繁请求 |
| 生产环境（全部） | 30-60秒 | 平衡实时性和请求频率 |
| 生产环境（重要） | 15-30秒 | 重要快讯可以更高频 |
| 高频监控 | 10-15秒 | 需注意反爬虫风险 |

### 2. 过滤策略建议

| 需求 | 配置 | 说明 |
|------|------|------|
| 全面监控 | `--interval 30` | 获取所有快讯 |
| 精准监控 | `--interval 30 --important` | 只看重要的 |
| 极速响应 | `--interval 15 --important` | 高频+重要 |
| 双重保障 | 两个进程并行 | 重要+全部 |

### 3. 存储优化

```bash
# 只保存重要快讯的JSON格式（节省空间）
python -m crawl.wallstreetcn_runner --monitor --interval 30 --important --format json

# 定期清理旧文件
find articles/wallstreetcn/ -name "*.json" -mtime +7 -delete  # 删除7天前的文件
```

### 4. 日志管理

```bash
# 后台运行并记录日志
nohup python -m crawl.wallstreetcn_runner --monitor --interval 30 --important \
  > logs/wsj_$(date +%Y%m%d).log 2>&1 &

# 实时查看日志
tail -f logs/wsj_$(date +%Y%m%d).log

# 日志轮转（每天一个文件）
# 在 crontab 中添加：
# 0 0 * * * pkill -f wallstreetcn_runner && nohup python -m crawl.wallstreetcn_runner --monitor --interval 30 --important > logs/wsj_$(date +%Y%m%d).log 2>&1 &
```

---

## 🔍 故障排查

### 问题1：无法获取数据

**症状**：`❌ 未获取到快讯`

**可能原因**：
1. 网络连接问题
2. API接口变化
3. 被反爬虫拦截

**解决方法**：
```bash
# 测试网络连接
curl -I https://api-one-wscn.awtmt.com/apiv1/content/lives

# 查看详细错误
python -m crawl.wallstreetcn_runner --fetch --limit 1

# 降低请求频率
python -m crawl.wallstreetcn_runner --monitor --interval 60
```

### 问题2：重要快讯过滤不生效

**症状**：使用 `--important` 但仍获取到所有快讯

**解决方法**：
```bash
# 确认使用了正确的参数
python -m crawl.wallstreetcn_runner --fetch --limit 50 --min-score 2

# 检查输出中的过滤模式提示
# 应该显示：过滤模式: 重要快讯 (min_score=2)
```

### 问题3：文件保存失败

**症状**：`❌ 保存失败`

**解决方法**：
```bash
# 检查目录权限
ls -la articles/wallstreetcn/

# 手动创建目录
mkdir -p articles/wallstreetcn/

# 检查磁盘空间
df -h
```

---

## 📚 相关文档

- **快速开始**: `README_WALLSTREETCN.md`
- **详细文档**: `docs/WALLSTREETCN_GUIDE.md`
- **重要过滤**: `docs/WALLSTREETCN_IMPORTANT_FILTER.md`（本文档）
- **核心代码**: `crawl/wallstreetcn.py`
- **命令行工具**: `crawl/wallstreetcn_runner.py`

---

## 🎉 总结

华尔街见闻爬虫现在支持完整的"只看重要的"功能：

✅ **智能过滤** - 基于官方评分系统（Score 1/2）
✅ **双重模式** - 支持 `--important` 和 `--min-score`
✅ **实时监控** - 自动轮询，增量抓取
✅ **灵活配置** - 可随时切换过滤级别
✅ **性能优化** - 减少94%的数据处理量
✅ **已验证可用** - 真实API测试通过

**推荐配置**：
```bash
# 生产环境推荐
python -m crawl.wallstreetcn_runner --monitor --interval 30 --important
```

这样可以：
- 每30秒轮询一次（平衡实时性和请求频率）
- 只获取重要快讯（过滤94%的噪音）
- 自动保存为JSON和Markdown格式
- 增量抓取，避免重复

---

**最后更新**: 2026-02-10
**功能状态**: ✅ 已测试可用
**测试数据**: 50条快讯中筛选出3条重要快讯（过滤率94%）
