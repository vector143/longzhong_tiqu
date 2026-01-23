"""
Cleaned 格式转换器

将资讯 JSON 转换为 Finreport cleaned 标准格式。
支持隆众资讯等多种来源的文章转换。

使用方式：
    from convert.cleaned_converter import CleanedConverter

    converter = CleanedConverter(output_dir="output/report/cleaned")
    result = converter.convert(article_dict, source_path)
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from utils.time_utils import format_publish_time


@dataclass
class ConversionResult:
    """转换结果"""

    success: bool
    cleaned_path: Optional[Path] = None
    error: Optional[str] = None
    skipped_reason: Optional[str] = None


class CleanedConverter:
    """
    资讯 JSON -> Finreport cleaned 格式转换器

    将爬取的资讯 JSON 转换为 Finreport 流程所需的 cleaned 标准格式。

    Attributes:
        output_dir: cleaned 文件输出目录
        on_duplicate: 重复文件处理策略 (skip/overwrite/new_version)
        filename_max_length: 文件名最大长度
    """

    # 机构映射表：URL 域名 → 机构名称
    INSTITUTION_MAP: Dict[str, str] = {
        "oilchem.net": "隆众资讯",
        "mysteel.com": "我的钢铁",
        "coalchem.com": "煤化工网",
        "sci99.com": "卓创资讯",
    }

    def __init__(
        self,
        output_dir: str = "output/report/cleaned",
        on_duplicate: str = "skip",
        filename_max_length: int = 180,
    ) -> None:
        """
        初始化转换器

        Args:
            output_dir: cleaned 文件输出目录
            on_duplicate: 重复处理策略 (skip/overwrite/new_version)
            filename_max_length: 文件名最大长度（含扩展名）
        """
        self.output_dir = Path(output_dir)
        self.on_duplicate = on_duplicate
        self.filename_max_length = filename_max_length
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def convert(
        self,
        article_dict: Dict[str, Any],
        source_path: Optional[str] = None,
    ) -> ConversionResult:
        """
        转换单篇资讯文章

        Args:
            article_dict: 资讯 JSON 数据，包含以下字段：
                - articleId: 文章 ID
                - title: 标题（可含 [分类]：前缀）
                - publishTime: 发布时间
                - url: 原文链接
                - columnName: 栏目名称（如"相关产品-原油"）
                - source: 来源机构
                - content: 正文内容
                - tables: 表格数据（可选）
            source_path: 原始 JSON 文件路径（可选）

        Returns:
            ConversionResult 对象
        """
        try:
            # 1. 提取并验证必要字段
            title_raw = (article_dict.get("title") or "").strip()
            content = (article_dict.get("content") or "").strip()
            publish_time_raw = article_dict.get("publishTime")

            if not title_raw:
                return ConversionResult(success=False, error="缺少 title 字段")
            if not content:
                return ConversionResult(success=False, error="缺少 content 字段")
            if not publish_time_raw:
                return ConversionResult(success=False, error="缺少 publishTime 字段")

            # 2. 解析发布时间
            date, publish_time = self._parse_publish_time(publish_time_raw)
            if not date:
                return ConversionResult(
                    success=False, error=f"无法解析发布时间: {publish_time_raw}"
                )

            # 3. 提取元数据
            institution = self._extract_institution(article_dict)
            cleaned_title = self._clean_title(title_raw)
            # 空标题回退到 article_id
            if not cleaned_title:
                article_id = article_dict.get("articleId", "unknown")
                cleaned_title = f"article_{article_id}" if article_id else "untitled"
            category = self._extract_category(article_dict)
            tables = article_dict.get("tables") or []

            # 4. 构建 cleaned_text（Markdown 格式）
            cleaned_text = self._build_cleaned_text(cleaned_title, content, tables)

            # 5. 计算内容摘要
            content_digest = self._compute_content_digest(cleaned_text)

            # 6. 构建 source_json_path
            source_json_path = self._normalize_source_path(source_path)

            # 7. 构建 cleaned 文档
            cleaned_payload = {
                # 必填字段
                "cleaned_text": cleaned_text,
                "date": date,
                "institution": institution,
                "title": cleaned_title,
                "period": "d",  # 资讯默认为日报
                "category": category,
                "researchers": [],  # 资讯通常无作者
                "content_type": "资讯",
                "source_json_path": source_json_path,
                "content_digest": content_digest,
                # 扩展字段
                "publish_time": publish_time,
                "source_url": article_dict.get("url") or "",
                "article_id": str(article_dict.get("articleId") or ""),
            }

            # 保留表格数据（如果有）
            if tables:
                cleaned_payload["tables"] = tables

            # 8. 生成文件名并处理重复
            filename = self._build_filename(date, institution, cleaned_title)
            target_path = self.output_dir / filename

            resolved_path, skipped_reason = self._resolve_duplicate(target_path)
            if skipped_reason:
                return ConversionResult(
                    success=True,
                    cleaned_path=resolved_path,
                    skipped_reason=skipped_reason,
                )

            # 9. 写入文件
            with resolved_path.open("w", encoding="utf-8") as f:
                json.dump(cleaned_payload, f, ensure_ascii=False, indent=2)

            return ConversionResult(success=True, cleaned_path=resolved_path)

        except Exception as exc:
            return ConversionResult(success=False, error=str(exc))

    def convert_batch(
        self,
        articles: List[Dict[str, Any]],
        source_paths: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        批量转换资讯文章

        Args:
            articles: 资讯 JSON 列表
            source_paths: 对应的源文件路径列表（可选）

        Returns:
            统计结果字典：{total, success, skipped, failed, errors}
        """
        stats = {
            "total": len(articles),
            "success": 0,
            "skipped": 0,
            "failed": 0,
            "errors": [],
        }

        for i, article in enumerate(articles):
            source_path = (
                source_paths[i] if source_paths and i < len(source_paths) else None
            )
            result = self.convert(article, source_path)

            if result.success:
                if result.skipped_reason:
                    stats["skipped"] += 1
                else:
                    stats["success"] += 1
            else:
                stats["failed"] += 1
                stats["errors"].append(
                    {
                        "article_id": article.get("articleId"),
                        "title": (article.get("title") or "")[:50],
                        "error": result.error,
                    }
                )

        return stats

    # =========================================================================
    # 内部方法
    # =========================================================================

    def _parse_publish_time(self, publish_time_raw: Any) -> Tuple[str, str]:
        """
        解析发布时间

        Args:
            publish_time_raw: 原始时间值

        Returns:
            (date, publish_time) 元组
            - date: "YYYY-MM-DD"
            - publish_time: 格式化后的完整时间字符串
        """
        formatted = format_publish_time(publish_time_raw)
        if not formatted:
            return "", ""

        formatted_str = str(formatted)
        # 提取日期部分（前 10 字符）
        date = formatted_str[:10] if len(formatted_str) >= 10 else ""
        return date, formatted_str

    def _extract_institution(self, article: Dict[str, Any]) -> str:
        """从资讯中提取机构名称"""
        # 优先使用 source 字段
        source = (article.get("source") or "").strip()
        if source:
            return source

        # 根据 URL 域名匹配机构
        url = article.get("url") or ""
        for domain, institution in self.INSTITUTION_MAP.items():
            if domain in url:
                return institution

        return "隆众资讯"  # 默认值

    def _extract_category(self, article: Dict[str, Any]) -> str:
        """
        从资讯中提取品种分类

        提取顺序：
        1. columnName 的最后一部分（如"相关产品-原油"→"原油"）
        2. 标题中的 [xxx] 前缀
        3. 默认值"综合"
        """
        # 从 columnName 提取
        column_name = (article.get("columnName") or "").strip()
        if column_name:
            # 支持中英文破折号
            parts = re.split(r"[-－]", column_name)
            last_part = parts[-1].strip()
            if last_part:
                return last_part

        # 从标题提取
        title = article.get("title") or ""
        match = re.match(r"^\s*\[([^\]]+)\]\s*[:：]", title)
        if match:
            return match.group(1).strip()

        return "综合"

    def _clean_title(self, title: str) -> str:
        """
        清理标题

        去除 [分类]：前缀
        """
        cleaned = re.sub(r"^\s*\[[^\]]+\]\s*[:：]\s*", "", title)
        return cleaned.strip()

    def _build_cleaned_text(
        self,
        title: str,
        content: str,
        tables: List[List[List[Any]]],
    ) -> str:
        """
        构建 cleaned_text（Markdown 格式，表格转自然语言）

        格式：
        # 标题

        正文内容...

        ## 表格 1
        【品种A】行情如下：价格为 100（涨跌 +2）；库存为 500。
        """
        parts: List[str] = [f"# {title}"]

        if content:
            parts.append(content)

        for index, table in enumerate(tables, start=1):
            table_text = self._table_to_sentences(table)
            if table_text:
                parts.append(f"## 表格 {index}")
                parts.append(table_text)

        return "\n\n".join(part for part in parts if part).strip()

    def _table_to_sentences(self, table: List[List[Any]]) -> str:
        """将表格数据转换为自然语言描述"""
        if not table or not isinstance(table, list):
            return ""

        valid_rows = [row for row in table if isinstance(row, list) and row]
        if not valid_rows:
            return ""

        def normalize_cell(cell: Any) -> str:
            if cell is None:
                return ""
            return str(cell).strip()

        normalized_rows = [[normalize_cell(cell) for cell in row] for row in valid_rows]

        def is_title_like_row(row: List[str]) -> bool:
            non_empty = [cell for cell in row if cell]
            if len(non_empty) < 2:
                return False
            counts: Dict[str, int] = {}
            for cell in non_empty:
                counts[cell] = counts.get(cell, 0) + 1
            most_common = max(counts.values(), default=0)
            return most_common / len(non_empty) >= 0.6

        title_line = ""
        header_index = 0
        if is_title_like_row(normalized_rows[0]) and len(normalized_rows) > 1:
            header_index = 1
            title_candidates = [cell for cell in normalized_rows[0] if cell]
            if title_candidates:
                title_line = f"{title_candidates[0]}。"

        headers = normalized_rows[header_index]
        if not headers:
            return ""

        lines: List[str] = []
        if title_line:
            lines.append(title_line)

        for row in normalized_rows[header_index + 1 :]:
            if not any(cell for cell in row):
                continue

            max_cols = max(len(headers), len(row))
            header_cells = headers + [""] * (max_cols - len(headers))
            row_cells = row + [""] * (max_cols - len(row))

            subject = row_cells[0].strip()
            prefix = f"【{subject}】行情如下：" if subject else "该项行情如下："

            descriptions: List[str] = []
            for idx in range(1, max_cols):
                key = header_cells[idx].strip() or f"列{idx + 1}"
                value = row_cells[idx].strip()
                if value == "":
                    continue
                if "涨跌" in key and descriptions:
                    descriptions[-1] = f"{descriptions[-1]}（{key} {value}）"
                else:
                    descriptions.append(f"{key}为 {value}")

            if descriptions:
                lines.append(f"{prefix}{'；'.join(descriptions)}。")

        return "\n".join(lines).strip()

    def _table_to_markdown(self, table: List[List[Any]]) -> str:
        """将表格数据转换为 Markdown 格式"""
        if not table or not isinstance(table, list):
            return ""

        # 过滤非列表行
        valid_rows = [row for row in table if isinstance(row, list) and row]
        if not valid_rows:
            return ""

        # 计算最大列数
        max_cols = max((len(row) for row in valid_rows), default=0)
        if max_cols == 0:
            return ""

        def normalize_row(row: List[Any]) -> List[str]:
            cells = [str(cell).strip().replace("|", "\\|") for cell in row]
            # 补齐列数
            cells.extend([""] * (max_cols - len(cells)))
            return cells

        # 表头
        header = normalize_row(valid_rows[0])
        lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(["---"] * max_cols) + " |",
        ]

        # 数据行
        for row in valid_rows[1:]:
            lines.append("| " + " | ".join(normalize_row(row)) + " |")

        return "\n".join(lines)

    def _compute_content_digest(self, text: str, max_chars: int = 4000) -> str:
        """
        计算内容摘要（SHA1）

        Args:
            text: 输入文本
            max_chars: 用于计算哈希的最大字符数

        Returns:
            40 字符的 SHA1 哈希值
        """
        truncated = text[:max_chars] if len(text) > max_chars else text
        return hashlib.sha1(truncated.encode("utf-8")).hexdigest()

    def _build_filename(self, date: str, institution: str, title: str) -> str:
        """
        构建文件名

        格式：{date}_{institution}_{title}.json
        """
        base = self._sanitize_filename(f"{date}_{institution}_{title}")
        return self._truncate_filename(base, ".json")

    def _sanitize_filename(self, name: str) -> str:
        """清理文件名中的非法字符"""
        # 替换非法字符为空格
        name = re.sub(r'[\\/*?:"<>|\n\r\t]', " ", name)
        # 合并连续空格
        name = re.sub(r"\s+", " ", name).strip()
        return name

    def _truncate_filename(self, base: str, suffix: str) -> str:
        """截断文件名到指定长度"""
        max_length = self.filename_max_length

        if max_length <= len(suffix):
            base = base[:1] if base else "cleaned"
            return f"{base}{suffix}"

        if len(base) + len(suffix) > max_length:
            base = base[: max_length - len(suffix)].rstrip()

        if not base:
            base = "cleaned"

        return f"{base}{suffix}"

    def _resolve_duplicate(self, path: Path) -> Tuple[Path, Optional[str]]:
        """
        处理重复文件

        Returns:
            (target_path, skipped_reason) 元组
        """
        if not path.exists():
            return path, None

        if self.on_duplicate == "skip":
            return path, "文件已存在"
        elif self.on_duplicate == "overwrite":
            return path, None
        elif self.on_duplicate == "new_version":
            return self._get_versioned_path(path), None
        else:
            # 无效值，警告并回退到 skip
            print(f"⚠️ 无效的 on_duplicate 值: '{self.on_duplicate}'，回退到 'skip'")
            return path, "文件已存在"

    def _get_versioned_path(self, path: Path) -> Path:
        """获取带版本号的路径"""
        counter = 2
        while True:
            candidate_name = self._truncate_filename(
                f"{path.stem}_v{counter}", path.suffix
            )
            candidate = path.with_name(candidate_name)
            if not candidate.exists():
                return candidate
            counter += 1

    def _normalize_source_path(self, source_path: Optional[str]) -> str:
        """规范化源文件路径"""
        if not source_path:
            return ""
        try:
            return str(Path(source_path).resolve())
        except Exception:
            return str(source_path)
