# 华尔街见闻爬虫 - 完全对应隆众资讯格式

## ✅ 确认：字段完全一致

华尔街见闻的JSON格式现在**完全对应**隆众资讯的cleaned格式！

---

## 📊 格式对比

### 隆众资讯格式

```json
{
  "cleaned_text": "# 周五国际原油价格下跌_28378673\n\n提取失败: 451 Client Error...",
  "date": "2025-02-01",
  "institution": "隆众资讯",
  "title": "周五国际原油价格下跌_28378673",
  "period": "d",
  "category": "相关产品",
  "researchers": [],
  "content_type": "资讯",
  "source_json_path": "/home/yztrade/PycharmProjects/longzhong_tiqu/articles/json/OIL_28378673_28378673.json",
  "content_digest": "bf7ce65b0d6711c62912784faac99914e443f59f",
  "publish_time": "2025-02-01 06:37:04",
  "source_url": "https://www.oilchem.net/25-0201-06-753ba15760523148.html",
  "article_id": "28378673"
}
```

### 华尔街见闻格式（新）

```json
{
  "cleaned_text": "# 快讯_3052664\n\n上海钢联发布数据显示，今日MMLC电池级碳酸锂（早盘）中间价报136800元/吨，较上日16:30价格上涨100元/吨。",
  "date": "2026-02-10",
  "institution": "华尔街见闻",
  "title": "快讯_3052664",
  "period": "d",
  "category": "大宗商品",
  "researchers": [
    "bumblebee"
  ],
  "content_type": "资讯",
  "source_json_path": "",
  "content_digest": "3cf9ac8e18eb1507f816c1ae98130e946096320c",
  "publish_time": "2026-02-10 10:31:00",
  "source_url": "https://wallstreetcn.com/livenews/3052664",
  "article_id": "3052664"
}
```

---

## ✅ 字段对应表

| 字段名 | 隆众资讯 | 华尔街见闻 | 说明 |
|--------|---------|-----------|------|
| `cleaned_text` | ✅ | ✅ | Markdown格式的完整内容 |
| `date` | ✅ | ✅ | 日期（YYYY-MM-DD） |
| `institution` | ✅ | ✅ | 机构名称 |
| `title` | ✅ | ✅ | 标题 |
| `period` | ✅ | ✅ | 周期（d=日度） |
| `category` | ✅ | ✅ | 分类 |
| `researchers` | ✅ | ✅ | 研究员列表 |
| `content_type` | ✅ | ✅ | 内容类型 |
| `source_json_path` | ✅ | ✅ | 源JSON路径 |
| `content_digest` | ✅ | ✅ | 内容摘要（SHA1） |
| `publish_time` | ✅ | ✅ | 发布时间 |
| `source_url` | ✅ | ✅ | 原文链接 |
| `article_id` | ✅ | ✅ | 文章ID |

**结论**: 13个字段完全一致！✅

---

## 📁 文件命名对比

### 隆众资讯

```
OIL_28378673_28378673.json
```

格式：`OIL_<ID>_<ID>.json`

### 华尔街见闻

```
WSJ_20260210_3052664.json
```

格式：`WSJ_<日期>_<ID>.json`

**说明**：
- `WSJ` = WallStreetCN（华尔街见闻）
- `20260210` = 日期（YYYYMMDD）
- `3052664` = 文章ID

---

## 🚀 立即使用

### 推荐命令

```bash
# 监控商品频道，自动保存为隆众资讯格式
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel
```

**输出文件**：
```
articles/wallstreetcn/
├── WSJ_20260210_3052664.json  ← 完全对应隆众资讯格式
├── WSJ_20260210_3052640.json
└── WSJ_20260210_3052559.json
```

---

## 💻 统一处理代码

现在可以用**完全相同的代码**处理两种数据源：

```python
import json
from pathlib import Path

def process_news(json_file):
    """统一处理隆众资讯和华尔街见闻的JSON"""
    with open(json_file) as f:
        data = json.load(f)

    # 使用完全相同的字段
    print(f"[{data['institution']}] {data['title']}")
    print(f"  日期: {data['date']}")
    print(f"  时间: {data['publish_time']}")
    print(f"  分类: {data['category']}")
    print(f"  类型: {data['content_type']}")
    print(f"  研究员: {', '.join(data['researchers']) if data['researchers'] else '无'}")
    print(f"  链接: {data['source_url']}")
    print(f"  摘要: {data['content_digest'][:16]}...")
    print()

# 处理隆众资讯
print("=== 隆众资讯 ===")
for json_file in Path('output/report/cleaned').glob('*.json'):
    process_news(json_file)

# 处理华尔街见闻（使用完全相同的代码！）
print("=== 华尔街见闻 ===")
for json_file in Path('articles/wallstreetcn').glob('WSJ_*.json'):
    process_news(json_file)
```

---

## 📊 批量分析示例

```python
import json
import pandas as pd
from pathlib import Path

# 读取所有JSON文件（隆众 + 华尔街）
all_data = []

# 读取隆众资讯
for json_file in Path('output/report/cleaned').glob('*.json'):
    with open(json_file) as f:
        data = json.load(f)
        all_data.append(data)

# 读取华尔街见闻
for json_file in Path('articles/wallstreetcn').glob('WSJ_*.json'):
    with open(json_file) as f:
        data = json.load(f)
        all_data.append(data)

# 转换为DataFrame
df = pd.DataFrame(all_data)

# 统一分析
print(f"总计: {len(df)} 条资讯")
print(f"\n按机构统计:")
print(df['institution'].value_counts())
print(f"\n按分类统计:")
print(df['category'].value_counts())
print(f"\n按类型统计:")
print(df['content_type'].value_counts())

# 导出为CSV
df.to_csv('all_news.csv', index=False, encoding='utf-8-sig')
print(f"\n已导出到 all_news.csv")
```

---

## 🎯 字段说明

### cleaned_text
- **格式**: Markdown格式
- **内容**: `# 标题\n\n正文内容`
- **用途**: 完整的文本内容，便于阅读和处理

### date
- **格式**: `YYYY-MM-DD`
- **示例**: `2026-02-10`
- **用途**: 日期索引和筛选

### institution
- **隆众**: `隆众资讯`
- **华尔街**: `华尔街见闻`
- **用途**: 数据源标识

### title
- **格式**: 纯文本标题
- **示例**: `快讯_3052664`
- **用途**: 快速识别内容

### period
- **固定值**: `d`（日度数据）
- **用途**: 数据周期标识

### category
- **隆众示例**: `相关产品`、`数据简报`
- **华尔街示例**: `大宗商品`、`全球快讯`、`重要快讯`
- **用途**: 内容分类

### researchers
- **格式**: 字符串数组
- **示例**: `["石惠"]` 或 `[]`
- **用途**: 作者/研究员信息

### content_type
- **隆众**: `资讯`
- **华尔街**: `资讯` 或 `快讯`（Score >= 2）
- **用途**: 内容类型标识

### source_json_path
- **隆众**: 源JSON文件的完整路径
- **华尔街**: 空字符串（无源JSON）
- **用途**: 追溯数据来源

### content_digest
- **格式**: SHA1哈希值（40字符）
- **示例**: `3cf9ac8e18eb1507f816c1ae98130e946096320c`
- **用途**: 内容去重和完整性校验

### publish_time
- **格式**: `YYYY-MM-DD HH:MM:SS`
- **示例**: `2026-02-10 10:31:00`
- **用途**: 精确时间戳

### source_url
- **格式**: 完整URL
- **用途**: 原文链接

### article_id
- **格式**: 字符串
- **用途**: 唯一标识符

---

## 🔍 内容去重

使用 `content_digest` 进行去重：

```python
import json
from pathlib import Path

# 收集所有内容摘要
seen_digests = set()
unique_news = []
duplicate_count = 0

# 处理所有JSON文件
all_files = list(Path('output/report/cleaned').glob('*.json')) + \
            list(Path('articles/wallstreetcn').glob('WSJ_*.json'))

for json_file in all_files:
    with open(json_file) as f:
        data = json.load(f)
        digest = data['content_digest']

        if digest not in seen_digests:
            seen_digests.add(digest)
            unique_news.append(data)
        else:
            duplicate_count += 1

print(f"总文件数: {len(all_files)}")
print(f"唯一内容: {len(unique_news)}")
print(f"重复内容: {duplicate_count}")
```

---

## 📈 时间序列分析

```python
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

# 读取所有数据
all_data = []
for json_file in Path('articles/wallstreetcn').glob('WSJ_*.json'):
    with open(json_file) as f:
        data = json.load(f)
        all_data.append(data)

# 转换为DataFrame
df = pd.DataFrame(all_data)

# 转换时间
df['publish_time'] = pd.to_datetime(df['publish_time'])
df['date'] = pd.to_datetime(df['date'])

# 按日期统计
daily_count = df.groupby('date').size()
print("每日快讯数量:")
print(daily_count)

# 按小时统计
df['hour'] = df['publish_time'].dt.hour
hourly_count = df.groupby('hour').size()
print("\n每小时快讯数量:")
print(hourly_count)

# 按分类统计
category_count = df.groupby('category').size()
print("\n按分类统计:")
print(category_count)
```

---

## 🎉 总结

### ✅ 已完成

1. **字段完全对应** - 13个字段与隆众资讯完全一致
2. **格式统一** - 可以用相同代码处理两种数据源
3. **自动转换** - 爬虫自动转换为隆众格式
4. **文件命名** - `WSJ_<日期>_<ID>.json`

### 🚀 立即使用

```bash
# 监控商品频道，自动保存为隆众资讯格式
python -m crawl.wallstreetcn_runner --monitor --interval 30 --channel commodity-channel
```

### 💡 核心优势

✅ **完全兼容** - 字段一模一样，无需修改处理代码
✅ **统一分析** - 可以合并分析两种数据源
✅ **自动去重** - 使用 content_digest 去重
✅ **易于集成** - 直接替换或补充隆众数据

---

**最后更新**: 2026-02-10
**格式版本**: v2.0（完全对应隆众资讯）
**状态**: ✅ 已验证，可直接使用
