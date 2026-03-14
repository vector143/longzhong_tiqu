# Investing.com 新闻爬虫（多频道支持）

自动爬取 Investing.com 多个频道的新闻。

## 支持的频道

- **commodities** - 商品新闻 (https://www.investing.com/news/commodities-news)
- **economic-indicators** - 经济指标 (https://www.investing.com/news/economic-indicators)
- **economy** - 经济新闻 (https://www.investing.com/news/economy)

## 功能特点

- ✅ 支持多个新闻频道
- ✅ 可单独或批量爬取所有频道
- ✅ 自动爬取新闻列表（支持多页）
- ✅ 可选获取文章详细内容
- ✅ 智能反爬虫处理（headers、cookies、延迟）
- ✅ 标准 JSON 格式输出
- ✅ 文件名包含频道标识

## 安装依赖

```bash
pip install requests beautifulsoup4 brotli
```

## 使用方法

### 1. 爬取单个频道

```bash
# 爬取商品新闻
python crawl/investing_runner.py --channel commodities --pages 3

# 爬取经济指标新闻
python crawl/investing_runner.py --channel economic-indicators --pages 2

# 爬取经济新闻
python crawl/investing_runner.py --channel economy --pages 3
```

### 2. 爬取所有频道

```bash
# 一次性爬取所有频道（推荐）
python crawl/investing_runner.py --all-channels --pages 2

# 爬取所有频道并获取详细内容
python crawl/investing_runner.py --all-channels --pages 1 --fetch-content --delay 3
```

### 3. 获取详细内容

```bash
# 爬取并获取每篇文章的详细内容
python crawl/investing_runner.py --channel commodities --pages 2 --fetch-content
```

### 4. 自定义配置

```bash
# 自定义延迟和输出目录
python crawl/investing_runner.py --channel economy --pages 3 --delay 5 --output ./my_output

# 限制爬取数量（只爬前10条）
python crawl/investing_runner.py --channel commodities --pages 2 --limit 10

# 组合使用：爬取所有频道，每个频道限制20条，获取详细内容
python crawl/investing_runner.py --all-channels --pages 3 --limit 20 --fetch-content --delay 3
```

## 命令行参数

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--channel` | - | 新闻频道 (commodities/economic-indicators/economy) | commodities |
| `--all-channels` | `-a` | 爬取所有频道 | False |
| `--pages` | `-p` | 爬取页数 | 3 |
| `--limit` | `-l` | 限制每个频道爬取的新闻数量 | 无限制 |
| `--delay` | `-d` | 请求延迟（秒） | 2.0 |
| `--fetch-content` | `-f` | 获取文章详细内容 | False |
| `--output` | `-o` | 输出目录 | ./output |

## 输出格式

每篇新闻保存为独立的 JSON 文件，格式如下：

```json
{
  "article_id": "4498596",
  "title": "China CPI inflation undershoots forecasts in Jan",
  "date": "2026-02-11",
  "time": "01:52:22",
  "source": "Investing.com",
  "category": "economic-indicators",
  "author": "Author Name",
  "url": "https://www.investing.com/news/...",
  "summary": "Article summary...",
  "content": "Full article content...",
  "html_content": "<div>HTML content...</div>",
  "raw_publish_time": "2026-02-11 01:52:22",
  "crawl_time": "2026-02-11 10:41:04"
}
```

## 文件命名规则

文件名格式：`INVESTING_{CHANNEL}_{YYYYMMDD}_{ArticleID}.json`

示例：
- `INVESTING_COMMODITIES_20260211_4498588.json` - 商品新闻
- `INVESTING_ECONOMIC_INDICATORS_20260211_4498596.json` - 经济指标
- `INVESTING_ECONOMY_20260210_4495796.json` - 经济新闻

## 使用示例

### 示例 1: 快速获取最新商品新闻

```bash
# 只爬取第1页，不获取详细内容（最快）
python crawl/investing_runner.py --channel commodities --pages 1
```

### 示例 2: 深度爬取经济指标

```bash
# 爬取前3页，获取所有详细内容（较慢）
python crawl/investing_runner.py --channel economic-indicators --pages 3 --fetch-content --delay 3
```

### 示例 3: 批量爬取所有频道

```bash
# 一次性爬取所有频道的最新新闻
python crawl/investing_runner.py --all-channels --pages 2 --delay 3
```

### 示例 4: 定时任务

```bash
# 配合 cron 定时执行
# 每小时爬取所有频道的最新一页，每个频道限制15条
0 * * * * cd /path/to/project && python crawl/investing_runner.py --all-channels --pages 1 --limit 15
```

### 示例 5: 限制数量爬取

```bash
# 只爬取每个频道的前10条新闻（快速测试）
python crawl/investing_runner.py --all-channels --pages 2 --limit 10

# 爬取前20条并获取详细内容
python crawl/investing_runner.py --channel economy --pages 3 --limit 20 --fetch-content --delay 3
```

## 注意事项

1. **反爬虫限制**：Investing.com 有反爬虫保护，建议：
   - 设置合理的延迟（建议 2-5 秒）
   - 避免频繁大量爬取
   - 遵守网站的 robots.txt
   - 如遇 403 错误，等待几分钟后再试

2. **获取详细内容**：
   - 使用 `--fetch-content` 会显著增加爬取时间
   - 每篇文章都需要额外的 HTTP 请求
   - 建议先爬取列表，再按需获取详细内容

3. **数据保存**：
   - 默认保存到 `./output/` 目录
   - 相同 article_id 的文章会被覆盖
   - 建议定期备份数据
   - 不同频道的文件通过文件名前缀区分

4. **多频道爬取**：
   - 使用 `--all-channels` 会依次爬取所有频道
   - 总耗时 = 单频道耗时 × 频道数量
   - 建议合理设置延迟，避免触发反爬虫

## 故障排除

### 403 Forbidden 错误

如果遇到 403 错误，尝试：
1. 增加延迟时间：`--delay 5`
2. 减少爬取页数
3. 等待一段时间后再试
4. 检查网络连接

### Brotli 解码错误

如果遇到 brotli 相关错误：
```bash
pip install brotli
```

### 网络超时

如果网络不稳定，可以修改代码中的 timeout 参数（默认 15 秒）。

## 代码结构

```
crawl/
├── investing_crawler.py      # 核心爬虫类（支持多频道）
├── investing_formatter.py    # 数据格式化器
├── investing_runner.py       # 命令行运行脚本
├── investing_example.py      # 使用示例
└── README_INVESTING.md       # 本文档
```

## API 使用

也可以在 Python 代码中直接使用：

```python
from crawl.investing_crawler import InvestingCommodityNewsCrawler
from crawl.investing_formatter import InvestingFormatter

# 初始化爬虫（指定频道）
crawler = InvestingCommodityNewsCrawler(channel="economic-indicators")

# 获取新闻列表
result = crawler.fetch_news_list(page=1, delay=2.0)
if result['success']:
    news_list = result['data']
    print(f"获取到 {len(news_list)} 条新闻")
    print(f"频道: {result['channel']}")

# 获取文章详细内容
article_url = news_list[0]['url']
content = crawler.fetch_article_content(article_url)
if content['success']:
    print(content['title'])
    print(content['content'])

# 格式化数据
formatter = InvestingFormatter()
standard_data = formatter.format_to_standard(news_list[0])
```

### 多频道爬取示例

```python
from crawl.investing_crawler import InvestingCommodityNewsCrawler

channels = ["commodities", "economic-indicators", "economy"]

for channel in channels:
    print(f"正在爬取频道: {channel}")
    crawler = InvestingCommodityNewsCrawler(channel=channel)

    result = crawler.fetch_news_list(page=1, delay=2.0)
    if result['success']:
        print(f"  {channel}: {len(result['data'])} 条新闻")
```

## 测试结果

已成功测试并验证：
- ✅ 单频道爬取：每个频道约 35 条新闻/页
- ✅ 多频道爬取：成功爬取所有 3 个频道
- ✅ 文件命名：正确包含频道标识
- ✅ 数据格式：符合标准 JSON 格式
- ✅ 详细内容获取：成功获取完整文章内容

## 更新日志

- **2026-02-11 v2.0**:
  - 新增多频道支持
  - 支持 commodities、economic-indicators、economy 三个频道
  - 新增 `--all-channels` 参数批量爬取
  - 文件名包含频道标识
  - 优化命令行参数

- **2026-02-11 v1.0**:
  - 初始版本发布
  - 支持新闻列表爬取
  - 支持详细内容获取
  - 标准 JSON 格式输出

## 许可证

本项目仅供学习和研究使用，请遵守目标网站的使用条款。
