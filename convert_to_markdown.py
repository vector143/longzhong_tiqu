"""
[DEPRECATED] 此文件已废弃，请使用 convert.html_utils 模块

保留此文件仅为向后兼容，将在未来版本移除。

新代码请使用:
    from convert import html_to_markdown, html_table_to_markdown
"""

import warnings

from convert.html_utils import html_table_to_markdown, html_to_markdown

warnings.warn(
    "convert_to_markdown 已废弃，请改用 from convert import html_to_markdown",
    DeprecationWarning,
    stacklevel=2,
)

# 别名
convert_single_html = html_to_markdown


def convert_html_files_to_markdown(
    html_dir="articles/html", output_dir="articles/markdown"
):
    """
    批量转换HTML文件为Markdown

    [DEPRECATED] 请使用 convert.html_utils 模块
    """
    import os
    from glob import glob
    from bs4 import BeautifulSoup

    os.makedirs(output_dir, exist_ok=True)
    html_files = glob(os.path.join(html_dir, "*.html"))

    if not html_files:
        print(f"❌ 在 {html_dir} 目录下没有找到HTML文件")
        return

    print(f"📂 找到 {len(html_files)} 个HTML文件")

    converted_count = 0
    for html_file in html_files:
        try:
            with open(html_file, "r", encoding="utf-8") as f:
                html_content = f.read()

            soup = BeautifulSoup(html_content, "html.parser")
            title_elem = soup.find("title") or soup.find("h1")
            title = title_elem.get_text(strip=True) if title_elem else ""

            if "没有开通该新闻的页面权限" in html_content:
                print(f"⏭️ 跳过无权限文章: {os.path.basename(html_file)}")
                continue

            markdown_content = html_to_markdown(html_content, title)
            base_name = os.path.splitext(os.path.basename(html_file))[0]
            md_file = os.path.join(output_dir, f"{base_name}.md")

            with open(md_file, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            converted_count += 1
            print(f"✅ 转换完成: {base_name}.md")

        except Exception as e:
            print(f"❌ 转换失败 {html_file}: {e}")

    print(f"\n🎉 转换完成！共转换 {converted_count} 个文件")
    print(f"📁 输出目录: {output_dir}")


__all__ = [
    "html_table_to_markdown",
    "html_to_markdown",
    "convert_html_files_to_markdown",
    "convert_single_html",
]


if __name__ == "__main__":
    convert_html_files_to_markdown(
        html_dir="articles/html", output_dir="articles/markdown"
    )
