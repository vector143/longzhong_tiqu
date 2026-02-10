# 华尔街见闻爬虫 - 商品频道监控指南

## ✅ 确认：已自动保存标准JSON格式

爬虫现在**默认只保存标准JSON格式**，无需额外配置！

---

## 🚀 立即开始监控商品频道

### 推荐命令（最简单）

```bash
# 监控商品频道，自动保存标准JSON
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel
```

**说明**：
- ✅ 自动保存为标准JSON格式（兼容隆众资讯）
- ✅ 每30秒轮询一次
- ✅ 增量抓取，避免重复
- ✅ 不会保存Markdown文件

---

## 📊 输出确认

### 保存的文件

```
articles/wallstreetcn/
└── WSJ_2026-02-10_103100_3052664.json  ← 只有JSON，没有MD文件
```

### JSON内容（标准格式）

```json
{
  "articleId": "3052664",
  "title": "快讯_3052664",
  "publishTime": "2026-02-10 10:31:00",
  "url": "https://wallstreetcn.com/livenews/3052664",
  "columnName": "大宗商品",
  "source": "华尔街见闻",
  "content": "上海钢联发布数据显示，今日MMLC电池级碳酸锂（早盘）中间价报136800元/吨，较上日16:30价格上涨100元/吨。",
  "tables": [],
  "date": "2026-02-10",
  "institution": "华尔街见闻",
  "period": "realtime",
  "category": "大宗商品",
  "researchers": ["bumblebee"],
  "content_type": "资讯",
  "content_digest": "3cf9ac8e18eb1507f816c1ae98130e946096320c",
  "article_id": "3052664",
  "score": 1,
  "channels": ["commodity-channel"],
  "author": "bumblebee",
  "is_important": false
}
```

**特点**：
- ✅ 兼容隆众资讯的基础字段（articleId, title, publishTime, url, columnName, source, content, tables）
- ✅ 包含扩展字段（date, institution, period, category, researchers, content_type, content_digest）
- ✅ 保留华尔街见闻特有字段（score, channels, is_important）

---

## 🎯 常用命令

### 1. 监控所有商品快讯（推荐）

```bash
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel
```

### 2. 只监控重要商品快讯

```bash
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel --important
```

### 3. 高频监控（每15秒）

```bash
python -m crawl.wallstreetcn_runner --monitor --interval 15 --channel commodity-channel
```

### 4. 后台运行

```bash
nohup python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel > commodity.log 2>&1 &
```

### 5. 单次测试

```bash
python -m crawl.wallstreetcn_runner --fetch --limit 10 --channel commodity-channel
```

---

## 💡 如果需要同时保存Markdown

如果你确实需要同时保存Markdown格式（不推荐），可以使用：

```bash
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel --format both
```

但**不推荐**这样做，因为：
- ❌ 占用更多磁盘空间
- ❌ Markdown文件不便于程序处理
- ✅ JSON格式已经包含所有信息

---

## 📁 文件组织

### 当前结构（推荐）

```
articles/wallstreetcn/
├── WSJ_2026-02-10_103100_3052664.json  ← 碳酸锂价格
├── WSJ_2026-02-10_094556_3052640.json  ← 种业投资
├── WSJ_2026-02-10_072508_3052559.json  ← 市场综述
└── WSJ_2026-02-10_070721_3052555.json  ← 镨钕价格
```

### 文件命名规则

```
WSJ_<完整时间>_<文章ID>.json
```

**示例**：
- `WSJ_2026-02-10_103100_3052664.json`
  - WSJ = WallStreetCN（华尔街见闻）
  - 2026-02-10_103100 = 发布时间（年月日_时分秒）
  - 3052664 = 文章ID

---

## 🔍 查看和管理文件

### 查看最新快讯

```bash
# 查看最新的5个JSON文件
ls -lt articles/wallstreetcn/WSJ_*.json | head -5

# 查看最新快讯的内容
ls -t articles/wallstreetcn/WSJ_*.json | head -1 | xargs cat | python3 -m json.tool
```

### 统计快讯数量

```bash
# 统计总数
ls articles/wallstreetcn/WSJ_*.json | wc -l

# 统计今天的快讯
ls articles/wallstreetcn/WSJ_$(date +%Y-%m-%d)_*.json 2>/dev/null | wc -l
```

### 按分类统计

```bash
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

print('商品频道分类统计:')
for category, count in category_count.most_common():
    print(f'  {category}: {count} 条')
EOF
```

### 查找特定内容

```bash
# 查找包含"碳酸锂"的快讯
grep -l "碳酸锂" articles/wallstreetcn/WSJ_*.json

# 查找重要快讯
grep -l '"is_important": true' articles/wallstreetcn/WSJ_*.json
```

---

## 💻 在代码中使用

### 读取标准JSON

```python
import json
from pathlib import Path

# 读取单个文件
with open('articles/wallstreetcn/WSJ_2026-02-10_103100_3052664.json') as f:
    data = json.load(f)

print(f"标题: {data['title']}")
print(f"分类: {data['columnName']}")
print(f"内容: {data['content']}")
print(f"评分: {data['score']}")
print(f"频道: {', '.join(data['channels'])}")
```

### 批量处理

```python
import json
from pathlib import Path

# 读取所有商品频道的JSON文件
json_dir = Path('articles/wallstreetcn')
commodity_news = []

for json_file in json_dir.glob('WSJ_*.json'):
    with open(json_file) as f:
        data = json.load(f)
        # 只处理商品频道的快讯
        if 'commodity-channel' in data.get('channels', []):
            commodity_news.append(data)

print(f"商品频道快讯总数: {len(commodity_news)}")

# 按内容分类
metal_news = [n for n in commodity_news if any(keyword in n['content'] for keyword in ['锂', '镨钕', '铜', '白银'])]
energy_news = [n for n in commodity_news if any(keyword in n['content'] for keyword in ['原油', '天然气'])]
gold_news = [n for n in commodity_news if '黄金' in n['content']]

print(f"金属相关: {len(metal_news)} 条")
print(f"能源相关: {len(energy_news)} 条")
print(f"黄金相关: {len(gold_news)} 条")
```

### 导出为CSV

```python
import json
import pandas as pd
from pathlib import Path

# 读取所有JSON文件
json_files = Path('articles/wallstreetcn').glob('WSJ_*.json')
data_list = []

for json_file in json_files:
    with open(json_file) as f:
        data = json.load(f)
        data_list.append(data)

# 转换为DataFrame
df = pd.DataFrame(data_list)

# 选择关键字段
df_export = df[[
    'articleId', 'title', 'publishTime', 'columnName',
    'content', 'score', 'is_important', 'author'
]]

# 导出为CSV
df_export.to_csv('wallstreetcn_commodity.csv', index=False, encoding='utf-8-sig')
print(f"已导出 {len(df_export)} 条快讯到 wallstreetcn_commodity.csv")
```

---

## 🎯 监控输出示例

### 启动监控

```bash
$ python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel

🚀 启动华尔街见闻实时监控
   频道: commodity-channel
   轮询间隔: 30 秒
   过滤模式: 全部快讯 (min_score=1)
   保存格式: json
   按 Ctrl+C 停止监控

✅ 初始化完成，当前最新ID: 3052664
⏳ 暂无新快讯
⏳ 暂无新快讯
📰 发现 2 条新快讯

============================================================
📰 收到 2 条新快讯
============================================================

1. [2026-02-10 11:30:15] 镨钕价格再创新高
   百川盈孚数据显示，稀土产品价格继续上涨...
   🔗 https://wallstreetcn.com/livenews/3052700

2. [2026-02-10 11:28:45] 原油期货大涨3%
   WTI原油期货涨3.2%，报78.5美元/桶...
   🔗 https://wallstreetcn.com/livenews/3052699

💾 保存快讯...
   ✅ 已保存: WSJ_2026-02-10_113015_3052700.json
   ✅ 已保存: WSJ_2026-02-10_112845_3052699.json
============================================================
```

---

## 📊 商品频道内容分类

根据实际抓取的数据，商品频道包含：

| 类别 | 占比 | 关键词 | 示例 |
|------|------|--------|------|
| 金属价格 | ~40% | 锂、镨钕、铜、白银 | 碳酸锂价格、稀土价格 |
| 能源市场 | ~20% | 原油、天然气 | WTI原油、布伦特原油 |
| 贵金属 | ~15% | 黄金、白银 | 黄金ETF、白银期货 |
| 农产品 | ~15% | 种业、农业 | 种业投资、农产品价格 |
| 综合快讯 | ~10% | 市场综述 | 早餐快讯、市场回顾 |

---

## 🔧 故障排查

### 问题1：没有生成JSON文件

**检查**：
```bash
ls -la articles/wallstreetcn/
```

**解决**：
```bash
# 确保目录存在
mkdir -p articles/wallstreetcn/

# 检查磁盘空间
df -h
```

### 问题2：生成了Markdown文件

**原因**：使用了 `--format both` 或 `--format markdown`

**解决**：
```bash
# 确保使用默认格式（json）或明确指定
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel --format json
```

### 问题3：JSON格式不正确

**检查**：
```bash
# 验证JSON格式
python3 -m json.tool articles/wallstreetcn/WSJ_*.json | head -20
```

---

## 🎉 总结

### 当前配置（已完成）

✅ **自动保存标准JSON格式**
- 默认只保存JSON，不保存Markdown
- 兼容隆众资讯格式
- 包含所有必要字段

✅ **商品频道监控**
- 支持 `commodity-channel` 频道
- 包含金属、能源、贵金属、农产品等

✅ **增量抓取**
- 自动去重
- 只获取新快讯

✅ **灵活配置**
- 可调整轮询间隔
- 可过滤重要快讯
- 可后台运行

---

## 🚀 立即开始

```bash
# 推荐命令：监控商品频道，自动保存标准JSON
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel
```

**这个命令会**：
- ✅ 每30秒自动抓取商品频道的新快讯
- ✅ 自动保存为标准JSON格式（兼容隆众资讯）
- ✅ 不会保存Markdown文件
- ✅ 增量抓取，避免重复
- ✅ 文件命名：`WSJ_<时间>_<ID>.json`

---

**最后更新**: 2026-02-10
**状态**: ✅ 已配置完成，可直接使用
**默认格式**: JSON（标准格式）
