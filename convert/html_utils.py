"""
HTML解析工具模块

提供HTML到各种格式的转换工具函数：
- html_table_to_markdown: HTML表格转Markdown
- html_to_markdown: HTML内容转Markdown
- html_table_to_data: HTML表格转结构化数据
- html_to_text_and_tables: 提取正文和表格
"""

import re
from typing import List, Set, Tuple

from bs4 import BeautifulSoup


def html_table_to_markdown(table_element) -> str:
    """
    将HTML表格转换为Markdown表格

    Args:
        table_element: BeautifulSoup表格元素

    Returns:
        Markdown格式的表格字符串
    """
    rows = table_element.find_all("tr")
    if not rows:
        return ""

    markdown_rows = []
    max_cols = 0

    # 计算最大列数
    for row in rows:
        cells = row.find_all(["td", "th"])
        col_count = sum(int(cell.get("colspan", 1)) for cell in cells)
        max_cols = max(max_cols, col_count)

    if max_cols == 0:
        return ""

    # 处理每一行
    for row_idx, row in enumerate(rows):
        cells = row.find_all(["td", "th"])
        row_data = []

        for cell in cells:
            text = cell.get_text(strip=True)
            text = re.sub(r"\s+", " ", text)
            text = text.replace("|", "\\|")
            row_data.append(text)

        while len(row_data) < max_cols:
            row_data.append("")

        markdown_rows.append("| " + " | ".join(row_data) + " |")

        if row_idx == 0:
            separator = "| " + " | ".join(["---"] * max_cols) + " |"
            markdown_rows.append(separator)

    return "\n".join(markdown_rows)


def html_to_markdown(html_content: str, title: str = "") -> str:
    """
    将HTML内容转换为干净的Markdown格式

    Args:
        html_content: HTML内容字符串
        title: 可选的标题

    Returns:
        Markdown格式的内容
    """
    soup = BeautifulSoup(html_content, "html.parser")

    for tag in soup.find_all(["script", "style"]):
        tag.decompose()

    markdown_parts = []

    if title:
        markdown_parts.append(f"# {title}\n")

    content_div = soup.find("div", class_="xq-content")
    if not content_div:
        content_div = soup.find("body") or soup

    processed_elements: Set[int] = set()

    for element in content_div.descendants:
        if not hasattr(element, "name") or element.name is None:
            continue

        if id(element) in processed_elements:
            continue

        element_name = element.name.lower()

        if element_name == "table":
            table_md = html_table_to_markdown(element)
            if table_md:
                markdown_parts.append(f"\n{table_md}\n")
            processed_elements.add(id(element))
            for child in element.descendants:
                processed_elements.add(id(child))

        elif element_name == "p" and not element.find_parent("table"):
            text = element.get_text(strip=True)
            text = re.sub(r"\s+", " ", text)
            if text and len(text) > 1:
                markdown_parts.append(f"\n{text}\n")
            processed_elements.add(id(element))

        elif element_name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            level = int(element_name[1])
            text = element.get_text(strip=True)
            if text:
                markdown_parts.append(f"\n{'#' * level} {text}\n")
            processed_elements.add(id(element))

    if len(markdown_parts) <= 1:
        text_content = content_div.get_text(separator="\n", strip=True)
        if text_content:
            lines = [line.strip() for line in text_content.split("\n") if line.strip()]
            markdown_parts.append("\n".join(lines))

    result = "\n".join(markdown_parts)
    result = re.sub(r"\n{3,}", "\n\n", result)

    return result.strip()


def html_table_to_data(table_element) -> List[List[str]]:
    """
    将HTML表格转换为结构化数据（二维数组）

    Args:
        table_element: BeautifulSoup表格元素

    Returns:
        二维数组形式的表格数据
    """
    rows = table_element.find_all("tr")
    if not rows:
        return []

    max_cols = 0
    for row in rows:
        cells = row.find_all(["td", "th"])
        col_count = sum(int(cell.get("colspan", 1)) for cell in cells)
        max_cols = max(max_cols, col_count)

    if max_cols == 0:
        return []

    table_rows = []
    for row in rows:
        cells = row.find_all(["td", "th"])
        row_data = []
        for cell in cells:
            text = cell.get_text(strip=True)
            text = re.sub(r"\s+", " ", text)
            colspan = int(cell.get("colspan", 1))
            row_data.extend([text] * colspan)
        while len(row_data) < max_cols:
            row_data.append("")
        table_rows.append(row_data)

    return table_rows


def html_to_text_and_tables(html_content: str) -> Tuple[str, List[List[List[str]]]]:
    """
    提取正文纯文本与表格数据

    Args:
        html_content: HTML内容字符串

    Returns:
        (正文文本, 表格数据列表) 的元组
    """
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()

    content_div = soup.find("div", class_="xq-content")
    if not content_div:
        content_div = soup.find("body") or soup

    processed_elements: Set[int] = set()
    text_parts: List[str] = []
    tables: List[List[List[str]]] = []

    for element in content_div.descendants:
        if not hasattr(element, "name") or element.name is None:
            continue
        if id(element) in processed_elements:
            continue

        element_name = element.name.lower()
        if element_name == "table":
            table_data = html_table_to_data(element)
            if table_data:
                tables.append(table_data)
            processed_elements.add(id(element))
            for child in element.descendants:
                processed_elements.add(id(child))
        elif element_name in [
            "p",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
        ] and not element.find_parent("table"):
            text = element.get_text(strip=True)
            text = re.sub(r"\s+", " ", text)
            if text and len(text) > 1:
                text_parts.append(text)
            processed_elements.add(id(element))

    if not text_parts:
        text_content = content_div.get_text(separator="\n", strip=True)
        if text_content:
            text_parts = [
                line.strip() for line in text_content.split("\n") if line.strip()
            ]

    content_text = "\n\n".join(text_parts)
    content_text = re.sub(r"\n{3,}", "\n\n", content_text)
    return content_text.strip(), tables
