# 隆众资讯爬虫项目 - 重构PR计划

> 生成日期：2025-12-20
> 项目路径：/home/yztrade/PycharmProjects/longzhong_tiqu
> 当前状态：main.py 1920行，需拆分到10+模块
> 文档版本：v1.2（完善测试计划、回滚方案、兼容性策略）

---

## 🎯 重构目标与非目标

### 目标
- main.py 从 1920 行拆分到 ~80 行兼容入口
- 每个模块文件不超过 300 行
- 保持 `from main import XXX` 旧 API 100% 兼容
- 消除重复代码
- 配置外部化

### 非目标（本次不做）
- 不改变任何业务逻辑
- 不修改 API 签名或返回值
- 不添加新功能
- 不升级依赖版本

### 兼容性策略
- **旧入口保留**：`main.py` 作为兼容层永久保留
- **废弃文件**：`convert_to_markdown.py` 转为 shim，显示 DeprecationWarning，保留至少 2 个版本
- **导入路径**：新旧路径均可使用，推荐逐步迁移到新路径

---

## 📋 总览

| PR# | 标题 | 优先级 | 预估改动行数 | 依赖 |
|-----|------|--------|-------------|------|
| PR1 | 创建模块目录，拆分日志和命名系统 | P0 | ~300行 | 无 |
| PR2 | 拆分网络请求函数 | P0 | ~150行 | PR1 |
| PR3 | 拆分客户端模块（Cookies/七牛云） | P0 | ~350行 | PR1 |
| PR4a | 拆分HTML解析工具 | P0 | ~180行 | PR1 |
| PR4b | 拆分格式转换器（Word/JSON处理） | P0 | ~280行 | PR4a |
| PR5 | 拆分爬虫Worker（依赖转换器） | P0 | ~100行 | PR2,PR4b |
| PR6 | 拆分存储和爬取管道模块 | P0 | ~350行 | PR3,PR5 |
| PR7 | main.py瘦身为兼容入口 | P0 | ~80行保留 | PR1-PR6 |
| PR8 | 统一时间格式化工具，消除重复 | P1 | ~80行 | PR7 |
| PR9 | 配置外部化 | P1 | ~100行 | PR7 |

**重要变更说明（v1.2）**：
1. **PR4 拆分为 PR4a + PR4b**：避免单文件超过300行
2. **PR2 调整**：仅包含网络请求，不含 worker（worker 依赖转换器）
3. **PR5 新增**：爬虫 worker 单独提取，解决依赖循环
4. **依赖关系修正**：确保每个 PR 可独立合并测试
5. **新增**：目标/非目标说明、兼容性策略、main.py符号清单、离线测试用例

---

## 📑 main.py 顶层符号清单（完整迁移映射）

确保无遗漏，以下是 main.py 中所有需要迁移的顶层符号：

| 符号名 | 类型 | 行范围 | 迁移目标 | PR |
|--------|------|--------|---------|-----|
| IncrementalUpdateLogger | 类 | 24-152 | core/logging.py | PR1 |
| UploadTask | 类 | 155-168 | clients/qiniu_uploader.py | PR3 |
| AsyncMemoryQiniuUploader | 类 | 171-391 | clients/qiniu_uploader.py | PR3 |
| UniversalNamingSystem | 类 | 395-509 | core/naming.py | PR1 |
| html_table_to_markdown | 函数 | 512-548 | convert/html_utils.py | PR4a |
| html_to_markdown | 函数 | 551-609 | convert/html_utils.py | PR4a |
| html_table_to_data | 函数 | 612-640 | convert/html_utils.py | PR4a |
| html_to_text_and_tables | 函数 | 643-685 | convert/html_utils.py | PR4a |
| AsyncFormatConverter | 类 | 689-1260 | convert/format_converter.py + word_processor.py | PR4b |
| OilChemCookiesManager | 类 | 1265-1360 | clients/cookies.py | PR3 |
| crawl_article_worker_async | 函数 | 1363-1439 | crawl/worker.py | PR5 |
| crawl_articles_async_multithread | 函数 | 1443-1533 | crawl/pipeline.py | PR6 |
| get_article_list | 函数 | 1538-1577 | crawl/requests.py | PR2 |
| _format_timestamp | 函数 | 1579-1582 | utils/time_utils.py | PR1 |
| extract_article_content | 函数 | 1585-1682 | crawl/requests.py | PR2 |
| save_results | 函数 | 1689-1760 | storage/save.py | PR6 |
| extract_from_keyword_async_multithread | 函数 | 1764-1904 | crawl/pipeline.py | PR6 |
| if __name__ == "__main__" | 入口 | 1907-1920 | main.py（保留） | PR7 |

**全局常量/配置（保留在各模块或迁移到 config）**：
- HTTP Headers → crawl/requests.py
- API URLs → crawl/requests.py
- 默认配置值 → config/settings.py (PR9)

---

## PR1: 创建模块目录，拆分日志和命名系统

### 基本信息
- **分支名**: `refactor/pr1-core-modules`
- **优先级**: P0
- **风险等级**: 低
- **预估改动**: ~300行移动

### 变更说明
创建项目模块化的基础目录结构，将核心工具类（日志记录器、命名系统）拆分到独立模块。

### 文件变更清单

#### 新增文件
```
core/__init__.py          # 模块初始化，导出公共API
core/logging.py           # IncrementalUpdateLogger 类
core/naming.py            # UniversalNamingSystem 类
utils/__init__.py         # 工具模块初始化
utils/time_utils.py       # 时间格式化工具函数
```

#### 代码迁移映射
| 源文件 | 源代码行范围 | 目标文件 | 说明 |
|--------|-------------|----------|------|
| main.py | 24-152 | core/logging.py | IncrementalUpdateLogger 类 |
| main.py | 395-509 | core/naming.py | UniversalNamingSystem 类 |
| main.py | 1579-1582 | utils/time_utils.py | _format_timestamp 函数 |

#### core/__init__.py 内容
```python
"""核心模块 - 日志记录和命名系统"""
from .logging import IncrementalUpdateLogger
from .naming import UniversalNamingSystem

__all__ = ['IncrementalUpdateLogger', 'UniversalNamingSystem']
```

#### utils/__init__.py 内容
```python
"""工具模块"""
from .time_utils import format_timestamp

__all__ = ['format_timestamp']
# 注意：format_publish_time 将在 PR8 中添加
```

### 验收标准
- [ ] `from core import IncrementalUpdateLogger` 可正常导入
- [ ] `from core import UniversalNamingSystem` 可正常导入
- [ ] main.py 中原有调用不受影响
- [ ] 无循环导入错误

### 测试计划
```bash
# === 必跑检查（离线）===
# 1. 语法检查
python -m py_compile core/logging.py core/naming.py utils/time_utils.py

# 2. 行数检查
wc -l core/*.py utils/*.py | awk '$1 > 300 {print "❌ 超过300行:", $2; exit 1}'

# 3. 导入检查
python -c "from core import IncrementalUpdateLogger, UniversalNamingSystem; print('OK')"

# 4. 循环导入检查
python -c "import core; import utils" 2>&1 | grep -i "circular" && exit 1 || echo "无循环导入"

# === 功能验证（离线）===
# 5. 时间格式化测试
python -c "
from utils import format_timestamp
# 测试毫秒时间戳
result = format_timestamp(1734700800000)
assert '2024' in result or '2025' in result, f'格式化失败: {result}'
print(f'时间格式化测试通过: {result}')
"
```

### 回滚方案
```bash
git revert HEAD  # 推荐方式
# 或手动回退
git checkout origin/main -- main.py && rm -rf core/ utils/
```

---

## PR2: 拆分网络请求函数

### 基本信息
- **分支名**: `refactor/pr2-crawl-requests`
- **优先级**: P0
- **风险等级**: 低
- **预估改动**: ~150行移动
- **依赖**: PR1

### 变更说明
将网络请求函数拆分到独立的爬虫模块。**注意**：Worker 函数依赖转换器，移至 PR5。

### 文件变更清单

#### 新增文件
```
crawl/__init__.py         # 爬虫模块初始化
crawl/requests.py         # 网络请求函数
```

#### 代码迁移映射
| 源文件 | 源代码行范围 | 目标文件 | 说明 |
|--------|-------------|----------|------|
| main.py | 1538-1577 | crawl/requests.py | get_article_list 函数 |
| main.py | 1585-1682 | crawl/requests.py | extract_article_content 函数 |

#### crawl/__init__.py 内容
```python
"""爬虫模块 - 网络请求和文章处理"""
from .requests import get_article_list, extract_article_content

__all__ = [
    'get_article_list',
    'extract_article_content',
]
# 注意：crawl_article_worker_async 将在 PR5 中添加
```

### 依赖关系
```
crawl/requests.py
  └── 依赖: requests, BeautifulSoup, utils.time_utils
```

### 验收标准
- [ ] `from crawl import get_article_list` 可正常导入
- [ ] `from crawl import extract_article_content` 可正常导入
- [ ] 网络请求功能正常（需网络）

### 测试计划
```bash
# === 必跑检查（离线）===
# 1. 语法检查
python -m py_compile crawl/requests.py crawl/__init__.py

# 2. 行数检查
wc -l crawl/*.py | awk '$1 > 300 {print "❌ 超过300行:", $2; exit 1}'

# 3. 导入检查
python -c "from crawl import get_article_list, extract_article_content; print('OK')"

# 4. 循环导入检查
python -c "import crawl" 2>&1 | grep -i "circular" && exit 1 || echo "无循环导入"

# === 功能验证（需网络，可选）===
# python -c "
# from crawl import get_article_list
# result = get_article_list('原油', page_no=1, page_size=1)
# print(f'获取到 {len(result.get(\"response\", {}).get(\"list\", []))} 篇文章')
# "
```

### 回滚方案
```bash
git revert HEAD  # 推荐方式
# 或手动回退
git checkout origin/main -- main.py && rm -rf crawl/
```

---

## PR3: 拆分客户端模块（Cookies/七牛云）

### 基本信息
- **分支名**: `refactor/pr3-clients-modules`
- **优先级**: P0
- **风险等级**: 中（涉及认证和云上传）
- **预估改动**: ~350行移动
- **依赖**: PR1

### 变更说明
将Cookie管理器和七牛云上传器拆分到独立的客户端模块。

### 文件变更清单

#### 新增文件
```
clients/__init__.py           # 客户端模块初始化
clients/cookies.py            # OilChemCookiesManager 类
clients/qiniu_uploader.py     # UploadTask + AsyncMemoryQiniuUploader 类
```

#### 代码迁移映射
| 源文件 | 源代码行范围 | 目标文件 | 说明 |
|--------|-------------|----------|------|
| main.py | 1265-1360 | clients/cookies.py | OilChemCookiesManager 类 |
| main.py | 155-168 | clients/qiniu_uploader.py | UploadTask 类 |
| main.py | 171-391 | clients/qiniu_uploader.py | AsyncMemoryQiniuUploader 类 |

#### clients/__init__.py 内容
```python
"""客户端模块 - Cookie管理和云存储"""
from .cookies import OilChemCookiesManager
from .qiniu_uploader import UploadTask, AsyncMemoryQiniuUploader

__all__ = [
    'OilChemCookiesManager',
    'UploadTask',
    'AsyncMemoryQiniuUploader'
]
```

### 依赖关系
```
clients/cookies.py
  └── 依赖: requests, json, threading

clients/qiniu_uploader.py
  └── 依赖: qiniu, threading, queue, datetime
```

### 验收标准
- [ ] `from clients import OilChemCookiesManager` 可正常导入
- [ ] `from clients import AsyncMemoryQiniuUploader` 可正常导入
- [ ] Cookie加载和验证功能正常
- [ ] 七牛云上传功能正常（需配置密钥）

### 测试计划
```bash
# === 必跑检查（离线）===
# 1. 语法检查
python -m py_compile clients/cookies.py clients/qiniu_uploader.py clients/__init__.py

# 2. 行数检查
wc -l clients/*.py | awk '$1 > 300 {print "❌ 超过300行:", $2; exit 1}'

# 3. 导入检查
python -c "from clients import OilChemCookiesManager, AsyncMemoryQiniuUploader, UploadTask; print('OK')"

# 4. 循环导入检查
python -c "import clients" 2>&1 | grep -i "circular" && exit 1 || echo "无循环导入"

# === 功能验证（离线）===
# 5. Cookie管理器初始化测试（不需要真实文件）
python -c "
from clients import OilChemCookiesManager
cm = OilChemCookiesManager('nonexistent.json')
# 测试加载不存在的文件应返回False
result = cm.load_cookies()
assert result == False, '不存在的文件应返回False'
print('Cookie管理器初始化测试通过')
"

# 6. 上传任务类测试
python -c "
from clients import UploadTask
task = UploadTask(b'test data', 'test.txt', 'html', {'title': 'test'})
assert task.file_data == b'test data'
assert task.filename == 'test.txt'
assert task.retry_count == 0
print('UploadTask测试通过')
"

# === 集成测试（需真实文件/网络，可选）===
# python -c "
# from clients import OilChemCookiesManager
# cm = OilChemCookiesManager('cookies_tang.json')
# if cm.load_cookies():
#     print('Cookies加载成功')
#     cm.validate_session()
# "
```

### 回滚方案
```bash
git revert HEAD  # 推荐方式
# 或手动回退
git checkout origin/main -- main.py && rm -rf clients/
```

---

## PR4a: 拆分HTML解析工具

### 基本信息
- **分支名**: `refactor/pr4a-html-utils`
- **优先级**: P0
- **风险等级**: 低
- **预估改动**: ~180行移动
- **依赖**: PR1

### 变更说明
将HTML解析工具函数拆分到独立模块。这是 PR4b（格式转换器）的前置依赖。

### 文件变更清单

#### 新增文件
```
convert/__init__.py           # 转换模块初始化
convert/html_utils.py         # HTML解析工具函数（~180行）
```

#### 兼容性处理
```
convert_to_markdown.py        # 保留为兼容shim，标记deprecated
```

#### 代码迁移映射
| 源文件 | 源代码行范围 | 目标文件 | 说明 |
|--------|-------------|----------|------|
| main.py | 512-548 | convert/html_utils.py | html_table_to_markdown |
| main.py | 551-609 | convert/html_utils.py | html_to_markdown |
| main.py | 612-640 | convert/html_utils.py | html_table_to_data |
| main.py | 643-685 | convert/html_utils.py | html_to_text_and_tables |

#### convert/__init__.py 内容（PR4a阶段）
```python
"""转换模块 - HTML解析和格式转换"""
from .html_utils import (
    html_table_to_markdown,
    html_to_markdown,
    html_table_to_data,
    html_to_text_and_tables
)

__all__ = [
    'html_table_to_markdown',
    'html_to_markdown',
    'html_table_to_data',
    'html_to_text_and_tables',
]
# 注意：AsyncFormatConverter 将在 PR4b 中添加
```

#### convert_to_markdown.py 兼容shim内容
```python
"""
[DEPRECATED] 此文件已废弃，请使用 convert.html_utils 模块
保留此文件仅为向后兼容，将在未来版本移除
"""
import warnings
warnings.warn(
    "convert_to_markdown 已废弃，请改用 from convert import html_to_markdown",
    DeprecationWarning,
    stacklevel=2
)

# Re-export for backward compatibility
from convert.html_utils import (
    html_table_to_markdown,
    html_to_markdown,
    convert_html_files_to_markdown,
    convert_single_html
)

# 别名
convert_single_html = html_to_markdown

__all__ = [
    'html_table_to_markdown',
    'html_to_markdown',
    'convert_html_files_to_markdown',
    'convert_single_html'
]
```

### 验收标准
- [ ] `from convert import html_to_markdown` 可正常导入
- [ ] `from convert import html_table_to_markdown` 可正常导入
- [ ] `from convert_to_markdown import html_to_markdown` 仍可工作（显示deprecation警告）
- [ ] HTML→Markdown 转换功能正常

### 测试计划
```bash
# === 必跑检查（离线）===
# 1. 语法检查
python -m py_compile convert/html_utils.py convert/__init__.py

# 2. 行数检查
wc -l convert/*.py | awk '$1 > 300 {print "❌ 超过300行:", $2; exit 1}'

# 3. 导入检查
python -c "from convert import html_to_markdown, html_table_to_markdown; print('OK')"

# 4. 循环导入检查
python -c "import convert" 2>&1 | grep -i "circular" && exit 1 || echo "无循环导入"

# === 功能验证（离线）===
# 5. HTML转Markdown测试
python -c "
from convert import html_to_markdown, html_table_to_markdown

# 测试段落转换
html1 = '<p>测试段落</p>'
result1 = html_to_markdown(html1, '标题')
assert '标题' in result1, f'标题未出现: {result1}'
print('段落转换测试通过')

# 测试表格转换
html2 = '<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>'
from bs4 import BeautifulSoup
soup = BeautifulSoup(html2, 'html.parser')
table = soup.find('table')
result2 = html_table_to_markdown(table)
assert '|' in result2, f'表格转换失败: {result2}'
assert 'A' in result2 and 'B' in result2
print('表格转换测试通过')
"

# 6. 兼容性检查（deprecation警告）
python -c "
import warnings
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter('always')
    from convert_to_markdown import html_to_markdown
    assert len(w) >= 1, '应该有deprecation警告'
    assert 'deprecated' in str(w[0].message).lower() or 'deprecat' in str(w[0].category.__name__).lower()
print('兼容性检查通过（显示了deprecation警告）')
"
```

### 回滚方案
```bash
git revert HEAD  # 推荐方式
# 或手动回退
git checkout origin/main -- main.py convert_to_markdown.py && rm -rf convert/
```

---

## PR4b: 拆分格式转换器（Word/JSON处理）

### 基本信息
- **分支名**: `refactor/pr4b-format-converter`
- **优先级**: P0
- **风险等级**: 中
- **预估改动**: ~280行移动（拆分后）
- **依赖**: PR4a

### 变更说明
将 `AsyncFormatConverter` 类拆分到独立模块。由于原类571行超标，需要进一步拆分处理方法。

### 文件变更清单

#### 新增文件
```
convert/format_converter.py   # AsyncFormatConverter 主类（~180行）
convert/word_processor.py     # Word文档处理方法（~150行）
```

#### 代码迁移映射
| 源文件 | 源代码行范围 | 目标文件 | 说明 |
|--------|-------------|----------|------|
| main.py | 689-843 | convert/format_converter.py | AsyncFormatConverter 核心方法 |
| main.py | 844-933 | convert/format_converter.py | save_as_html_async 方法 |
| main.py | 935-1090 | convert/format_converter.py | html_to_word_async 方法（调用word_processor） |
| main.py | 1093-1260 | convert/word_processor.py | _process_table_*, _process_image_* 方法 |

#### convert/format_converter.py 结构
```python
"""格式转换器 - 支持HTML/Word/Markdown/JSON"""
from .html_utils import html_to_markdown, html_to_text_and_tables
from .word_processor import WordDocumentProcessor

class AsyncFormatConverter:
    def __init__(self, ...): ...
    def save_as_markdown(self, ...): ...
    def save_as_json(self, ...): ...
    def save_as_html_async(self, ...): ...
    def html_to_word_async(self, ...):
        # 委托给 WordDocumentProcessor
        processor = WordDocumentProcessor(self.doc)
        processor.process_content(...)
```

#### convert/word_processor.py 结构
```python
"""Word文档处理器 - 表格和图片处理"""
from docx import Document
from docx.shared import Inches, Pt

class WordDocumentProcessor:
    def __init__(self, doc): ...
    def process_content(self, soup, ...): ...
    def _process_table_enhanced(self, ...): ...
    def _process_table_cell_content(self, ...): ...
    def _process_table_image(self, ...): ...
    def _process_image_paragraph(self, ...): ...
    def _process_standalone_image(self, ...): ...
    def _extract_cell_text(self, ...): ...
    def _process_table_fallback(self, ...): ...
```

#### 更新 convert/__init__.py
```python
"""转换模块 - HTML解析和格式转换"""
from .html_utils import (
    html_table_to_markdown,
    html_to_markdown,
    html_table_to_data,
    html_to_text_and_tables
)
from .format_converter import AsyncFormatConverter

__all__ = [
    'html_table_to_markdown',
    'html_to_markdown',
    'html_table_to_data',
    'html_to_text_and_tables',
    'AsyncFormatConverter'
]
```

### 验收标准
- [ ] `from convert import AsyncFormatConverter` 可正常导入
- [ ] `convert/format_converter.py` 不超过200行
- [ ] `convert/word_processor.py` 不超过200行
- [ ] HTML→Word 转换功能正常
- [ ] HTML→JSON 转换功能正常

### 测试计划
```bash
# === 必跑检查（离线）===
# 1. 语法检查
python -m py_compile convert/format_converter.py convert/word_processor.py

# 2. 行数检查（严格限制）
wc -l convert/format_converter.py convert/word_processor.py | awk '
    /format_converter/ && $1 > 200 {print "❌ format_converter.py 超过200行:", $1; exit 1}
    /word_processor/ && $1 > 200 {print "❌ word_processor.py 超过200行:", $1; exit 1}
'

# 3. 导入检查
python -c "from convert import AsyncFormatConverter; print('OK')"

# 4. 循环导入检查
python -c "import convert.format_converter; import convert.word_processor" 2>&1 | grep -i "circular" && exit 1 || echo "无循环导入"

# === 功能验证（离线）===
# 5. 格式转换器初始化测试
python -c "
from convert import AsyncFormatConverter
import tempfile
import os

# 创建临时目录测试
with tempfile.TemporaryDirectory() as tmpdir:
    converter = AsyncFormatConverter(
        output_dir=tmpdir,
        formats=['json', 'markdown']  # 不测试word，避免依赖docx
    )
    print(f'支持的格式: {converter.formats}')
    print('格式转换器初始化测试通过')
"

# 6. JSON格式转换测试（离线）
python -c "
from convert import AsyncFormatConverter
import tempfile
import json

with tempfile.TemporaryDirectory() as tmpdir:
    converter = AsyncFormatConverter(output_dir=tmpdir, formats=['json'])

    # 模拟文章数据
    article = {
        'id': 'test_001',
        'title': '测试文章',
        'content': '<p>测试内容</p>',
        'publish_time': 1734700800000
    }

    # 测试JSON保存
    result = converter.save_as_json(article, 'test_001')
    assert result is not None, 'JSON保存失败'

    # 验证文件存在
    import os
    json_files = [f for f in os.listdir(tmpdir) if f.endswith('.json')]
    assert len(json_files) > 0, '未生成JSON文件'
    print('JSON格式转换测试通过')
"
```

### 回滚方案
```bash
git revert HEAD  # 推荐方式
# 或手动回退
git checkout origin/main -- main.py && rm convert/format_converter.py convert/word_processor.py
```

---

## PR5: 拆分爬虫Worker

### 基本信息
- **分支名**: `refactor/pr5-crawl-worker`
- **优先级**: P0
- **风险等级**: 低
- **预估改动**: ~100行移动
- **依赖**: PR2, PR4b

### 变更说明
将单篇文章处理Worker拆分到独立模块。此函数依赖 `convert.AsyncFormatConverter`，因此必须在 PR4b 之后。

### 文件变更清单

#### 新增文件
```
crawl/worker.py               # 单篇文章处理Worker
```

#### 代码迁移映射
| 源文件 | 源代码行范围 | 目标文件 | 说明 |
|--------|-------------|----------|------|
| main.py | 1363-1439 | crawl/worker.py | crawl_article_worker_async 函数 |

#### 更新 crawl/__init__.py
```python
"""爬虫模块 - 网络请求和文章处理"""
from .requests import get_article_list, extract_article_content
from .worker import crawl_article_worker_async

__all__ = [
    'get_article_list',
    'extract_article_content',
    'crawl_article_worker_async'
]
```

#### crawl/worker.py 依赖
```python
"""爬虫Worker - 单篇文章处理"""
import time
import random
import threading

from .requests import extract_article_content
from convert import AsyncFormatConverter  # 使用绝对导入
```

### 验收标准
- [ ] `from crawl import crawl_article_worker_async` 可正常导入
- [ ] Worker 函数可正常处理文章
- [ ] crawl/worker.py 不超过150行

### 测试计划
```bash
# === 必跑检查（离线）===
# 1. 语法检查
python -m py_compile crawl/worker.py

# 2. 行数检查
wc -l crawl/worker.py | awk '$1 > 150 {print "❌ worker.py 超过150行:", $1; exit 1}'

# 3. 导入检查
python -c "from crawl import crawl_article_worker_async; print('OK')"

# 4. 循环导入检查
python -c "import crawl.worker" 2>&1 | grep -i "circular" && exit 1 || echo "无循环导入"

# === 功能验证（离线）===
# 5. Worker函数签名检查
python -c "
from crawl import crawl_article_worker_async
import inspect

sig = inspect.signature(crawl_article_worker_async)
params = list(sig.parameters.keys())
print(f'Worker参数: {params}')

# 检查必要参数存在
required = ['article_info']  # 根据实际情况调整
for p in required:
    assert p in params, f'缺少必要参数: {p}'
print('Worker函数签名检查通过')
"
```

### 回滚方案
```bash
git revert HEAD  # 推荐方式
# 或手动回退
git checkout origin/main -- main.py && rm crawl/worker.py
```

---

## PR6: 拆分存储和爬取管道模块

### 基本信息
- **分支名**: `refactor/pr6-storage-pipeline`
- **优先级**: P0
- **风险等级**: 中
- **预估改动**: ~350行移动
- **依赖**: PR3, PR5

### 变更说明
将结果保存函数和主爬取流程拆分到独立模块。

### 文件变更清单

#### 新增文件
```
storage/__init__.py           # 存储模块初始化
storage/save.py               # save_results 函数
crawl/pipeline.py             # 主爬取流程函数
```

#### 代码迁移映射
| 源文件 | 源代码行范围 | 目标文件 | 说明 |
|--------|-------------|----------|------|
| main.py | 1689-1760 | storage/save.py | save_results 函数 |
| main.py | 1443-1533 | crawl/pipeline.py | crawl_articles_async_multithread |
| main.py | 1764-1904 | crawl/pipeline.py | extract_from_keyword_async_multithread |

#### storage/__init__.py 内容
```python
"""存储模块 - 结果保存"""
from .save import save_results

__all__ = ['save_results']
```

#### crawl/pipeline.py 依赖（使用绝对导入）
```python
"""爬取管道 - 主流程控制"""
from crawl.requests import get_article_list
from crawl.worker import crawl_article_worker_async
from clients import OilChemCookiesManager, AsyncMemoryQiniuUploader
from convert import AsyncFormatConverter
from core import IncrementalUpdateLogger, UniversalNamingSystem
from storage import save_results
```

### 验收标准
- [ ] `from storage import save_results` 可正常导入
- [ ] `from crawl.pipeline import extract_from_keyword_async_multithread` 可正常导入
- [ ] storage/save.py 不超过100行
- [ ] crawl/pipeline.py 不超过300行
- [ ] 完整爬取流程可正常执行

### 测试计划
```bash
# === 必跑检查（离线）===
# 1. 语法检查
python -m py_compile storage/save.py storage/__init__.py crawl/pipeline.py

# 2. 行数检查
wc -l storage/save.py crawl/pipeline.py | awk '
    /save.py/ && $1 > 100 {print "❌ save.py 超过100行:", $1; exit 1}
    /pipeline.py/ && $1 > 300 {print "❌ pipeline.py 超过300行:", $1; exit 1}
'

# 3. 导入检查
python -c "from storage import save_results; print('storage OK')"
python -c "from crawl.pipeline import extract_from_keyword_async_multithread, crawl_articles_async_multithread; print('pipeline OK')"

# 4. 循环导入检查
python -c "import storage; import crawl.pipeline" 2>&1 | grep -i "circular" && exit 1 || echo "无循环导入"

# === 功能验证（离线）===
# 5. save_results 函数签名检查
python -c "
from storage import save_results
import inspect

sig = inspect.signature(save_results)
params = list(sig.parameters.keys())
print(f'save_results参数: {params}')
print('save_results签名检查通过')
"

# 6. pipeline 函数签名检查
python -c "
from crawl.pipeline import extract_from_keyword_async_multithread
import inspect

sig = inspect.signature(extract_from_keyword_async_multithread)
params = list(sig.parameters.keys())
print(f'pipeline主函数参数: {params}')

# 检查关键参数存在
expected = ['keyword']
for p in expected:
    assert p in params, f'缺少参数: {p}'
print('pipeline签名检查通过')
"

# === 集成测试（需网络和cookies，可选）===
# python -c "
# from crawl.pipeline import extract_from_keyword_async_multithread
# extract_from_keyword_async_multithread(
#     keyword='原油',
#     pages_to_crawl=1,
#     output_formats=['json'],
#     save_locally=True,
#     upload_to_qiniu=False
# )
# "
```

### 回滚方案
```bash
git revert HEAD  # 推荐方式
# 或手动回退
git checkout origin/main -- main.py && rm -rf storage/ && rm crawl/pipeline.py
```

---

## PR7: main.py瘦身为兼容入口

### 基本信息
- **分支名**: `refactor/pr7-main-slim`
- **优先级**: P0
- **风险等级**: 低
- **预估改动**: main.py 从1920行减少到~80行
- **依赖**: PR1-PR6

### 变更说明
将 main.py 转换为纯兼容入口，仅保留 re-export 和 CLI 入口。

### main.py 最终内容
```python
"""
隆众资讯爬虫 - 兼容入口
实际实现已拆分到各子模块，此文件保持向后兼容
"""

# === 兼容性导出 ===
# 保持旧的 import 方式可用：from main import XXX

from core import IncrementalUpdateLogger, UniversalNamingSystem
from clients import OilChemCookiesManager, AsyncMemoryQiniuUploader, UploadTask
from crawl import (
    get_article_list,
    extract_article_content,
    crawl_article_worker_async
)
from crawl.pipeline import (
    crawl_articles_async_multithread,
    extract_from_keyword_async_multithread
)
from convert import (
    html_table_to_markdown,
    html_to_markdown,
    html_table_to_data,
    html_to_text_and_tables,
    AsyncFormatConverter
)
from storage import save_results
from utils import format_timestamp

# === 公共API ===
__all__ = [
    # 核心类
    'IncrementalUpdateLogger',
    'UniversalNamingSystem',
    # 客户端
    'OilChemCookiesManager',
    'AsyncMemoryQiniuUploader',
    'UploadTask',
    # 爬虫
    'get_article_list',
    'extract_article_content',
    'crawl_article_worker_async',
    'crawl_articles_async_multithread',
    'extract_from_keyword_async_multithread',
    # 转换
    'html_table_to_markdown',
    'html_to_markdown',
    'html_table_to_data',
    'html_to_text_and_tables',
    'AsyncFormatConverter',
    # 存储
    'save_results',
    # 工具
    'format_timestamp',
]


def main():
    """CLI主入口函数"""
    extract_from_keyword_async_multithread(
        keyword="原油",
        pages_to_crawl=3,
        delay_between_requests=1,
        use_cookies=True,
        output_formats=['json'],
        hours_back=None,
        days_back=None,
        qiniu_config=None,
        save_locally=True,
        upload_to_qiniu=False,
        max_crawl_workers=3,
    )


if __name__ == "__main__":
    main()
```

### 验收标准
- [ ] main.py 不超过100行
- [ ] `from main import extract_from_keyword_async_multithread` 仍可正常工作
- [ ] `python main.py --help` 不报错（如有argparse）
- [ ] 所有旧的 import 路径保持兼容
- [ ] 符号清单中的18个符号全部可导入

### 测试计划
```bash
# === 必跑检查（离线）===
# 1. 行数检查
wc -l main.py | awk '$1 > 100 {print "❌ main.py 超过100行:", $1; exit 1}'

# 2. 语法检查
python -m py_compile main.py

# 3. 全量兼容性测试（对照符号清单）
python -c "
from main import (
    # 核心类
    IncrementalUpdateLogger,
    UniversalNamingSystem,
    # 客户端
    OilChemCookiesManager,
    AsyncMemoryQiniuUploader,
    UploadTask,
    # 爬虫
    get_article_list,
    extract_article_content,
    crawl_article_worker_async,
    crawl_articles_async_multithread,
    extract_from_keyword_async_multithread,
    # 转换
    html_table_to_markdown,
    html_to_markdown,
    html_table_to_data,
    html_to_text_and_tables,
    AsyncFormatConverter,
    # 存储
    save_results,
    # 工具
    format_timestamp,
)
print('✅ 全部18个符号导入成功')
"

# 4. __all__ 检查
python -c "
from main import __all__
expected_count = 18
actual_count = len(__all__)
assert actual_count >= expected_count, f'__all__ 应有 {expected_count} 个，实际 {actual_count} 个'
print(f'✅ __all__ 包含 {actual_count} 个符号')
"

# === 集成测试（需网络，可选）===
# python main.py
```

### 回滚方案
```bash
git revert HEAD~6..HEAD  # 回退所有重构PR（PR1-PR7）
# 或单独回退
git revert HEAD
```

---

## PR8: 统一时间格式化工具，消除重复

### 基本信息
- **分支名**: `refactor/pr8-time-utils`
- **优先级**: P1
- **风险等级**: 低
- **预估改动**: ~80行
- **依赖**: PR7

### 变更说明
将分散在多处的时间格式化逻辑统一到 `utils/time_utils.py`。

### 重复代码位置
| 位置 | 函数名 | 功能 |
|------|--------|------|
| core/logging.py | _format_publish_time | 格式化发布时间（毫秒时间戳） |
| core/naming.py | _format_publish_time_for_csv | 格式化发布时间（CSV用） |
| convert/format_converter.py | _format_publish_time_for_json | 格式化发布时间（JSON用） |
| utils/time_utils.py | format_timestamp | 格式化时间戳 |

### 统一后的 utils/time_utils.py
```python
"""时间工具模块 - 统一的时间格式化函数"""
import datetime
from typing import Union, Optional


def format_timestamp(timestamp_ms: int) -> str:
    """格式化毫秒时间戳为可读字符串"""
    timestamp_sec = timestamp_ms / 1000
    return datetime.datetime.fromtimestamp(timestamp_sec).strftime('%Y-%m-%d %H:%M:%S')


def format_publish_time(publish_time: Union[int, float, str, None]) -> Optional[str]:
    """
    统一的发布时间格式化函数

    支持格式：
    - 13位毫秒时间戳 (如: 1761441750966)
    - 10位秒时间戳 (如: 1761441750)
    - 字符串时间格式

    返回：格式化后的时间字符串 'YYYY-MM-DD HH:MM:SS'
    """
    if publish_time is None:
        return None

    try:
        # 处理13位毫秒时间戳
        if isinstance(publish_time, (int, float)) and publish_time > 1000000000000:
            timestamp_sec = publish_time / 1000
            dt = datetime.datetime.fromtimestamp(timestamp_sec)
            return dt.strftime('%Y-%m-%d %H:%M:%S')

        # 处理10位秒时间戳
        elif isinstance(publish_time, (int, float)) and publish_time > 1000000000:
            dt = datetime.datetime.fromtimestamp(publish_time)
            return dt.strftime('%Y-%m-%d %H:%M:%S')

        # 字符串格式尝试解析
        elif isinstance(publish_time, str):
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y/%m/%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M',
                '%Y-%m-%d'
            ]
            for fmt in formats:
                try:
                    dt = datetime.datetime.strptime(publish_time, fmt)
                    return dt.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    continue
            return publish_time  # 无法解析则原样返回

        return str(publish_time)

    except Exception:
        return str(publish_time) if publish_time else None
```

### 需要更新的调用点
```python
# core/logging.py
from utils.time_utils import format_publish_time
# 删除 _format_publish_time 方法，改用 format_publish_time

# core/naming.py
from utils.time_utils import format_publish_time
# 删除 _format_publish_time_for_csv 方法，改用 format_publish_time

# convert/format_converter.py
from utils.time_utils import format_publish_time
# 删除 _format_publish_time_for_json 方法，改用 format_publish_time
```

### 验收标准
- [ ] 所有时间格式化使用统一的 `format_publish_time` 函数
- [ ] 删除3处重复的时间格式化方法
- [ ] 功能行为保持一致
- [ ] 更新 utils/__init__.py 导出 format_publish_time

### 测试计划
```bash
# === 必跑检查（离线）===
# 1. 语法检查
python -m py_compile utils/time_utils.py

# 2. 导入检查（更新后）
python -c "from utils import format_timestamp, format_publish_time; print('OK')"

# === 功能验证（离线）===
# 3. 全面时间格式化测试
python -c "
from utils.time_utils import format_publish_time

# 测试用例
test_cases = [
    # (输入, 预期包含的内容)
    (1734700800000, '2024'),      # 毫秒时间戳
    (1734700800, '2024'),          # 秒时间戳
    ('2025-01-15 10:30:00', '2025-01-15 10:30:00'),  # 标准格式
    ('2025/01/15 10:30:00', '2025-01-15 10:30:00'),  # 斜杠格式
    ('2025-01-15', '2025-01-15'),  # 仅日期
    (None, None),                  # None处理
    ('invalid', 'invalid'),        # 无法解析，原样返回
]

passed = 0
for input_val, expected in test_cases:
    result = format_publish_time(input_val)
    if expected is None:
        ok = result is None
    else:
        ok = expected in str(result) if result else False
    status = '✅' if ok else '❌'
    print(f'{status} format_publish_time({repr(input_val)}) = {repr(result)}')
    if ok:
        passed += 1

print(f'\\n通过 {passed}/{len(test_cases)} 个测试')
assert passed == len(test_cases), f'有 {len(test_cases) - passed} 个测试失败'
"

# 4. 检查重复代码是否已删除
python -c "
import ast
import os

# 检查这些文件中不应再包含 _format_publish_time
files_to_check = [
    'core/logging.py',
    'core/naming.py',
    'convert/format_converter.py'
]

for filepath in files_to_check:
    if os.path.exists(filepath):
        with open(filepath) as f:
            content = f.read()
        if '_format_publish_time' in content and 'def _format_publish_time' in content:
            print(f'❌ {filepath} 仍包含 _format_publish_time 定义')
        else:
            print(f'✅ {filepath} 已清理重复代码')
"
```

### 回滚方案
```bash
git revert HEAD  # 推荐方式
# 或手动回退
git checkout origin/main -- core/logging.py core/naming.py convert/format_converter.py utils/time_utils.py
```

---

## PR9: 配置外部化

### 基本信息
- **分支名**: `refactor/pr9-config`
- **优先级**: P1
- **风险等级**: 中（涉及敏感配置）
- **预估改动**: ~100行
- **依赖**: PR7

### 变更说明
将硬编码的配置项（Cookie文件路径、七牛云密钥等）外部化到配置文件或环境变量。

### 文件变更清单

#### 新增文件
```
config/__init__.py            # 配置模块初始化
config/settings.py            # 配置读取逻辑
.env.example                  # 环境变量示例
```

#### config/settings.py 内容
```python
"""配置管理模块"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class QiniuConfig:
    """七牛云配置"""
    access_key: str
    secret_key: str
    bucket_name: str
    prefix: str = "crawled_articles"


@dataclass
class CrawlerConfig:
    """爬虫配置"""
    cookies_file: str = "cookies_tang.json"
    default_keyword: str = "原油"
    default_pages: int = 3
    delay_between_requests: float = 1.0
    max_crawl_workers: int = 3
    max_upload_workers: int = 3


@dataclass
class AppConfig:
    """应用总配置"""
    qiniu: Optional[QiniuConfig]
    crawler: CrawlerConfig
    save_locally: bool = True
    upload_to_qiniu: bool = False
    output_formats: list = None

    def __post_init__(self):
        if self.output_formats is None:
            self.output_formats = ['json']


def load_config() -> AppConfig:
    """从环境变量加载配置"""

    # 七牛云配置（可选）
    qiniu_config = None
    if os.getenv('QINIU_ACCESS_KEY'):
        qiniu_config = QiniuConfig(
            access_key=os.getenv('QINIU_ACCESS_KEY'),
            secret_key=os.getenv('QINIU_SECRET_KEY'),
            bucket_name=os.getenv('QINIU_BUCKET_NAME'),
            prefix=os.getenv('QINIU_PREFIX', 'crawled_articles')
        )

    # 爬虫配置
    crawler_config = CrawlerConfig(
        cookies_file=os.getenv('COOKIES_FILE', 'cookies_tang.json'),
        default_keyword=os.getenv('DEFAULT_KEYWORD', '原油'),
        default_pages=int(os.getenv('DEFAULT_PAGES', '3')),
        delay_between_requests=float(os.getenv('DELAY_BETWEEN_REQUESTS', '1.0')),
        max_crawl_workers=int(os.getenv('MAX_CRAWL_WORKERS', '3')),
        max_upload_workers=int(os.getenv('MAX_UPLOAD_WORKERS', '3'))
    )

    return AppConfig(
        qiniu=qiniu_config,
        crawler=crawler_config,
        save_locally=os.getenv('SAVE_LOCALLY', 'true').lower() == 'true',
        upload_to_qiniu=os.getenv('UPLOAD_TO_QINIU', 'false').lower() == 'true',
        output_formats=[x.strip() for x in os.getenv('OUTPUT_FORMATS', 'json').split(',')]
    )


# 全局配置实例
config = load_config()
```

#### .env.example 内容
```bash
# 隆众资讯爬虫配置示例
# 复制此文件为 .env 并填入实际值

# === 七牛云配置（可选）===
# QINIU_ACCESS_KEY=your_access_key
# QINIU_SECRET_KEY=your_secret_key
# QINIU_BUCKET_NAME=your_bucket
# QINIU_PREFIX=crawled_articles

# === 爬虫配置 ===
COOKIES_FILE=cookies_tang.json
DEFAULT_KEYWORD=原油
DEFAULT_PAGES=3
DELAY_BETWEEN_REQUESTS=1.0
MAX_CRAWL_WORKERS=3
MAX_UPLOAD_WORKERS=3

# === 输出配置 ===
SAVE_LOCALLY=true
UPLOAD_TO_QINIU=false
OUTPUT_FORMATS=json
```

### 需要更新的调用点
```python
# crawl/pipeline.py
from config import config

def extract_from_keyword_async_multithread(
    keyword=None,
    pages_to_crawl=None,
    ...
):
    # 使用配置默认值
    keyword = keyword or config.crawler.default_keyword
    pages_to_crawl = pages_to_crawl or config.crawler.default_pages
    ...
```

### 验收标准
- [ ] 所有敏感配置可通过环境变量设置
- [ ] 代码中无硬编码的密钥
- [ ] `.env.example` 文件完整
- [ ] 默认配置仍可正常运行
- [ ] config/__init__.py 正确导出

### 测试计划
```bash
# === 必跑检查（离线）===
# 1. 语法检查
python -m py_compile config/settings.py config/__init__.py

# 2. 行数检查
wc -l config/*.py | awk '$1 > 150 {print "❌ 超过150行:", $2; exit 1}'

# 3. 导入检查
python -c "from config import config, load_config, AppConfig, CrawlerConfig; print('OK')"

# === 功能验证（离线）===
# 4. 默认配置测试
python -c "
from config import config

# 检查默认值
assert config.crawler.cookies_file == 'cookies_tang.json', '默认cookies文件不正确'
assert config.crawler.default_keyword == '原油', '默认关键词不正确'
assert config.crawler.default_pages == 3, '默认页数不正确'
assert config.save_locally == True, '默认本地保存不正确'
assert config.upload_to_qiniu == False, '默认上传设置不正确'
print('✅ 默认配置测试通过')
print(f'配置内容: {config}')
"

# 5. 环境变量覆盖测试
python -c "
import os
os.environ['COOKIES_FILE'] = 'test_override.json'
os.environ['DEFAULT_PAGES'] = '10'
os.environ['OUTPUT_FORMATS'] = 'json, markdown, html'

# 重新加载配置
from config.settings import load_config
config = load_config()

assert config.crawler.cookies_file == 'test_override.json', '环境变量覆盖失败'
assert config.crawler.default_pages == 10, '整数解析失败'
assert 'markdown' in config.output_formats, 'output_formats解析失败'
assert all(f.strip() == f for f in config.output_formats), 'strip未生效'
print('✅ 环境变量覆盖测试通过')
"

# 6. 检查敏感信息未硬编码
python -c "
import os

# 检查这些文件中不应包含硬编码密钥
sensitive_patterns = ['access_key', 'secret_key', 'QINIU']
files_to_check = ['crawl/pipeline.py', 'clients/qiniu_uploader.py']

for filepath in files_to_check:
    if os.path.exists(filepath):
        with open(filepath) as f:
            content = f.read().lower()
        has_hardcode = False
        for pattern in sensitive_patterns:
            # 检查是否有硬编码值（排除变量名和注释）
            if f'{pattern.lower()}=' in content.replace(' ', '') and 'os.getenv' not in content:
                if 'your_' not in content and 'xxx' not in content:
                    has_hardcode = True
                    break
        if has_hardcode:
            print(f'⚠️ {filepath} 可能包含硬编码配置，请检查')
        else:
            print(f'✅ {filepath} 无硬编码敏感信息')
"
```

### 回滚方案
```bash
git revert HEAD  # 推荐方式
# 或手动回退
git checkout origin/main -- crawl/pipeline.py && rm -rf config/ .env.example
```

---

## 📊 重构后的依赖关系图

```
                      ┌─────────────┐
                      │   main.py   │  (兼容入口，~80行)
                      └──────┬──────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
  │  crawl/       │  │  convert/     │  │  storage/     │
  │  ├─requests   │  │  ├─html_utils │  │  └─save       │
  │  ├─worker ────┼──┤  ├─word_proc  │  └───────────────┘
  │  └─pipeline   │  │  └─converter  │
  └───────┬───────┘  └───────┬───────┘
          │                  │
          ▼                  │
  ┌───────────────┐          │
  │  clients/     │          │
  │  ├─cookies    │          │
  │  └─qiniu      │          │
  └───────────────┘          │
                             │
          ┌──────────────────┘
          ▼
  ┌───────────────┐
  │  core/        │
  │  ├─logging    │
  │  └─naming     │
  └───────┬───────┘
          │
          ▼
  ┌───────────────┐
  │  utils/       │
  │  └─time_utils │
  └───────────────┘

  ┌───────────────┐
  │  config/      │  (可选，PR9后添加)
  │  └─settings   │
  └───────────────┘
```

**依赖规则**：
- `main.py` → 所有模块（仅 re-export）
- `crawl/pipeline` → `crawl/worker`, `crawl/requests`, `clients`, `convert`, `core`, `storage`
- `crawl/worker` → `crawl/requests`, `convert`
- `convert/format_converter` → `convert/html_utils`, `convert/word_processor`
- `core/*`, `utils/*` → 无内部依赖（底层模块）
- **禁止**：子模块向 `main.py` 导入（避免循环）

---

## ✅ 执行检查清单

### 每个 PR 合并前必须通过
```bash
# 1. 语法检查
python -m py_compile <新增/修改的.py文件>

# 2. 行数检查（每个文件）
wc -l <文件> | awk '$1 > 300 {print "❌ 超过300行:", $2; exit 1}'

# 3. 导入检查
python -c "from <模块> import <类/函数>; print('OK')"

# 4. 循环导入检查
python -c "import <所有新模块>" 2>&1 | grep -i "circular\|import"
```

### 最终验收（所有 PR 完成后）
- [ ] main.py 从 1920 行减少到 ~80 行
- [ ] convert_to_markdown.py 已转为兼容 shim（显示 deprecation 警告）
- [ ] 所有模块单文件不超过 300 行
- [ ] 所有模块职责清晰，单一职责
- [ ] `from main import XXX` 旧 API 保持兼容
- [ ] 无循环导入错误
- [ ] 配置已外部化（PR9 后）

---

## ⚠️ 风险评估与注意事项

### 高风险 PR（需特别注意）

| PR | 风险等级 | 风险点 | 缓解措施 |
|----|---------|--------|---------|
| PR4b | 🔴 高 | `AsyncFormatConverter` 拆分后 Word/JSON 转换可能回归 | 准备离线 HTML 样本测试转换结果 |
| PR3 | 🟡 中 | 七牛云上传和 Cookie 认证涉及外部服务 | 先在测试环境验证，保留原代码注释 |
| PR7 | 🟡 中 | main.py 兼容层遗漏导出会破坏旧 API | 对照符号清单逐项检查 |
| PR6 | 🟡 中 | pipeline 涉及多模块协调 | 端到端测试（小规模爬取） |

### 功能回归风险点

1. **格式转换回归**（PR4b）
   - 表格处理：复杂表格（合并单元格）可能丢失
   - 图片处理：图片下载失败的 fallback 逻辑
   - 时间格式化：毫秒/秒时间戳判断边界

2. **认证失效**（PR3）
   - Cookie 加载路径变化
   - Session 对象传递

3. **API 兼容性**（PR7）
   - 默认参数值变化
   - 返回值结构变化

### 建议的验证顺序

```
1. PR1 完成后：验证 main.py 仍可运行
2. PR2+PR3+PR4a 完成后：验证各模块独立导入
3. PR4b+PR5 完成后：验证单篇文章处理
4. PR6 完成后：验证完整爬取流程（1页）
5. PR7 完成后：验证所有 from main import XXX
```

---

## 📋 PR 执行顺序总结

```
PR1 ─────┬───► PR2 ────────────────┐
         │                         │
         ├───► PR3 ────────────────┤
         │                         │
         └───► PR4a ──► PR4b ──► PR5 ──► PR6 ──► PR7 ──► PR8 ──► PR9
                                                  │
                                                  └── 结构拆分完成
```

| 阶段 | PR 范围 | 目标 |
|------|--------|------|
| 结构拆分 | PR1 - PR7 | main.py 瘦身到 ~80 行 |
| 代码优化 | PR8 | 消除重复代码 |
| 配置优化 | PR9 | 配置外部化 |

---

## 📝 附录：离线测试用例

### HTML 转换测试样本
```python
# tests/test_html_utils.py（建议添加）
TEST_HTML = '''
<div class="xq-content">
    <p>这是测试段落</p>
    <table>
        <tr><th>品种</th><th>价格</th></tr>
        <tr><td>原油</td><td>100</td></tr>
    </table>
</div>
'''

def test_html_to_markdown():
    from convert import html_to_markdown
    result = html_to_markdown(TEST_HTML, "测试标题")
    assert "# 测试标题" in result
    assert "原油" in result
    assert "|" in result  # 表格转换
```

### 时间格式化测试样本
```python
# tests/test_time_utils.py（建议添加）
def test_format_publish_time():
    from utils.time_utils import format_publish_time

    # 毫秒时间戳
    assert format_publish_time(1734700800000) is not None

    # 秒时间戳
    assert format_publish_time(1734700800) is not None

    # 字符串
    assert format_publish_time("2025-01-01 12:00:00") == "2025-01-01 12:00:00"

    # None
    assert format_publish_time(None) is None
```

---

*文档版本: v1.3*
*最后更新: 2025-12-20*
*修订说明:
- v1.1: 修复 PR4 超 300 行问题，调整依赖关系，添加兼容 shim
- v1.2: 添加目标/非目标、符号清单、风险评估、离线测试用例
- v1.3: 完善所有 PR 测试计划为离线优先格式，添加详细功能验证用例*
