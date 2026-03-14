"""
Investing.com 商品新闻爬虫模块

爬取 Investing.com 的商品新闻页面
"""

import time
import re
import json
from typing import Any, Dict, List, Optional
from datetime import datetime
import requests
from bs4 import BeautifulSoup


class InvestingCommodityNewsCrawler:
    """Investing.com 新闻爬虫（支持多个频道）"""

    BASE_URL = "https://www.investing.com"

    # 支持的新闻频道
    CHANNELS = {
        "commodities": "https://www.investing.com/news/commodities-news",
        "economic-indicators": "https://www.investing.com/news/economic-indicators",
        "economy": "https://www.investing.com/news/economy",
    }

    def __init__(
        self,
        channel: str = "commodities",
        session: Optional[requests.Session] = None,
        proxy: Optional[str] = None,
    ):
        """
        初始化爬虫

        Args:
            channel: 频道名称 (commodities, economic-indicators, economy)
            session: requests会话对象，如果为None则创建新会话
            proxy: 代理地址，格式如 "http://127.0.0.1:7890" 或 "socks5://127.0.0.1:1080"
        """
        self.channel = channel
        self.news_url = self.CHANNELS.get(channel, self.CHANNELS["commodities"])
        self.session = session or requests.Session()
        self.proxy = proxy
        self._setup_headers()
        self._setup_proxy()

    def _setup_headers(self):
        """设置请求头，模拟真实浏览器访问"""
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
                "DNT": "1",
            }
        )

        # 设置cookies强制使用英文站点，防止重定向到cn.investing.com
        self.session.cookies.set(
            "StickySession", "id.1234567890.123abc", domain=".investing.com"
        )
        self.session.cookies.set(
            "adBlockerNewUserDomains", "1", domain=".investing.com"
        )
        self.session.cookies.set("edition", "us", domain=".investing.com")  # 强制美国版
        self.session.cookies.set("lang", "en", domain=".investing.com")  # 强制英文

    def _setup_proxy(self):
        """设置代理"""
        if self.proxy:
            self.session.proxies = {
                "http": self.proxy,
                "https": self.proxy,
            }
            print(f"🌐 使用代理: {self.proxy}")

    def fetch_news_list(self, page: int = 1, delay: float = 2.0) -> Dict[str, Any]:
        """
        获取新闻列表

        Args:
            page: 页码（从1开始）
            delay: 请求延迟（秒）

        Returns:
            包含新闻列表和元数据的字典
            {
                'success': bool,
                'data': List[Dict],  # 新闻列表
                'page': int,         # 当前页码
                'channel': str,      # 频道名称
                'error': str         # 错误信息（如果有）
            }
        """
        try:
            # 构建URL
            if page > 1:
                url = f"{self.news_url}/{page}"
            else:
                url = self.news_url

            # 添加延迟避免被封
            if delay > 0:
                time.sleep(delay)

            print(f"🔍 正在获取第 {page} 页: {url}")

            # 发送请求（禁止自动重定向到中文站点）
            response = self.session.get(url, timeout=15, allow_redirects=False)

            # 检查是否被重定向到中文站点
            if response.status_code in (301, 302, 303, 307, 308):
                redirect_url = response.headers.get("Location", "")
                if "cn.investing.com" in redirect_url:
                    print("⚠️ 检测到重定向到中文站点，强制访问英文站点")
                    # 继续访问原URL，但这次允许重定向
                    response = self.session.get(url, timeout=15, allow_redirects=True)
                else:
                    response = self.session.get(
                        redirect_url, timeout=15, allow_redirects=True
                    )

            response.raise_for_status()

            # 解析HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # 检查页面语言，确保是英文页面
            html_tag = soup.find("html")
            if html_tag:
                lang = html_tag.get("lang", "")
                if lang.startswith("zh") or "cn.investing.com" in response.url:
                    print(f"❌ 检测到中文页面 (lang={lang}, url={response.url})")
                    return {
                        "success": False,
                        "data": [],
                        "page": page,
                        "error": "Redirected to Chinese site, please use VPN or proxy",
                    }

            # 提取新闻列表
            news_items = self._parse_news_list(soup)

            if not news_items:
                print("⚠️ 未找到新闻列表，可能页面结构已变化")
                return {
                    "success": False,
                    "data": [],
                    "page": page,
                    "error": "No news items found",
                }

            print(f"✅ 成功获取 {len(news_items)} 条新闻")

            return {
                "success": True,
                "data": news_items,
                "page": page,
                "channel": self.channel,
                "error": None,
            }

        except requests.exceptions.RequestException as e:
            error_msg = f"请求失败: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "data": [],
                "page": page,
                "error": error_msg,
            }
        except Exception as e:
            error_msg = f"解析失败: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "data": [],
                "page": page,
                "error": error_msg,
            }

    def _parse_news_list(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        解析新闻列表页面

        Args:
            soup: BeautifulSoup对象

        Returns:
            新闻列表
        """
        news_items = []

        # Investing.com 的新闻列表可能使用以下选择器
        # 需要根据实际页面结构调整
        selectors = [
            "article.js-article-item",
            "div.largeTitle article",
            "article[data-test='article-item']",
            ".articleItem",
            "article",
        ]

        articles = []
        for selector in selectors:
            articles = soup.select(selector)
            if articles:
                print(f"✅ 使用选择器: {selector}")
                break

        if not articles:
            print("⚠️ 尝试通用解析...")
            # 尝试查找所有包含链接和标题的容器
            articles = soup.find_all("article") or soup.find_all(
                "div", class_=re.compile(r"article|news|item", re.I)
            )

        for article in articles:
            try:
                item = self._parse_article_item(article)
                if item:
                    news_items.append(item)
            except Exception as e:
                print(f"⚠️ 解析单条新闻失败: {e}")
                continue

        return news_items

    def _parse_article_item(self, article) -> Optional[Dict[str, Any]]:
        """
        解析单条新闻

        Args:
            article: BeautifulSoup元素

        Returns:
            新闻数据字典，失败返回None
        """
        # 提取标题和链接
        title_elem = article.find(
            "a", class_=re.compile(r"title", re.I)
        ) or article.find("a")
        if not title_elem:
            return None

        title = title_elem.get_text(strip=True)
        link = title_elem.get("href", "")

        # 补全链接
        if link.startswith("/"):
            link = self.BASE_URL + link
        elif not link.startswith("http"):
            return None

        # 过滤中文站点链接
        if "cn.investing.com" in link:
            return None

        # 过滤非新闻链接：只保留包含 /news/ 的URL
        if "/news/" not in link:
            return None

        # 提取ID（从URL中）
        article_id = self._extract_id_from_url(link)

        # 提取时间
        time_elem = article.find("time") or article.find(
            class_=re.compile(r"date|time", re.I)
        )
        publish_time = ""
        if time_elem:
            publish_time = time_elem.get("datetime") or time_elem.get_text(strip=True)

        # 提取摘要
        summary_elem = article.find(
            class_=re.compile(r"summary|description|excerpt", re.I)
        )
        summary = summary_elem.get_text(strip=True) if summary_elem else ""

        # 提取作者
        author_elem = article.find(class_=re.compile(r"author", re.I))
        author = author_elem.get_text(strip=True) if author_elem else ""

        return {
            "id": article_id,
            "title": title,
            "url": link,
            "summary": summary,
            "publish_time": publish_time,
            "author": author,
            "source": "Investing.com",
            "category": self.channel,
        }

    def _extract_id_from_url(self, url: str) -> str:
        """从URL中提取文章ID"""
        # Investing.com URL格式通常是: /news/commodities-news/article-title-123456
        match = re.search(r"-(\d+)$", url)
        if match:
            return match.group(1)
        # 如果没有找到数字ID，使用URL的hash作为ID
        return str(hash(url))[-10:]

    def _normalize_publish_time(self, raw_time: str) -> str:
        """将发布时间统一为 YYYY-MM-DD HH:MM:SS。"""
        raw_time = (raw_time or "").strip()
        if not raw_time:
            return ""

        try:
            if "T" in raw_time:
                dt = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%m/%d/%Y, %I:%M %p",
            "%m/%d/%Y %I:%M %p",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(raw_time, fmt)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue

        return raw_time

    def _find_time_in_json_ld(self, payload: Any) -> str:
        """从 JSON-LD 中递归提取发布时间。"""
        if isinstance(payload, dict):
            for key in ("dateModified", "datePublished", "dateCreated"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

            for value in payload.values():
                candidate = self._find_time_in_json_ld(value)
                if candidate:
                    return candidate

        if isinstance(payload, list):
            for item in payload:
                candidate = self._find_time_in_json_ld(item)
                if candidate:
                    return candidate

        return ""

    def _extract_publish_time_from_json_ld(self, soup: BeautifulSoup) -> str:
        """优先从 JSON-LD 提取发布时间。"""
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            raw_json = script.string or script.get_text(strip=True)
            if not raw_json:
                continue

            try:
                payload = json.loads(raw_json)
            except json.JSONDecodeError:
                continue

            candidate = self._find_time_in_json_ld(payload)
            if candidate:
                return self._normalize_publish_time(candidate)

        return ""

    def _extract_publish_time_from_text(self, text: str) -> str:
        """从正文头部文本中提取发布时间。"""
        normalized_text = re.sub(r"\s+", " ", text or "").strip()
        if not normalized_text:
            return ""

        for label in ("Updated", "Published"):
            match = re.search(
                rf"{label}\s+(\d{{1,2}}/\d{{1,2}}/\d{{4}},\s+\d{{1,2}}:\d{{2}}\s+[AP]M)",
                normalized_text,
                re.I,
            )
            if match:
                return self._normalize_publish_time(match.group(1))

        return ""

    def _extract_publish_time_from_scoped_time(self, scope) -> str:
        """在正文作用域内查找 time 标签或日期节点。"""
        if scope is None:
            return ""

        time_elem = scope.find("time") or scope.find(
            class_=re.compile(r"date|time|publish", re.I)
        )
        if not time_elem:
            return ""

        raw_time = time_elem.get("datetime") or time_elem.get_text(strip=True)
        return self._normalize_publish_time(raw_time)

    def _extract_publish_time(
        self, soup: BeautifulSoup, title_elem=None, content_elem=None
    ) -> str:
        """按可信度顺序提取正文发布时间。"""
        candidate = self._extract_publish_time_from_json_ld(soup)
        if candidate:
            return candidate

        scoped_nodes = []
        if title_elem is not None:
            scoped_nodes.extend(
                [
                    title_elem.parent,
                    title_elem.find_parent("header"),
                    title_elem.find_parent("article"),
                ]
            )
        if content_elem is not None:
            scoped_nodes.extend(
                [
                    content_elem,
                    content_elem.find_parent("article"),
                    content_elem.find_parent("main"),
                ]
            )
        scoped_nodes.extend([soup.find("article"), soup.find("main")])

        seen_ids = set()
        unique_nodes = []
        for node in scoped_nodes:
            if node is None:
                continue
            node_id = id(node)
            if node_id in seen_ids:
                continue
            seen_ids.add(node_id)
            unique_nodes.append(node)

        for node in unique_nodes:
            candidate = self._extract_publish_time_from_text(
                node.get_text(" ", strip=True)
            )
            if candidate:
                return candidate

        for node in unique_nodes:
            candidate = self._extract_publish_time_from_scoped_time(node)
            if candidate:
                return candidate

        time_elem = soup.find("time") or soup.find(
            class_=re.compile(r"date|time|publish", re.I)
        )
        if not time_elem:
            return ""

        raw_time = time_elem.get("datetime") or time_elem.get_text(strip=True)
        return self._normalize_publish_time(raw_time)

    def fetch_article_content(self, article_url: str) -> Dict[str, Any]:
        """
        获取文章详细内容

        Args:
            article_url: 文章URL

        Returns:
            文章内容字典
            {
                'success': bool,
                'title': str,
                'content': str,
                'html_content': str,
                'publish_time': str,
                'author': str,
                'error': str
            }
        """
        try:
            print(f"📖 正在获取文章: {article_url}")

            # 确保URL是英文站点
            if "cn.investing.com" in article_url:
                article_url = article_url.replace(
                    "cn.investing.com", "www.investing.com"
                )
                print(f"   ⚠️ 转换为英文站点: {article_url}")

            response = self.session.get(article_url, timeout=15, allow_redirects=False)

            # 检查重定向
            if response.status_code in (301, 302, 303, 307, 308):
                redirect_url = response.headers.get("Location", "")
                if "cn.investing.com" not in redirect_url:
                    response = self.session.get(
                        redirect_url, timeout=15, allow_redirects=True
                    )
                else:
                    # 被重定向到中文站点，强制访问英文站点
                    response = self.session.get(
                        article_url, timeout=15, allow_redirects=True
                    )

            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # 提取标题
            title_elem = soup.find("h1") or soup.find(
                class_=re.compile(r"title|headline", re.I)
            )
            title = title_elem.get_text(strip=True) if title_elem else ""

            # 提取正文
            content_selectors = [
                "div.articlePage",
                "div.WYSIWYG",
                "article.article",
                "div[class*='article']",
                "div[class*='content']",
            ]

            content_elem = None
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    break

            if not content_elem:
                content_elem = soup.find("article") or soup.find("main")

            # 清理内容
            if content_elem:
                # 移除脚本、样式等
                for tag in content_elem.find_all(["script", "style", "nav", "aside"]):
                    tag.decompose()

                html_content = str(content_elem)
                text_content = content_elem.get_text(separator="\n", strip=True)
            else:
                html_content = ""
                text_content = ""

            # 提取时间：优先正文结构化时间，避免误拿推荐区旧时间
            publish_time = self._extract_publish_time(
                soup, title_elem=title_elem, content_elem=content_elem
            )

            # 提取作者
            author_elem = soup.find(class_=re.compile(r"author", re.I))
            author = author_elem.get_text(strip=True) if author_elem else ""

            return {
                "success": True,
                "title": title,
                "content": text_content,
                "html_content": html_content,
                "publish_time": publish_time,
                "author": author,
                "error": None,
            }

        except Exception as e:
            error_msg = f"获取文章内容失败: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "title": "",
                "content": "",
                "html_content": "",
                "publish_time": "",
                "author": "",
                "error": error_msg,
            }

    def fetch_multiple_pages(
        self, max_pages: int = 3, delay: float = 2.0
    ) -> List[Dict[str, Any]]:
        """
        获取多页新闻

        Args:
            max_pages: 最大页数
            delay: 页面间延迟（秒）

        Returns:
            所有新闻列表
        """
        all_news = []

        for page in range(1, max_pages + 1):
            result = self.fetch_news_list(page=page, delay=delay)

            if result["success"]:
                all_news.extend(result["data"])
            else:
                print(f"⚠️ 第 {page} 页获取失败，停止爬取")
                break

        return all_news
