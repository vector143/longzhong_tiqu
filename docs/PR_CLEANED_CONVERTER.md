# PR 计划：资讯 JSON 自动转换为 Cleaned 格式

## 1. 需求概述

将爬虫生成的资讯 JSON 自动转换为 Finreport cleaned 标准格式，支持：
- 爬取完成后自动转换
- 与现有 Finreport 流程无缝集成
- 可配置的转换行为

---

## 2. 技术方案

### 2.1 集成方式选择

| 方案 | 实现位置 | 优点 | 缺点 | 推荐度 |
|------|----------|------|------|--------|
| **A (推荐)** | worker.py 调用新模块 | 单篇处理、异常隔离、元信息完整 | 增加 worker 依赖 | ⭐⭐⭐ |
| B | format_converter.py 扩展 | 复用现有逻辑 | 模块职责膨胀 | ⭐⭐ |
| C | 独立后处理任务 | 离线补跑方便 | 非实时、需二次扫描 | ⭐ |

**选择方案 A**：在 `crawl/worker.py` 中集成，调用新增的 `convert/cleaned_converter.py` 模块。

### 2.2 转换时机

- **默认**：实时转换（每篇文章处理后立即生成 cleaned）
- **备选**：提供 CLI 命令支持批量补跑

### 2.3 数据流图

```
                            当前流程
                            ========
爬取HTML → html_content → save_as_json() → articles/json/*.json
                        ↘ save_as_html_async()
                        ↘ html_to_word_async()

                            新增流程
                            ========
爬取HTML → html_content → save_as_json() → articles/json/*.json
                                    ↓
                           CleanedConverter.convert()
                                    ↓
                        output/report/cleaned/*.json (cleaned格式)
```

---

## 3. 格式映射

### 3.1 输入格式（当前 JSON）

```json
{
  "articleId": "33094861",
  "title": "[原油]：聚焦石化行业稳增长方向",
  "publishTime": "2025-12-19 11:22:45",
  "url": "https://www.oilchem.net/...",
  "columnName": "相关产品-原油",
  "source": "隆众资讯",
  "content": "导语：国家工信部今年发布的...",
  "tables": [[["列1", "列2"], ["数据1", "数据2"]]]
}
```

### 3.2 输出格式（cleaned JSON）

```json
{
  "cleaned_text": "# 聚焦石化行业稳增长方向\n\n导语：国家工信部今年发布的...\n\n## 表格 1\n| 列1 | 列2 |\n| --- | --- |\n| 数据1 | 数据2 |",
  "date": "2025-12-19",
  "institution": "隆众资讯",
  "title": "聚焦石化行业稳增长方向",
  "period": "d",
  "category": "原油",
  "researchers": [],
  "content_type": "资讯",
  "source_json_path": "/absolute/path/to/articles/json/xxx.json",
  "content_digest": "3b7901a5c1d5e8f2...(40字符SHA1)",
  "publish_time": "2025-12-19 11:22:45",
  "source_url": "https://www.oilchem.net/...",
  "article_id": "33094861",
  "tables": [[["列1", "列2"], ["数据1", "数据2"]]]
}
```

### 3.3 字段映射规则

| cleaned 字段 | 来源 | 转换规则 |
|--------------|------|----------|
| `cleaned_text` | title + content + tables | Markdown 格式拼接 |
| `date` | publishTime | 解析为 YYYY-MM-DD |
| `institution` | source | 直接使用 |
| `title` | title | 去除 `[xxx]：` 前缀 |
| `period` | 固定值 | "d"（日报） |
| `category` | columnName | 提取最后一个 `-` 后的内容 |
| `researchers` | 固定值 | []（资讯无作者） |
| `content_type` | 固定值 | "资讯" |
| `source_json_path` | 运行时 | JSON 文件绝对路径 |
| `content_digest` | cleaned_text | SHA1 前 4000 字符 |
| `publish_time` | publishTime | 原样保留（秒级） |
| `source_url` | url | 原样保留 |
| `article_id` | articleId | 原样保留 |
| `tables` | tables | 原样保留 |

---

## 4. 文件变更清单

### 4.1 新增文件

| 文件路径 | 说明 |
|----------|------|
| `convert/cleaned_converter.py` | Cleaned 格式转换器核心模块 |

### 4.2 修改文件

| 文件路径 | 修改内容 |
|----------|----------|
| `config/settings.py` | 新增 CleanedConfig 配置类 |
| `crawl/worker.py` | 集成 cleaned 转换调用 |
| `convert/__init__.py` | 导出 CleanedConverter |

---

## 5. 详细实现计划

### Phase 1: 配置扩展

**文件**: `config/settings.py`

新增配置类：
```python
@dataclass
class CleanedConfig:
    """Cleaned 输出配置"""
    enable: bool = True                              # 是否启用
    output_dir: str = "output/report/cleaned"        # 输出目录
    on_duplicate: str = "skip"                       # skip/overwrite/new_version
    filename_max_length: int = 180                   # 文件名最大长度
    digest_max_chars: int = 4000                     # 摘要计算字符数
    period_default: str = "d"                        # 默认周期
    content_type_default: str = "资讯"               # 默认内容类型
```

环境变量支持：
```
CLEANED_ENABLE=true
CLEANED_OUTPUT_DIR=output/report/cleaned
CLEANED_ON_DUPLICATE=skip
```

### Phase 2: 转换器实现

**文件**: `convert/cleaned_converter.py`

```
CleanedConverter 类:
├── __init__(output_dir, on_duplicate, ...)
│
├── convert(article_dict, source_path) -> ConversionResult
│   ├── 解析发布时间
│   ├── 提取元数据（机构、分类、标题）
│   ├── 构建 cleaned_text（Markdown 格式）
│   ├── 计算 content_digest（SHA1）
│   ├── 生成文件名
│   ├── 处理重复
│   └── 写入文件
│
├── convert_batch(articles) -> dict[str, int]
│   └── 批量转换，返回统计
│
├── _parse_publish_time(time_str) -> (date, publish_time)
├── _extract_institution(article) -> str
├── _extract_category(article) -> str
├── _clean_title(title) -> str
├── _build_cleaned_text(article, title, content) -> str
├── _table_to_markdown(table) -> str
├── _compute_content_digest(text) -> str
├── _build_filename(date, institution, title) -> str
├── _sanitize_filename(name) -> str
└── _get_versioned_path(path) -> Path
```

**ConversionResult 数据类**：
```python
@dataclass
class ConversionResult:
    success: bool
    cleaned_path: Path | None = None
    error: str | None = None
    skipped_reason: str | None = None
```

### Phase 3: Worker 集成

**文件**: `crawl/worker.py`

在 JSON 保存成功后调用转换：

```python
# JSON格式
if 'json' in output_formats:
    json_result = converter.save_as_json(...)
    if json_result:
        # 新增：转换为 cleaned 格式
        if settings.cleaned.enable:
            cleaned_result = cleaned_converter.convert(
                article={
                    'articleId': article.get('articleId'),
                    'title': article['title'],
                    'publishTime': article.get('publishTime'),
                    'url': article.get('url'),
                    'columnName': article.get('columnName'),
                    'source': '隆众资讯',
                    'content': content_text,  # 从 html_to_text_and_tables 获取
                    'tables': tables,
                },
                source_path=json_result.get('local_path')
            )
            if cleaned_result.success:
                local_files['cleaned'] = str(cleaned_result.cleaned_path)
```

### Phase 4: 导出更新

**文件**: `convert/__init__.py`

```python
from .cleaned_converter import CleanedConverter, ConversionResult

__all__ = [
    "AsyncFormatConverter",
    "CleanedConverter",
    "ConversionResult",
    ...
]
```

---

## 6. 配置示例

### 6.1 默认配置（启用转换）

```python
# config/settings.py 默认值
cleaned = CleanedConfig()
```

### 6.2 禁用转换

```bash
export CLEANED_ENABLE=false
```

### 6.3 自定义输出目录

```bash
export CLEANED_OUTPUT_DIR=/path/to/custom/cleaned
```

---

## 7. 目录结构

```
longzhong_tiqu/
├── config/
│   └── settings.py              # 新增 CleanedConfig
├── convert/
│   ├── __init__.py              # 更新导出
│   ├── format_converter.py      # 不变
│   ├── html_utils.py            # 不变
│   ├── word_processor.py        # 不变
│   └── cleaned_converter.py     # 新增
├── crawl/
│   ├── pipeline.py              # 不变
│   ├── requests.py              # 不变
│   └── worker.py                # 修改：集成 cleaned 转换
├── articles/
│   ├── json/                    # 原始 JSON（不变）
│   ├── html/                    # HTML 文件（不变）
│   └── word/                    # Word 文件（不变）
└── output/
    └── report/
        └── cleaned/             # 新增：cleaned 格式输出
            └── 2025-12-19_隆众资讯_xxx.json
```

---

## 8. 机构与分类映射

### 8.1 机构映射

```python
INSTITUTION_MAP = {
    "oilchem.net": "隆众资讯",
    "mysteel.com": "我的钢铁",
    "coalchem.com": "煤化工网",
    "sci99.com": "卓创资讯",
}
```

### 8.2 分类提取规则

1. **从 columnName 提取**：
   - `"相关产品-原油"` → `"原油"`
   - `"行业资讯-化工"` → `"化工"`

2. **从标题提取**（备选）：
   - `"[原油]：xxx"` → `"原油"`
   - `"[LNG]：xxx"` → `"LNG"`

3. **默认值**：`"综合"`

### 8.3 标题清理规则

- 去除 `[xxx]：` 前缀
- 去除 `[xxx]:` 前缀（英文冒号）
- 去除前后空白

```python
# 示例
"[原油]：聚焦石化行业稳增长方向" → "聚焦石化行业稳增长方向"
"[LNG]: 市场分析" → "市场分析"
```

---

## 9. 文件命名规则

### 9.1 格式

```
{date}_{institution}_{title}.json
```

### 9.2 重要约束：防止文件名碰撞

由于同一天可能存在多篇标题相似的文章，**建议在爬取阶段将 `article_id` 加入标题**，使其成为标题的一部分。这样可以：

1. 避免 cleaned 文件名碰撞
2. 保持文件可追溯性
3. 无需修改 cleaned 转换逻辑

**示例**：
```python
# 爬取时修改标题
article['title'] = f"{article['title']}_{article['articleId']}"
# 或
article['title'] = f"[{article['articleId']}] {article['title']}"
```

**生成的 cleaned 文件名**：
```
2025-12-19_隆众资讯_聚焦石化行业稳增长方向_33094861.json
```

### 9.3 清理规则

```python
# 非法字符替换为空格
illegal_chars = '/\\:*?"<>|\n\r\t'

# 合并连续空格
re.sub(r'\s+', ' ', name)

# 截断到 max_length
name[:max_length]
```

### 9.4 示例

```
2025-12-19_隆众资讯_聚焦石化行业稳增长方向炼油结构优化及减油增化双擎驱动.json
```

---

## 10. 错误处理

### 10.1 转换失败

- 记录错误日志
- 不影响后续文章处理
- 返回 `ConversionResult(success=False, error=...)`

### 10.2 重复文件

根据 `on_duplicate` 配置：
- `skip`：跳过，返回现有路径
- `overwrite`：覆盖现有文件
- `new_version`：生成带版本号的新文件

### 10.3 缺少必要字段

- `publishTime`：报错并跳过
- `title`：报错并跳过
- `content`：报错并跳过
- `columnName`：使用默认分类

---

## 11. 测试计划

### 11.1 单元测试

```python
def test_parse_publish_time():
    converter = CleanedConverter()
    assert converter._parse_publish_time("2025-12-19 11:22:45") == ("2025-12-19", "2025-12-19 11:22:45")
    assert converter._parse_publish_time("2025-12-19") == ("2025-12-19", None)
    assert converter._parse_publish_time("2025/12/19 11:22:45") == ("2025-12-19", "2025-12-19 11:22:45")

def test_extract_category():
    converter = CleanedConverter()
    assert converter._extract_category({"columnName": "相关产品-原油"}) == "原油"
    assert converter._extract_category({"title": "[LNG]：市场分析"}) == "LNG"
    assert converter._extract_category({}) == "综合"

def test_clean_title():
    converter = CleanedConverter()
    assert converter._clean_title("[原油]：聚焦石化行业") == "聚焦石化行业"
    assert converter._clean_title("[LNG]: 市场分析") == "市场分析"

def test_convert_article():
    converter = CleanedConverter(output_dir="/tmp/test_cleaned")
    article = {
        "articleId": "test001",
        "title": "[原油]：测试标题",
        "publishTime": "2025-12-19 11:22:45",
        "url": "https://www.oilchem.net/test",
        "columnName": "相关产品-原油",
        "source": "隆众资讯",
        "content": "测试正文内容",
        "tables": [],
    }
    result = converter.convert(article)
    assert result.success
    assert result.cleaned_path.exists()
```

### 11.2 集成测试

```bash
# 启用 cleaned 转换运行爬虫
python main.py --keyword 原油 --pages 1

# 检查输出目录
ls -la output/report/cleaned/

# 验证 JSON 格式
python -c "import json; print(json.load(open('output/report/cleaned/2025-12-19_xxx.json')))"
```

### 11.3 验收标准

- [ ] 爬取完成后自动生成 cleaned 文件
- [ ] cleaned 文件格式符合 Finreport 标准
- [ ] 文件命名正确
- [ ] 配置开关有效
- [ ] 错误不影响主流程

---

## 12. Commit 计划

```
1. feat(config): add CleanedConfig for cleaned output settings
2. feat(convert): add CleanedConverter for article to cleaned format conversion
3. feat(worker): integrate cleaned conversion after JSON save
4. test: add unit tests for CleanedConverter
5. docs: update README with cleaned output configuration
```

---

## 13. 实现顺序

```
Step 1: config/settings.py - 添加 CleanedConfig
    ↓
Step 2: convert/cleaned_converter.py - 实现转换器
    ↓
Step 3: convert/__init__.py - 更新导出
    ↓
Step 4: crawl/worker.py - 集成转换调用
    ↓
Step 5: 测试验证
    ↓
Step 6: 文档更新
```

---

## 14. 风险与应对

| 风险 | 应对措施 |
|------|----------|
| 文件名过长导致保存失败 | 截断到 180 字符 |
| 时间格式解析失败 | 支持多种格式，失败时跳过 |
| 分类提取不准确 | 提供默认值"综合" |
| 转换失败影响爬取 | 异常隔离，不影响主流程 |
| 磁盘空间不足 | 复用现有磁盘检查逻辑 |
| 文件名碰撞（同日同标题） | 爬取阶段将 article_id 加入标题 |
| 多线程并发写入竞态 | 通过唯一 article_id 避免 |

---

## 15. 后续扩展

1. **CLI 补跑命令**：批量转换已有 JSON 文件
2. **增量去重**：基于 content_digest 跳过重复内容
3. **多来源支持**：扩展机构映射表
4. **数据库记录**：记录转换状态到 SQLite
