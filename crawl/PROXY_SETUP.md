# Investing.com 爬虫代理配置指南

## 问题说明

由于 Investing.com 会根据 IP 地址自动重定向到对应地区的站点，中国大陆 IP 会被强制重定向到 `cn.investing.com`（中文站点），导致无法爬取英文新闻。

## 解决方案：使用代理

### 1. HTTP/HTTPS 代理

如果你有 HTTP 代理服务器（如 Clash、V2Ray 等），使用 `--proxy` 参数：

```bash
# 使用 HTTP 代理
python crawl/investing_runner.py --all-channels --fetch-content --delay 3 --limit 5 --proxy http://127.0.0.1:7890

# 使用 HTTPS 代理
python crawl/investing_runner.py --all-channels --fetch-content --delay 3 --limit 5 --proxy https://127.0.0.1:7890
```

### 2. SOCKS5 代理

如果使用 SOCKS5 代理，需要先安装 `requests[socks]`：

```bash
pip install requests[socks]
```

然后使用：

```bash
python crawl/investing_runner.py --all-channels --fetch-content --delay 3 --limit 5 --proxy socks5://127.0.0.1:1080
```

### 3. 常见代理软件端口

- **Clash**: 默认 HTTP 端口 7890
- **V2Ray**: 默认 SOCKS5 端口 1080
- **Shadowsocks**: 默认 1080

### 4. 测试代理是否工作

```bash
# 测试单个频道，限制1条新闻
python crawl/investing_runner.py --channel commodities --fetch-content --limit 1 --proxy http://127.0.0.1:7890
```

如果看到以下输出，说明代理工作正常：
```
🌐 使用代理: http://127.0.0.1:7890
✅ 使用选择器: article[data-test='article-item']
✅ 成功获取 35 条新闻
```

如果看到以下错误，说明代理配置有问题：
```
❌ 检测到中文页面 (lang=zh-Hans, url=https://cn.investing.com)
```

## 无代理替代方案

如果没有代理，可以考虑：

1. **使用云服务器**：在海外云服务器上运行爬虫
2. **使用 VPN**：连接 VPN 后再运行爬虫
3. **使用免费代理**：搜索免费的 HTTP 代理（不推荐，不稳定）

## 完整示例

```bash
# 爬取所有频道，每个频道10条新闻，获取详细内容，使用代理
python crawl/investing_runner.py \
  --all-channels \
  --fetch-content \
  --delay 3 \
  --limit 10 \
  --proxy http://127.0.0.1:7890 \
  --output ./output
```
