# 华尔街见闻爬虫 - 标准JSON格式说明

## 📋 格式说明

现在华尔街见闻爬虫默认保存为**标准JSON格式**，参考隆众资讯的数据结构，便于统一处理和分析。

---

## 🎯 标准JSON格式

### 基础字段（兼容隆众资讯）

```json
{
  "articleId": "3052662",           // 文章ID
  "title": "快讯_3052662",          // 标题
  "publishTime": "2026-02-10 10:26:04",  // 发布时间
  "url": "https://wallstreetcn.com/livenews/3052662",  // 原文链接
  "columnName": "重要快讯",          // 栏目/分类
  "source": "华尔街见闻",            // 来源
  "content": "传媒板块涨势扩大...",  // 正文内容
  "tables": []                       // 表格数据（快讯通常为空）
}
```

### 扩展字段（参考cleaned格式）

```json
{
  "date": "2026-02-10",              // 日期
  "institution": "华尔街见闻",       // 机构名称
  "period": "realtime",              // 周期（实时）
  "category": "重要快讯",            // 分类
  "researchers": ["A股团队"],        // 作者/研究员
  "content_type": "快讯",            // 内容类型
  "content_digest": "3fb13f8a...",   // 内容摘要（SHA1，用于去重）
  "article_id": "3052662"            // 文章ID（冗余字段）
}
```

### 华尔街见闻特有字段

```json
{
  "score": 2,                        // 重要性评分（1=普通, 2=重要）
  "channels": ["global-channel"],    // 频道列表
  "author": "A股团队",               // 作者
  "is_important": true               // 是否重要快讯
}
```

---

## 📊 完整示例

### 示例1：重要快讯（Score=2）

```json
{
  "articleId": "3052662",
  "title": "快讯_3052662",
  "publishTime": "2026-02-10 10:26:04",
  "url": "https://wallstreetcn.com/livenews/3052662",
  "columnName": "重要快讯",
  "source": "华尔街见闻",
  "content": "传媒板块涨势扩大，读客文化冲击20cm涨停，捷成股份、荣信文化、风语筑、人民网、掌阅科技等十余股封涨停板。",
  "tables": [],
  "date": "2026-02-10",
  "institution": "华尔街见闻",
  "period": "realtime",
  "category": "重要快讯",
  "researchers": ["A股团队"],
  "content_type": "快讯",
  "content_digest": "3fb13f8a3f2823209673977ad370ce9ebbe282dd",
  "article_id": "3052662",
  "score": 2,
  "channels": ["global-channel"],
  "author": "A股团队",
  "is_important": true
}
```

### 示例2：普通快讯（Score=1）

```json
{
  "articleId": "3052668",
  "title": "快讯_3052668",
  "publishTime": "2026-02-10 10:34:00",
  "url": "https://wallstreetcn.com/livenews/3052668",
  "columnName": "债券市场",
  "source": "华尔街见闻",
  "content": "国开行发行2年期债券，规模60亿元...",
  "tables": [],
  "date": "2026-02-10",
  "institution": "华尔街见闻",
  "period": "realtime",
  "category": "债券市场",
  "researchers": [],
  "content_type": "资讯",
  "content_digest": "22462f33ce2253e21f908386640fe673f0fe2977",
  "article_id": "3052668",
  "score": 1,
  "channels": ["bond-channel", "global-channel"],
  "author": "",
  "is_important": false
}
```

---

## 🚀 使用方法

### 1. 默认使用（只保存JSON）

```bash
# 抓取快讯，自动保存为标准JSON格式
python -m crawl.wallstreetcn_runner --fetch --limit 20

# 实时监控，只保存JSON
python -m crawl.wallstreetcn_runner --monitor --interval 30 --important
```

### 2. 同时保存JSON和Markdown

```bash
# 如果需要同时保存Markdown格式
python -m crawl.wallstreetcn_runner --fetch --limit 20 --format both
```

### 3. 只保存Markdown

```bash
# 只保存Markdown格式（不推荐）
python -m crawl.wallstreetcn_runner --fetch --limit 20 --format markdown
```

---

## 📁 文件命名规则

### 标准JSON格式

```
WSJ_<发布时间>_<文章ID>.json
```

**示例**：
- `WSJ_2026-02-10_102604_3052662.json`
- `WSJ_2026-02-10_094824_3052641.json`

**命名规则**：
- 前缀：`WSJ_`（WallStreetCN缩写）
- 时间：`YYYY-MM-DD_HHMMSS`
- ID：文章ID

---

## 🔍 字段说明

### columnName（栏目分类）

根据频道和评分自动分类：

| 条件 | columnName | 说明 |
|------|-----------|------|
| score >= 2 | 重要快讯 | 重要市场事件 |
| global-channel | 全球快讯 | 全球市场动态 |
| forex-channel | 外汇市场 | 外汇相关 |
| us-stock-channel | 美股市场 | 美股相关 |
| a-stock-channel | A股市场 | A股相关 |
| bond-channel | 债券市场 | 债券相关 |
| commodity-channel | 大宗商品 | 商品相关 |

### content_type（内容类型）

| score | content_type | 说明 |
|-------|-------------|------|
| >= 2 | 快讯 | 重要快讯 |
| 1 | 资讯 | 普通资讯 |

### period（周期）

固定为 `realtime`（实时快讯）

### content_digest（内容摘要）

使用 SHA1 算法生成，用于：
- 内容去重
- 变更检测
- 数据完整性校验

---

## 💡 在代码中使用

### 读取标准JSON

```python
import json
from pathlib import Path

# 读取单个文件
with open('articles/wallstreetcn/WSJ_2026-02-10_102604_3052662.json') as f:
    data = json.load(f)

print(f"标题: {data['title']}")
print(f"分类: {data['columnName']}")
print(f"重要性: {'重要' if data['is_important'] else '普通'}")
print(f"内容: {data['content'][:100]}...")
```

### 批量处理

```python
import json
from pathlib import Path

# 读取所有JSON文件
json_dir = Path('articles/wallstreetcn')
all_news = []

for json_file in json_dir.glob('WSJ_*.json'):
    with open(json_file) as f:
        data = json.load(f)
        all_news.append(data)

# 按重要性分类
important_news = [n for n in all_news if n['is_important']]
normal_news = [n for n in all_news if not n['is_important']]

print(f"总计: {len(all_news)} 条")
print(f"重要: {len(important_news)} 条")
print(f"普通: {len(normal_news)} 条")
```

### 按分类统计

```python
from collections import Counter

# 统计各分类数量
categories = [n['columnName'] for n in all_news]
category_count = Counter(categories)

print("分类统计:")
for category, count in category_count.most_common():
    print(f"  {category}: {count} 条")
```

### 内容去重

```python
# 使用 content_digest 去重
seen_digests = set()
unique_news = []

for news in all_news:
    digest = news['content_digest']
    if digest not in seen_digests:
        seen_digests.add(digest)
        unique_news.append(news)

print(f"去重前: {len(all_news)} 条")
print(f"去重后: {len(unique_news)} 条")
```

---

## 🔧 自定义格式化

如果需要自定义格式，可以修改 `crawl/wallstreetcn_formatter.py`：

```python
from crawl.wallstreetcn_formatter import WallStreetCNFormatter

# 创建自定义格式化器
class MyFormatter(WallStreetCNFormatter):
    def format_to_standard(self, item):
        # 调用父类方法
        standard_data = super().format_to_standard(item)

        # 添加自定义字段
        standard_data['custom_field'] = 'custom_value'

        # 修改分类逻辑
        if '涨停' in standard_data['content']:
            standard_data['columnName'] = '涨停快讯'

        return standard_data

# 使用自定义格式化器
formatter = MyFormatter()
formatted_data = formatter.format_to_standard(raw_item)
```

---

## 📊 与隆众资讯格式对比

| 字段 | 隆众资讯 | 华尔街见闻 | 说明 |
|------|---------|-----------|------|
| articleId | ✅ | ✅ | 文章ID |
| title | ✅ | ✅ | 标题 |
| publishTime | ✅ | ✅ | 发布时间 |
| url | ✅ | ✅ | 原文链接 |
| columnName | ✅ | ✅ | 栏目分类 |
| source | ✅ | ✅ | 来源 |
| content | ✅ | ✅ | 正文内容 |
| tables | ✅ | ✅ | 表格数据 |
| date | ✅ | ✅ | 日期 |
| institution | ✅ | ✅ | 机构名称 |
| period | ✅ | ✅ | 周期 |
| category | ✅ | ✅ | 分类 |
| researchers | ✅ | ✅ | 研究员 |
| content_type | ✅ | ✅ | 内容类型 |
| content_digest | ✅ | ✅ | 内容摘要 |
| score | ❌ | ✅ | 重要性评分（华尔街见闻特有） |
| channels | ❌ | ✅ | 频道列表（华尔街见闻特有） |
| is_important | ❌ | ✅ | 是否重要（华尔街见闻特有） |

**兼容性**：✅ 完全兼容隆众资讯的基础字段，可以使用相同的处理逻辑

---

## 🎯 最佳实践

### 1. 只保存重要快讯的JSON

```bash
# 节省存储空间，只保存重要快讯
python -m crawl.wallstreetcn_runner --monitor --interval 30 --important --format json
```

### 2. 定期清理旧文件

```bash
# 删除7天前的JSON文件
find articles/wallstreetcn/ -name "WSJ_*.json" -mtime +7 -delete
```

### 3. 数据分析

```python
import json
import pandas as pd
from pathlib import Path

# 读取所有JSON文件到DataFrame
json_files = Path('articles/wallstreetcn').glob('WSJ_*.json')
data_list = []

for json_file in json_files:
    with open(json_file) as f:
        data = json.load(f)
        data_list.append(data)

df = pd.DataFrame(data_list)

# 分析
print(df['columnName'].value_counts())  # 分类统计
print(df['is_important'].value_counts())  # 重要性统计
print(df.groupby('date').size())  # 按日期统计
```

### 4. 导出为CSV

```python
# 选择关键字段导出
df_export = df[[
    'articleId', 'title', 'publishTime',
    'columnName', 'content', 'score', 'is_important'
]]

df_export.to_csv('wallstreetcn_news.csv', index=False, encoding='utf-8-sig')
```

---

## 📚 相关文档

- **快速开始**: `README_WALLSTREETCN.md`
- **完整指南**: `docs/WALLSTREETCN_COMPLETE_GUIDE.md`
- **重要过滤**: `docs/WALLSTREETCN_IMPORTANT_FILTER.md`
- **格式化器代码**: `crawl/wallstreetcn_formatter.py`

---

## 🎉 总结

华尔街见闻爬虫现在默认保存为**标准JSON格式**：

✅ **兼容隆众资讯** - 使用相同的基础字段结构
✅ **统一处理** - 可以用相同的代码处理两种数据源
✅ **扩展字段** - 保留华尔街见闻的特有信息（score、channels等）
✅ **内容去重** - 使用 content_digest 进行去重
✅ **易于分析** - 标准化格式便于数据分析和可视化

**推荐配置**：
```bash
# 只保存重要快讯的标准JSON格式
python -m crawl.wallstreetcn_runner --monitor --interval 30 --important
```

这样可以：
- 只保存重要快讯（过滤94%噪音）
- 使用标准JSON格式（兼容隆众资讯）
- 节省存储空间
- 便于后续处理和分析

---

**最后更新**: 2026-02-10
**格式版本**: v1.0
**兼容性**: ✅ 兼容隆众资讯JSON格式
