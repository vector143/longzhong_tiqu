#!/usr/bin/env python
"""
Investing.com 爬虫 - 快速使用指南

两种模式：
1. 快速模式（只爬标题）- 不带 --fetch-content
2. 完整模式（爬取正文）- 带 --fetch-content
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 80)
print("Investing.com 爬虫使用指南")
print("=" * 80)
print()

print("📋 支持的频道:")
print("  - commodities (商品新闻)")
print("  - economic-indicators (经济指标)")
print("  - economy (经济新闻)")
print()

print("🚀 快速开始:")
print()

print("1️⃣  快速模式（只爬标题，速度快）")
print("   python crawl/investing_runner.py --all-channels --pages 2")
print("   ⚡ 优点: 速度快，适合快速浏览")
print("   ⚠️  缺点: 只有标题，没有正文内容")
print()

print("2️⃣  完整模式（爬取正文，速度慢）")
print(
    "   python crawl/investing_runner.py --all-channels --pages 2 --fetch-content --delay 3"
)
print("   ✅ 优点: 包含完整正文内容")
print("   ⏱️  缺点: 速度较慢（每篇文章需要额外请求）")
print()

print("💡 推荐用法:")
print("   # 先快速爬取标题，了解有哪些新闻")
print("   python crawl/investing_runner.py --all-channels --pages 3")
print()
print("   # 然后针对感兴趣的频道获取详细内容")
print("   python crawl/investing_runner.py --channel economy --pages 1 --fetch-content")
print()

print("=" * 80)
print("查看完整文档: crawl/README_INVESTING.md")
print("=" * 80)
