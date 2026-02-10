# 华尔街见闻爬虫 - 快速参考

## 🚀 一键启动

```bash
# 推荐配置：只保存重要快讯的标准JSON格式
python -m crawl.wallstreetcn_runner --monitor --interval 30 --important
```

---

## 📋 常用命令

### 单次抓取

```bash
# 抓取最新20条快讯
python -m crawl.wallstreetcn_runner --fetch --limit 20

# 只抓取重要快讯
python -m crawl.wallstreetcn_runner --fetch --limit 50 --important

# 抓取并保存为Markdown
python -m crawl.wallstreetcn_runner --fetch --limit 20 --format markdown
```

### 实时监控

```bash
# 监控全部快讯（每30秒）
python -m crawl.wallstreetcn_runner --monitor --interval 30

# 只监控重要快讯（推荐）
python -m crawl.wallstreetcn_runner --monitor --interval 30 --important

# 高频监控重要快讯
python -m crawl.wallstreetcn_runner --monitor --interval 15 --min-score 2
```

### 后台运行

```bash
# 后台运行并记录日志
nohup python -m crawl.wallstreetcn_runner --monitor --interval 30 --important > wsj.log 2>&1 &

# 查看日志
tail -f wsj.log

# 停止运行
ps aux | grep wallstreetcn_runner
kill <进程ID>
```

---

## 📊 输出格式对比

### 标准JSON格式（默认，推荐）

**文件名**: `WSJ_2026-02-10_102604_3052662.json`

**优势**:
- ✅ 兼容隆众资讯格式
- ✅ 统一数据结构
- ✅ 便于批量处理
- ✅ 支持内容去重
- ✅ 易于数据分析

**示例**:
```json
{
  "articleId": "3052662",
  "title": "快讯_3052662",
  "publishTime": "2026-02-10 10:26:04",
  "url": "https://wallstreetcn.com/livenews/3052662",
  "columnName": "重要快讯",
  "source": "华尔街见闻",
  "content": "传媒板块涨势扩大...",
  "score": 2,
  "is_important": true
}
```

### Markdown格式（可选）

**文件名**: `wsj_3052662_2026-02-10_102604.md`

**优势**:
- ✅ 易读性强
- ✅ 适合人工查看
- ✅ 支持富文本

**示例**:
```markdown
# 快讯

**来源**: 华尔街见闻
**作者**: A股团队
**发布时间**: 2026-02-10 10:26:04
**评分**: 2

---

## 内容

传媒板块涨势扩大...
```

---

## 🎯 使用场景

### 场景1：全面监控

```bash
python -m crawl.wallstreetcn_runner --monitor --interval 30
```

- 获取所有快讯
- 适合需要完整信息的场景
- 每30秒轮询一次

### 场景2：精准监控（推荐）

```bash
python -m crawl.wallstreetcn_runner --monitor --interval 30 --important
```

- 只获取重要快讯（Score >= 2）
- 过滤94%的普通快讯
- 专注高价值信息

### 场景3：高频监控

```bash
python -m crawl.wallstreetcn_runner --monitor --interval 15 --important
```

- 每15秒轮询一次
- 只关注重要快讯
- 适合需要极速响应的场景

### 场景4：双模式并行

```bash
# 终端1：高频监控重要快讯
python -m crawl.wallstreetcn_runner --monitor --interval 15 --important

# 终端2：低频备份全部快讯
python -m crawl.wallstreetcn_runner --monitor --interval 60
```

- 重要信息实时获取（15秒）
- 全部信息定期备份（60秒）
- 兼顾实时性和完整性

---

## 📁 文件结构

```
articles/wallstreetcn/
├── WSJ_2026-02-10_102604_3052662.json  ← 标准JSON格式
├── WSJ_2026-02-10_094824_3052641.json
├── WSJ_2026-02-10_085731_3052600.json
└── wsj_3052662_2026-02-10_102604.md    ← Markdown格式（可选）
```

---

## 🔍 快速查询

### 查看最新快讯

```bash
# 查看最新的5个JSON文件
ls -lt articles/wallstreetcn/WSJ_*.json | head -5

# 查看最新快讯的标题
ls -t articles/wallstreetcn/WSJ_*.json | head -1 | xargs cat | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'{d[\"publishTime\"]} - {d[\"title\"]}')"
```

### 统计快讯数量

```bash
# 统计总数
ls articles/wallstreetcn/WSJ_*.json | wc -l

# 统计今天的快讯
ls articles/wallstreetcn/WSJ_$(date +%Y-%m-%d)_*.json 2>/dev/null | wc -l
```

### 查找重要快讯

```bash
# 查找所有重要快讯（is_important: true）
grep -l '"is_important": true' articles/wallstreetcn/WSJ_*.json
```

---

## 💡 命令参数速查

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| --monitor | -m | - | 启动实时监控模式 |
| --fetch | -f | - | 单次抓取模式 |
| --channel | -c | global-channel | 频道名称 |
| --interval | -i | 30 | 监控轮询间隔（秒） |
| --limit | -l | 20 | 单次抓取数量 |
| --format | - | json | 保存格式 (json/markdown/both) |
| --important | - | false | 只抓取重要快讯 |
| --min-score | - | 1 | 最低评分过滤 (1/2) |

---

## 📊 数据统计

### 重要性分布（实测数据）

| Score | 类型 | 占比 | 示例 |
|-------|------|------|------|
| 1 | 普通快讯 | ~94% | 常规市场动态 |
| 2 | 重要快讯 | ~6% | 重大市场事件 |

**测试结果**：50条快讯中，3条为重要快讯（过滤率94%）

### 分类统计

| columnName | 说明 | 触发条件 |
|-----------|------|---------|
| 重要快讯 | 重大市场事件 | score >= 2 |
| 全球快讯 | 全球市场动态 | global-channel |
| 外汇市场 | 外汇相关 | forex-channel |
| 美股市场 | 美股相关 | us-stock-channel |
| A股市场 | A股相关 | a-stock-channel |
| 债券市场 | 债券相关 | bond-channel |
| 大宗商品 | 商品相关 | commodity-channel |

---

## 🔧 故障排查

### 问题1：无法获取数据

```bash
# 测试网络连接
curl -I https://api-one-wscn.awtmt.com/apiv1/content/lives

# 降低请求频率
python -m crawl.wallstreetcn_runner --monitor --interval 60
```

### 问题2：文件保存失败

```bash
# 检查目录权限
ls -la articles/wallstreetcn/

# 手动创建目录
mkdir -p articles/wallstreetcn/

# 检查磁盘空间
df -h
```

### 问题3：过滤不生效

```bash
# 确认使用了正确的参数
python -m crawl.wallstreetcn_runner --fetch --limit 50 --min-score 2

# 检查输出中的过滤模式提示
# 应该显示：过滤模式: 重要快讯 (min_score=2)
```

---

## 📚 完整文档

1. **快速开始**: `README_WALLSTREETCN.md`
2. **完整指南**: `docs/WALLSTREETCN_COMPLETE_GUIDE.md`
3. **重要过滤**: `docs/WALLSTREETCN_IMPORTANT_FILTER.md`
4. **JSON格式**: `docs/WALLSTREETCN_JSON_FORMAT.md`
5. **快速参考**: `docs/WALLSTREETCN_QUICK_REFERENCE.md`（本文档）

---

## 🎉 核心特性

✅ **实时监控** - 自动轮询获取最新快讯
✅ **增量抓取** - 智能去重，只获取新内容
✅ **重要过滤** - 支持"只看重要的"功能（过滤94%噪音）
✅ **标准格式** - 兼容隆众资讯JSON格式
✅ **多频道支持** - 全球/外汇/美股/A股等
✅ **已验证可用** - 真实API测试通过

---

## 🚀 推荐配置

### 生产环境推荐

```bash
# 只保存重要快讯的标准JSON格式
python -m crawl.wallstreetcn_runner --monitor --interval 30 --important
```

**优势**：
- 每30秒轮询一次（平衡实时性和请求频率）
- 只获取重要快讯（过滤94%的噪音）
- 自动保存为标准JSON格式（兼容隆众资讯）
- 增量抓取，避免重复

### 测试环境推荐

```bash
# 单次抓取测试
python -m crawl.wallstreetcn_runner --fetch --limit 10 --important
```

---

## 📞 技术支持

- **项目地址**: `/home/yztrade/PycharmProjects/longzhong_tiqu`
- **核心代码**: `crawl/wallstreetcn.py`
- **格式化器**: `crawl/wallstreetcn_formatter.py`
- **命令行工具**: `crawl/wallstreetcn_runner.py`

---

**最后更新**: 2026-02-10
**版本**: v1.0
**状态**: ✅ 已测试可用
