# 华尔街见闻爬虫 - 商品资讯完整爬取方案

## ⚠️ 重要发现

华尔街见闻将商品资讯**分散在多个频道**中，单独监控 `commodity-channel` 会遗漏大量内容！

---

## 📊 商品相关频道分布

根据实际分析（前100条全球快讯）：

| 频道 | 快讯数量 | 占比 | 内容类型 |
|------|---------|------|---------|
| `oil-channel` | 9条 | 28% | **原油、能源** ⭐ |
| `gold-channel` | 7条 | 22% | **黄金** ⭐ |
| `gold-forex-channel` | 7条 | 22% | **黄金+外汇** ⭐ |
| `goldc-channel` | 5条 | 16% | **黄金C** |
| `commodity-channel` | 4条 | 12% | **其他商品** |
| **总计** | **32条** | **100%** | **所有商品资讯** |

### 关键发现

- ❌ 只监控 `commodity-channel` 只能获得 **12%** 的商品资讯
- ✅ 需要监控 **5个频道** 才能获得完整的商品资讯
- ⚠️ 你提到的 ID 3052599（委内瑞拉原油）属于 `oil-channel`，不在 `commodity-channel`

---

## 🚀 解决方案

### 方案1：多频道监控脚本（推荐）

我已经创建了 `multi_commodity_monitor.py`，可以同时监控所有商品频道：

```bash
# 监控所有5个商品相关频道
python -m crawl.multi_commodity_monitor

# 只监控重要快讯
python -m crawl.multi_commodity_monitor --important

# 自定义轮询间隔
python -m crawl.multi_commodity_monitor --interval 60

# 只监控特定频道（如原油+黄金）
python -m crawl.multi_commodity_monitor --channels oil-channel gold-channel
```

**优势**：
- ✅ 一个命令监控5个频道
- ✅ 自动去重（使用 content_digest）
- ✅ 统一保存到同一目录
- ✅ 获得100%的商品资讯

---

### 方案2：监控全球频道（最简单）

```bash
# 监控全球频道，获取所有快讯（包括所有商品资讯）
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel global-channel
```

**优势**：
- ✅ 最简单，一个命令搞定
- ✅ 获得所有市场的快讯
- ✅ 包含所有商品资讯

**劣势**：
- ❌ 会获取非商品的快讯（股票、债券等）
- ❌ 数据量较大

---

### 方案3：手动启动多个进程

```bash
# 终端1：监控大宗商品
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel

# 终端2：监控原油
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel oil-channel

# 终端3：监控黄金
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel gold-channel

# 终端4：监控黄金外汇
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel gold-forex-channel

# 终端5：监控黄金C
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel goldc-channel
```

**优势**：
- ✅ 完全控制每个频道
- ✅ 可以为不同频道设置不同的轮询间隔

**劣势**：
- ❌ 需要开5个终端
- ❌ 管理复杂

---

## 💡 推荐方案对比

| 方案 | 命令数量 | 覆盖率 | 复杂度 | 推荐度 |
|------|---------|--------|--------|--------|
| 方案1：多频道脚本 | 1个 | 100% | 低 | ⭐⭐⭐⭐⭐ |
| 方案2：全球频道 | 1个 | 100%+ | 最低 | ⭐⭐⭐⭐ |
| 方案3：多进程 | 5个 | 100% | 高 | ⭐⭐ |

---

## 🎯 推荐配置

### 配置1：多频道监控（最推荐）

```bash
# 监控所有商品相关频道
python -m crawl.multi_commodity_monitor --interval 30
```

**输出示例**：
```
============================================================
🎯 华尔街见闻 - 多频道商品监控
============================================================
监控频道: 5 个
  - commodity-channel
  - oil-channel
  - gold-channel
  - gold-forex-channel
  - goldc-channel
轮询间隔: 30 秒
过滤模式: 全部快讯
按 Ctrl+C 停止监控
============================================================

🚀 启动 commodity-channel 监控
🚀 启动 oil-channel 监控
🚀 启动 gold-channel 监控
🚀 启动 gold-forex-channel 监控
🚀 启动 goldc-channel 监控

============================================================
📰 [oil-channel] 收到 1 条新快讯
============================================================

1. [2026-02-10 08:54:41] 委内瑞拉主产油区恢复，全国产量接近100万桶/日
   知情人士表示，委内瑞拉国有石油公司PDVSA已基本恢复奥里诺科重油带...
   🔗 https://wallstreetcn.com/livenews/3052599

💾 保存快讯...
   ✅ 已保存: WSJ_20260210_3052599.json
============================================================
```

---

### 配置2：全球频道（最简单）

```bash
# 监控全球频道，包含所有商品资讯
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel global-channel
```

**优势**：
- 最简单，一个命令
- 获得所有市场快讯
- 包含所有商品资讯

---

## 📈 数据覆盖率对比

### 只监控 commodity-channel

```bash
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel
```

**覆盖率**: 12%（100条中只有4条）

**遗漏内容**：
- ❌ 原油资讯（oil-channel）
- ❌ 黄金资讯（gold-channel）
- ❌ 黄金外汇（gold-forex-channel）
- ❌ 黄金C（goldc-channel）

---

### 监控所有商品频道（推荐）

```bash
python -m crawl.multi_commodity_monitor --interval 30
```

**覆盖率**: 100%（所有商品资讯）

**包含内容**：
- ✅ 大宗商品（commodity-channel）
- ✅ 原油资讯（oil-channel）⭐
- ✅ 黄金资讯（gold-channel）⭐
- ✅ 黄金外汇（gold-forex-channel）
- ✅ 黄金C（goldc-channel）

---

### 监控全球频道

```bash
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel global-channel
```

**覆盖率**: 100%+（所有快讯，包括非商品）

**包含内容**：
- ✅ 所有商品资讯
- ✅ 股票、债券、外汇等其他资讯

---

## 🔍 为什么 ID 3052599 没有爬到？

### 原因分析

```
ID 3052599: 委内瑞拉主产油区恢复，全国产量接近100万桶/日
频道: global-channel, forex-channel, oil-channel
```

**结论**：
- ❌ 这条快讯**不属于** `commodity-channel`
- ✅ 这条快讯属于 `oil-channel`（原油频道）
- ⚠️ 华尔街见闻将原油单独分类到 `oil-channel`，而不是 `commodity-channel`

---

## 💡 解决方案总结

### 如果你想获得所有商品资讯，有3个选择：

#### 选择1：多频道监控（最推荐）⭐⭐⭐⭐⭐

```bash
python -m crawl.multi_commodity_monitor --interval 30
```

**优势**：
- ✅ 覆盖100%的商品资讯
- ✅ 一个命令搞定
- ✅ 自动去重
- ✅ 包含原油、黄金等所有商品

---

#### 选择2：全球频道（最简单）⭐⭐⭐⭐

```bash
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel global-channel
```

**优势**：
- ✅ 最简单
- ✅ 包含所有商品资讯
- ✅ 还包含其他市场资讯

**劣势**：
- ❌ 会获取非商品的快讯

---

#### 选择3：手动监控5个频道⭐⭐

需要开5个终端，分别监控：
- commodity-channel
- oil-channel
- gold-channel
- gold-forex-channel
- goldc-channel

---

## 📊 实际测试

### 测试1：只监控 commodity-channel

```bash
$ python -m crawl.wallstreetcn_runner --fetch --limit 20 --channel commodity-channel
✅ 成功获取 4 条快讯
```

**结果**：只获得4条，遗漏了原油、黄金等资讯

---

### 测试2：监控所有商品频道

```bash
$ python -m crawl.multi_commodity_monitor --channels commodity-channel oil-channel gold-channel
```

**结果**：获得所有商品资讯，包括：
- ✅ 碳酸锂价格（commodity-channel）
- ✅ 委内瑞拉原油（oil-channel）⭐
- ✅ 黄金ETF（gold-channel）
- ✅ 稀土价格（commodity-channel）

---

## 🎉 最终推荐

### 推荐命令（获得所有商品资讯）

```bash
# 方式1：多频道监控（推荐）
python -m crawl.multi_commodity_monitor --interval 30

# 方式2：全球频道（最简单）
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel global-channel
```

### 如果只想要重要的商品资讯

```bash
# 方式1：多频道 + 重要过滤
python -m crawl.multi_commodity_monitor --interval 30 --important

# 方式2：全球频道 + 重要过滤
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel global-channel --important
```

---

## 📁 输出文件

所有商品资讯都会保存到同一目录：

```
articles/wallstreetcn/
├── WSJ_20260210_3052664.json  ← 碳酸锂（commodity-channel）
├── WSJ_20260210_3052599.json  ← 委内瑞拉原油（oil-channel）⭐
├── WSJ_20260210_3052555.json  ← 镨钕价格（commodity-channel）
├── WSJ_20260210_3052528.json  ← 黄金指数（gold-channel）
└── WSJ_20260210_3052526.json  ← 白银期货（gold-channel）
```

**自动去重**：使用 `content_digest` 确保不会重复保存

---

## 🔧 核心文件

- **单频道工具**: `crawl/wallstreetcn_runner.py`
- **多频道工具**: `crawl/multi_commodity_monitor.py` ⭐ 新增
- **爬虫核心**: `crawl/wallstreetcn.py`
- **格式化器**: `crawl/wallstreetcn_formatter.py`

---

## 📚 完整文档

- **商品爬取方案**: `docs/WALLSTREETCN_COMMODITY_SOLUTION.md`（本文档）⭐⭐⭐
- **频道列表**: `docs/WALLSTREETCN_CHANNELS.md`
- **格式对应**: `docs/WALLSTREETCN_LONGZHONG_FORMAT.md`
- **快速参考**: `docs/WALLSTREETCN_QUICK_REFERENCE.md`

---

## 🎉 总结

### 问题原因

- ❌ 华尔街见闻将商品资讯分散在5个频道
- ❌ 只监控 `commodity-channel` 只能获得12%的商品资讯
- ❌ 原油资讯在 `oil-channel`，黄金资讯在 `gold-channel`

### 解决方案

- ✅ 使用 `multi_commodity_monitor.py` 监控所有5个频道
- ✅ 或者监控 `global-channel` 获得所有快讯
- ✅ 自动去重，避免重复保存

### 推荐命令

```bash
# 最推荐：多频道监控
python -m crawl.multi_commodity_monitor --interval 30

# 最简单：全球频道
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel global-channel
```

---

**最后更新**: 2026-02-10
**状态**: ✅ 问题已解决
**覆盖率**: ✅ 100%商品资讯

---

## 🚀 现在就开始！

```bash
# 推荐命令：监控所有商品频道，获得100%的商品资讯
python -m crawl.multi_commodity_monitor --interval 30
```

这样就能获得包括原油、黄金在内的所有商品资讯了！📈🎉
