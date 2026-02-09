"""
华尔街见闻爬虫 - 修复时间解析和去重问题
"""

import time
import hashlib
import pandas as pd
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from bs4 import BeautifulSoup
import re

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    import random

    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("⚠️ 警告：未安装Selenium")


class WallStreetCNSpider:
    """华尔街见闻爬虫 - 修复版"""

    def __init__(self, use_selenium: bool = True):
        self.use_selenium = use_selenium and SELENIUM_AVAILABLE

    def _validate_datetime(self, dt_str: str) -> bool:
        """验证时间字符串是否合理"""
        if not dt_str or len(dt_str) < 10:
            return False

        # 检查格式
        pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
        if not re.match(pattern, dt_str):
            return False

        # 提取年份
        try:
            year = int(dt_str[:4])
            return 2020 <= year <= 2030  # 合理年份范围
        except:
            return False

    def fetch_with_selenium(self, url: str = "https://wallstreetcn.com/live/global") -> Optional[str]:
        """使用Selenium获取页面"""
        if not SELENIUM_AVAILABLE:
            print("❌ Selenium不可用")
            return None

        print("🚀 加载华尔街见闻页面...")

        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        driver = webdriver.Chrome(options=options)

        try:
            driver.get(url)
            print("✅ 页面加载完成")
            time.sleep(3)

            # 滚动加载
            for i in range(2):
                driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(1)

            return driver.page_source

        except Exception as e:
            print(f"❌ 错误: {e}")
            return None
        finally:
            driver.quit()

    def parse_live_news_optimized(self, html: str) -> List[Dict[str, str]]:
        """解析新闻 - 使用正确的兄弟关系"""
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        news_items = []
        seen_hashes = set()

        time_elements = soup.find_all('time')
        print(f"🔍 找到 {len(time_elements)} 个时间元素")

        for idx, time_elem in enumerate(time_elements, 1):
            try:
                # 1. 提取时间
                datetime_str = time_elem.get('datetime', '').strip()
                if not datetime_str or not self._validate_datetime(datetime_str):
                    continue

                # 2. 找到time的父元素live-item
                live_item = time_elem.parent
                if not live_item or 'live-item' not in str(live_item.get('class', [])):
                    continue

                # 3. 在live-item中查找live-item_main
                main_container = live_item.find('div', class_=lambda x: x and 'live-item_main' in str(x))
                if not main_container:
                    continue

                # 4. 提取标题（可能为空）
                title_elem = main_container.find('div', class_=lambda x: x and 'live-item_title' in str(x))
                title = title_elem.get_text(strip=True) if title_elem else None

                # 5. 提取内容
                html_container = main_container.find('div', class_=lambda x: x and 'live-item_html' in str(x))
                content = None
                if html_container:
                    p_tags = html_container.find_all('p')
                    if p_tags:
                        texts = [p.get_text(strip=True) for p in p_tags if p.get_text(strip=True)]
                        content = ' '.join(texts) if texts else html_container.get_text(strip=True)
                    else:
                        content = html_container.get_text(strip=True)

                if not content:
                    continue

                # 6. 处理短新闻（没有标题）
                if not title:
                    title = content[:80] + "..." if len(content) > 80 else content

                # 7. 创建新闻条目
                news_item = {
                    'datetime': datetime_str,
                    'title': title,
                    'content': content,
                    'source': '华尔街见闻'
                }

                # 去重
                item_hash = hashlib.md5(f"{datetime_str}|{title[:50]}".encode()).hexdigest()
                if item_hash not in seen_hashes:
                    seen_hashes.add(item_hash)
                    news_items.append(news_item)
                    print(f"  ✅ 第{idx}条: {title[:40]}...")

            except Exception as e:
                continue

        print(f"📊 解析完成: {len(news_items)} 条新闻")
        return news_items

    def _find_news_container(self, time_elem):
        """查找新闻容器 - 更精确的查找"""
        # 向上查找包含标题的容器
        current = time_elem

        for _ in range(4):  # 最多向上4层
            current = current.parent
            if current is None:
                return None

            # 检查是否有标题元素（更严格的检查）
            title_elem = current.find(class_=lambda x: x and 'title' in str(x).lower())
            if title_elem and title_elem.get_text(strip=True):
                # 同时检查是否有内容元素
                content_elem = current.find(['p', 'div'],
                                            string=lambda x: x and len(str(x).strip()) > 20)
                if content_elem:
                    return current

        return None

    def _extract_title(self, container):
        """提取标题"""
        # 优先查找live-item_title
        title_elem = container.find(class_=lambda x: x and 'live-item_title' in str(x))
        if title_elem:
            return title_elem.get_text(strip=True)

        # 次选其他标题元素
        for tag in ['h1', 'h2', 'h3', 'h4', 'div', 'span']:
            elem = container.find(tag, class_=lambda x: x and 'title' in str(x).lower())
            if elem and elem.get_text(strip=True):
                return elem.get_text(strip=True)

        return None

    def _extract_content_preview(self, container):
        """提取内容预览（用于标题）"""
        # 先查找live-item_html
        html_container = container.find(class_=lambda x: x and 'live-item_html' in str(x))

        if html_container:
            # 先找p标签
            p_tags = html_container.find_all('p')
            if p_tags:
                first_p = p_tags[0].get_text(strip=True)
                if first_p:
                    return first_p

            # 没有p标签，直接取文本
            text = html_container.get_text(strip=True)
            if text:
                return text

        # 如果没有live-item_html，尝试从容器中找第一个有意义的文本
        # 查找所有文本元素，跳过空的和太短的
        for elem in container.find_all(['p', 'div', 'span']):
            text = elem.get_text(strip=True)
            if text and len(text) > 5:  # 至少5个字符
                return text

        return None

    def _extract_content(self, container):
        """提取内容"""
        # 优先查找live-item_html中的p标签
        html_container = container.find(class_=lambda x: x and 'live-item_html' in str(x))
        if html_container:
            p_tags = html_container.find_all('p')
            if p_tags:
                texts = [p.get_text(strip=True) for p in p_tags if p.get_text(strip=True)]
                if texts:
                    return ' '.join(texts)

        # 查找所有p标签
        all_p = container.find_all('p')
        if all_p:
            texts = []
            for p in all_p:
                text = p.get_text(strip=True)
                if text and len(text) > 10:  # 过滤太短的段落
                    texts.append(text)
            if texts:
                return ' '.join(texts)

        return None


# ================ 接口兼容函数 ================
def get_article_list(
        keyword: str = "",
        page_no: int = 1,
        page_size: int = 20,
        session=None,
        **kwargs
) -> Optional[Dict[str, Any]]:
    """获取华尔街见闻文章列表"""
    print("📋 获取华尔街见闻直播新闻")

    spider = WallStreetCNSpider(use_selenium=True)
    html = spider.fetch_with_selenium()

    if not html:
        print("❌ 无法获取页面内容")
        return None

    news_items = spider.parse_live_news_optimized(html)

    if not news_items:
        print("❌ 未解析到有效新闻")
        return None

    # 转换为兼容格式
    articles = []
    for item in news_items[:page_size]:
        try:
            # 生成ID
            id_str = f"{item['datetime']}_{item['title']}"
            article_id = hashlib.md5(id_str.encode()).hexdigest()[:16]

            # 转换时间（确保有效）
            dt_str = item['datetime'].replace('Z', '+00:00')
            dt = datetime.fromisoformat(dt_str)
            publish_time = int(dt.timestamp() * 1000)

            articles.append({
                "articleId": article_id,
                "title": item['title'],
                "url": f"https://wallstreetcn.com/live/global#{article_id}",
                "publishTime": publish_time,
                "content": item['content'][:100] + "...",
                "source": "华尔街见闻",
                "columnName": "7x24直播",
                "_raw_datetime": item['datetime'],
                "_raw_content": item['content'],
            })
        except Exception as e:
            print(f"⚠️ 转换新闻数据时出错: {e}")
            continue

    print(f"✅ 获取到 {len(articles)} 条有效新闻")

    return {
        "response": {
            "list": articles
        }
    }


# ================ 测试代码 ================
if __name__ == "__main__":
    print("=" * 60)
    print("测试华尔街见闻爬虫 - 修复版")
    print("=" * 60)

    # 测试
    data = get_article_list(page_size=50)

    if data and data.get('response'):
        articles = data['response']['list']
        print(f"\n✅ 测试成功！获取到 {len(articles)} 条新闻")

        # 显示不重复的新闻
        shown_titles = set()
        for i, article in enumerate(articles):
            title = article['title']
            title_key = title[:30]

            if title_key not in shown_titles:
                shown_titles.add(title_key)
                print(f"\n{len(shown_titles)}. {title[:50]}...")
                print(f"   时间: {article['_raw_datetime']}")
                print(f"   ID: {article['articleId']}")

                if len(shown_titles) >= 5:  # 只显示前5条不同的
                    break
    else:
        print("\n❌ 测试失败")