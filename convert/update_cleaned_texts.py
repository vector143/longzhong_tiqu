#!/usr/bin/env python
"""批量更新 cleaned_text（表格转自然句子）。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

from convert.cleaned_converter import CleanedConverter


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_source_path(
    cleaned_data: Dict[str, Any],
    articles_dir: Path,
) -> Optional[Path]:
    source_json_path = str(cleaned_data.get("source_json_path") or "").strip()
    if source_json_path:
        source_path = Path(source_json_path)
        if source_path.exists():
            return source_path

    article_id = str(cleaned_data.get("article_id") or "").strip()
    if not article_id:
        return None

    candidates = sorted(articles_dir.glob(f"*{article_id}*.json"), key=lambda p: p.name)
    if not candidates:
        return None

    for candidate in candidates:
        name = candidate.name
        if name == f"{article_id}.json" or name.endswith(f"_{article_id}.json"):
            return candidate

    return candidates[0]


def _rebuild_cleaned_text(
    converter: CleanedConverter,
    cleaned_data: Dict[str, Any],
    article_data: Dict[str, Any],
) -> Optional[str]:
    title = (cleaned_data.get("title") or "").strip()
    if not title:
        raw_title = (article_data.get("title") or "").strip()
        title = converter._clean_title(raw_title)
        if not title:
            article_id = str(article_data.get("articleId") or "").strip()
            if article_id:
                title = f"article_{article_id}"
            else:
                title = "untitled"

    content = (article_data.get("content") or "").strip()
    tables = article_data.get("tables") or []

    if not content and not tables:
        return None

    return converter._build_cleaned_text(title, content, tables)


def _iter_cleaned_files(cleaned_dir: Path) -> Iterable[Path]:
    return sorted(cleaned_dir.glob("*.json"), key=lambda p: p.name)


def update_cleaned_texts(
    cleaned_dir: Path,
    articles_dir: Path,
    dry_run: bool = False,
) -> Tuple[int, int, int, int]:
    converter = CleanedConverter(output_dir=str(cleaned_dir))

    total = 0
    updated = 0
    skipped = 0
    failed = 0

    for cleaned_path in _iter_cleaned_files(cleaned_dir):
        total += 1
        try:
            cleaned_data = _load_json(cleaned_path)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"❌ 读取失败: {cleaned_path.name} ({exc})")
            continue

        source_path = _find_source_path(cleaned_data, articles_dir)
        if not source_path:
            skipped += 1
            print(f"⚠️  无源文件，跳过: {cleaned_path.name}")
            continue

        try:
            article_data = _load_json(source_path)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"❌ 源文件读取失败: {source_path} ({exc})")
            continue

        new_cleaned_text = _rebuild_cleaned_text(converter, cleaned_data, article_data)
        if not new_cleaned_text:
            skipped += 1
            print(f"⚠️  无内容/表格，跳过: {cleaned_path.name}")
            continue

        new_digest = converter._compute_content_digest(new_cleaned_text)

        old_cleaned_text = cleaned_data.get("cleaned_text")
        old_digest = cleaned_data.get("content_digest")

        if new_cleaned_text == old_cleaned_text and new_digest == old_digest:
            continue

        cleaned_data["cleaned_text"] = new_cleaned_text
        cleaned_data["content_digest"] = new_digest

        if not dry_run:
            cleaned_path.write_text(
                json.dumps(cleaned_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        updated += 1
        print(f"✅ 已更新: {cleaned_path.name}")

    return total, updated, skipped, failed


def main() -> None:
    parser = argparse.ArgumentParser(description="批量更新 cleaned_text")
    parser.add_argument(
        "--cleaned-dir",
        default="output/report/cleaned",
        help="cleaned 文件目录 (默认: output/report/cleaned)",
    )
    parser.add_argument(
        "--articles-dir",
        default="articles/json",
        help="原始文章 JSON 目录 (默认: articles/json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只演练不写入",
    )

    args = parser.parse_args()
    cleaned_dir = Path(args.cleaned_dir)
    articles_dir = Path(args.articles_dir)

    if not cleaned_dir.exists():
        raise SystemExit(f"cleaned_dir 不存在: {cleaned_dir}")
    if not articles_dir.exists():
        raise SystemExit(f"articles_dir 不存在: {articles_dir}")

    total, updated, skipped, failed = update_cleaned_texts(
        cleaned_dir=cleaned_dir,
        articles_dir=articles_dir,
        dry_run=args.dry_run,
    )

    print(
        "\n".join(
            [
                "\n==== 汇总 ====",
                f"总数: {total}",
                f"更新: {updated}",
                f"跳过: {skipped}",
                f"失败: {failed}",
            ]
        )
    )


if __name__ == "__main__":
    main()
