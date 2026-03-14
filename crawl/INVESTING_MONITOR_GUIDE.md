# Investing.com 监控脚本使用指南

## 功能特性

1. **历史爬取**：首次运行时爬取每个频道的历史文章（可指定数量）
2. **增量爬取**：只爬取新文章，自动跳过已存在的文章
3. **自动去重**：基于内容 SHA1 哈希去重，避免重复爬取
4. **持续监控**：定时检查新文章，自动保存
5. **标准格式**：输出格式与隆众、华尔街见闻完全一致

## 使用方法

### 1. 首次运行：爬取历史文章

```bash
# 爬取每个频道100篇历史文章
python crawl/investing_monitor.py --history 100 --proxy http://127.0.0.1:7897

# 只爬取特定频道的历史文章
python crawl/investing_monitor.py --history 50 --channels commodities --proxy http://127.0.0.1:7897

# 自定义延迟和输出目录
python crawl/investing_monitor.py --history 100 --delay 2 --output ./data --proxy http://127.0.0.1:7897
```

### 2. 增量爬取：单次检查新文章

```bash
# 检查所有频道的新文章（单次）
python crawl/investing_monitor.py --proxy http://127.0.0.1:7897

# 只检查特定频道
python crawl/investing_monitor.py --channels commodities economy --proxy http://127.0.0.1:7897
```

### 3. 持续监控：定时自动爬取

```bash
# 每5分钟检查一次新文章（默认）
python crawl/investing_monitor.py --monitor --proxy http://127.0.0.1:7897

# 每10分钟检查一次
python crawl/investing_monitor.py --monitor --interval 600 --proxy http://127.0.0.1:7897

# 只监控特定频道
python crawl/investing_monitor.py --monitor --channels commodities --proxy http://127.0.0.1:7897
```

## 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `--history N` | 历史爬取模式，每个频道爬取N篇文章 | `--history 100` |
| `--monitor` / `-m` | 持续监控模式 | `--monitor` |
| `--interval N` / `-i N` | 监控间隔（秒），默认300秒 | `--interval 600` |
| `--channels` / `-c` | 指定频道列表 | `--channels commodities economy` |
| `--delay N` / `-d N` | 请求延迟（秒），默认3秒 | `--delay 2` |
| `--output DIR` / `-o DIR` | 输出目录，默认./output | `--output ./data` |
| `--proxy URL` / `-x URL` | 代理地址 | `--proxy http://127.0.0.1:7897` |

## 频道列表

- `commodities` - 大宗商品新闻
- `economic-indicators` - 经济指标新闻
- `economy` - 宏观经济新闻

## 去重机制

脚本会在输出目录生成 `investing_articles.db.json` 文件，记录所有已爬取文章的内容哈希：

```json
{
  "digests": ["hash1", "hash2", "..."],
  "last_update": "2026-02-11 11:29:25",
  "total_count": 150
}
```

- 基于文章内容的 SHA1 哈希去重
- 即使文章URL不同，内容相同也会被识别为重复
- 删除此文件会重新爬取所有文章

## 输出格式

所有文章保存为标准JSON格式，与隆众、华尔街见闻完全一致：

```json
{
  "cleaned_text": "# 标题\n\n内容...",
  "date": "2026-02-11",
  "institution": "Investing.com",
  "title": "标题",
  "period": "d",
  "category": "大宗商品",
  "researchers": ["作者"],
  "content_type": "资讯",
  "source_json_path": "",
  "content_digest": "sha1哈希",
  "publish_time": "2026-02-11 02:48:33",
  "source_url": "https://...",
  "article_id": "4498614"
}
```

## 文件命名规则

```
INVESTING_{频道}_{日期}_{文章ID}.json
```

示例：
- `INVESTING_COMMODITIES_20260211_4498614.json`
- `INVESTING_ECONOMIC_INDICATORS_20260211_4498228.json`
- `INVESTING_ECONOMY_20260210_4496477.json`

## 推荐工作流程

### 首次使用

```bash
# 1. 爬取历史文章（每个频道100篇）
python crawl/investing_monitor.py --history 100 --proxy http://127.0.0.1:7897

# 2. 启动持续监控（每5分钟检查一次）
python crawl/investing_monitor.py --monitor --interval 300 --proxy http://127.0.0.1:7897
```

### 日常使用

```bash
# 方式1：手动增量爬取（每天运行一次）
python crawl/investing_monitor.py --proxy http://127.0.0.1:7897

# 方式2：持续监控（后台运行）
nohup python crawl/investing_monitor.py --monitor --proxy http://127.0.0.1:7897 > investing_monitor.log 2>&1 &
```

### 使用 systemd 服务（Linux）

创建服务文件 `/etc/systemd/system/investing-monitor.service`：

```ini
[Unit]
Description=Investing.com News Monitor
After=network.target

[Service]
Type=simple
User=<your-user>
WorkingDirectory=/path/to/longzhong_tiqu
ExecStart=/path/to/anaconda3/envs/longzhong/bin/python crawl/investing_monitor.py --monitor --interval 300 --proxy http://127.0.0.1:7897
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable investing-monitor
sudo systemctl start investing-monitor
sudo systemctl status investing-monitor
```

查看日志：

```bash
sudo journalctl -u investing-monitor -f
```

## 注意事项

1. **必须使用代理**：由于IP限制，必须使用 `--proxy` 参数
2. **合理设置延迟**：建议 `--delay` 不小于2秒，避免被封IP
3. **监控间隔**：建议 `--interval` 不小于300秒（5分钟）
4. **历史爬取**：首次运行建议爬取100-200篇，不要太多
5. **去重数据库**：不要删除 `investing_articles.db.json` 文件

## 故障排查

### 问题1：被重定向到中文站点

```
❌ 检测到中文页面 (lang=zh-Hans, url=https://cn.investing.com)
```

**解决方案**：确保使用了代理参数 `--proxy http://127.0.0.1:7897`

### 问题2：代理连接失败

```
❌ 请求失败: ProxyError...
```

**解决方案**：
1. 检查代理是否正在运行：`nc -zv 127.0.0.1 7897`
2. 确认代理地址正确
3. 尝试其他代理端口

### 问题3：爬取速度慢

**解决方案**：
1. 减小 `--delay` 参数（但不要小于2秒）
2. 只爬取需要的频道：`--channels commodities`
3. 使用更快的代理服务器

### 问题4：重复爬取文章

**解决方案**：
1. 检查 `investing_articles.db.json` 是否存在
2. 确认文件权限正常
3. 查看日志中是否有保存失败的提示

## 统计信息

查看已爬取文章数量：

```bash
cat output/investing_articles.db.json | python -c "import sys, json; d=json.load(sys.stdin); print(f'总计: {d[\"total_count\"]} 篇文章')"
```

查看各频道文章数量：

```bash
ls output/INVESTING_*.json | awk -F'_' '{print $2}' | sort | uniq -c
```

查看最新爬取时间：

```bash
cat output/investing_articles.db.json | python -c "import sys, json; d=json.load(sys.stdin); print(f'最后更新: {d[\"last_update\"]}')"
```
