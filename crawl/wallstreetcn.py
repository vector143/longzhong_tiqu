"""
华尔街见闻全球快讯爬虫模块

实时爬取华尔街见闻全球快讯页面的内容
"""

import time
from typing import Any, Dict, List, Optional
import requests
from datetime import datetime


class WallStreetCNLiveCrawler:
    """华尔街见闻实时快讯爬虫"""

    BASE_URL = "https://api-one-wscn.awtmt.com"
    API_ENDPOINT = "/apiv1/content/lives"

    def __init__(self, session: Optional[requests.Session] = None):
        """
        初始化爬虫

        Args:
            session: requests会话对象，如果为None则创建新会话
        """
        self.session = session or requests.Session()
        self._setup_headers()

    def _setup_headers(self):
        """设置请求头，模拟浏览器访问"""
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": "https://wallstreetcn.com/live/global",
                "Origin": "https://wallstreetcn.com",
            }
        )

    def fetch_lives(
        self,
        channel: str = "global-channel",
        limit: int = 20,
        cursor: Optional[str] = None,
        important_only: bool = False,
        min_score: int = 1,
    ) -> Dict[str, Any]:
        """
        获取快讯列表

        Args:
            channel: 频道名称，默认 global-channel（全球）
            limit: 每次获取的数量
            cursor: 分页游标（时间戳字符串）
            important_only: 是否只获取重要快讯（Score >= 2）
            min_score: 最低评分过滤（1=全部, 2=重要）

        Returns:
            包含快讯列表和元数据的字典
            {
                'success': bool,
                'data': List[Dict],  # 快讯列表
                'next_cursor': str,  # 下一页游标
                'polling_cursor': str, # 轮询游标（最新ID）
                'error': str         # 错误信息（如果有）
            }
        """
        try:
            # 构建请求参数
            params = {
                "channel": channel,
                "client": "pc",
                "limit": limit,
            }

            if cursor:
                params["cursor"] = cursor

            # 添加重要性过滤参数
            if important_only:
                params["important"] = "true"

            # 发送请求
            url = f"{self.BASE_URL}{self.API_ENDPOINT}"
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            # 解析响应
            result = response.json()

            # 检查响应状态
            if result.get("code") != 20000:
                return {
                    "success": False,
                    "data": [],
                    "next_cursor": None,
                    "polling_cursor": None,
                    "error": result.get("message", "Unknown error"),
                }

            data = result.get("data", {})
            items = data.get("items", [])

            # 如果设置了 min_score，进行客户端过滤
            if min_score > 1:
                items = [item for item in items if item.get("score", 0) >= min_score]

            return {
                "success": True,
                "data": items,
                "next_cursor": data.get("next_cursor"),
                "polling_cursor": data.get("polling_cursor"),
                "error": None,
            }

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "data": [],
                "next_cursor": None,
                "polling_cursor": None,
                "error": str(e),
            }

    def parse_live_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析单条快讯数据，转换为统一格式

        Args:
            item: API返回的原始快讯数据

        Returns:
            标准化的快讯数据
        """
        # 根据实际API响应字段调整
        author = item.get("author", {})

        return {
            "id": item.get("id"),
            "title": item.get("title", ""),
            "content": item.get("content", ""),
            "content_text": item.get("content_text", ""),
            "display_time": item.get("display_time"),
            "display_time_str": (
                datetime.fromtimestamp(item.get("display_time", 0)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                if item.get("display_time")
                else ""
            ),
            "uri": item.get("uri", ""),
            "url": item.get("uri", ""),
            "source": "华尔街见闻",
            "channels": item.get("channels", []),
            "score": item.get("score", 0),
            "author_name": author.get("display_name", ""),
            "author_id": author.get("id"),
            "has_image": bool(item.get("images")),
            "images": item.get("images", []),
            "comment_count": item.get("comment_count", 0),
            "type": item.get("type", "live"),
        }

    def _extract_text(self, html_content: str) -> str:
        """
        从HTML内容中提取纯文本

        Args:
            html_content: HTML格式的内容

        Returns:
            纯文本内容
        """
        # 简单的HTML标签清理，可以使用BeautifulSoup做更完善的处理
        import re

        text = re.sub(r"<[^>]+>", "", html_content)
        text = text.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">")
        return text.strip()

    def fetch_incremental(
        self,
        last_id: Optional[int] = None,
        channel: str = "global-channel",
        limit: int = 20,
        important_only: bool = False,
        min_score: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        增量获取新快讯

        Args:
            last_id: 上次获取的最后一条ID
            channel: 频道名称
            limit: 每次获取的数量
            important_only: 是否只获取重要快讯
            min_score: 最低评分过滤（1=全部, 2=重要）

        Returns:
            新快讯列表（已解析为统一格式）
        """
        result = self.fetch_lives(
            channel=channel,
            limit=limit,
            important_only=important_only,
            min_score=min_score,
        )

        if not result["success"]:
            print(f"❌ 获取快讯失败: {result['error']}")
            return []

        # 解析并过滤
        parsed_items = []
        for item in result["data"]:
            try:
                parsed = self.parse_live_item(item)

                # 如果指定了 last_id，只返回比它新的内容
                if last_id and parsed["id"] <= last_id:
                    continue

                parsed_items.append(parsed)
            except Exception as e:
                print(f"⚠️ 解析快讯失败: {e}")
                continue

        return parsed_items


class WallStreetCNMonitor:
    """华尔街见闻实时监控器"""

    def __init__(
        self,
        crawler: WallStreetCNLiveCrawler,
        poll_interval: int = 30,
        channel: str = "global-channel",
        important_only: bool = False,
        min_score: int = 1,
    ):
        """
        初始化监控器

        Args:
            crawler: 爬虫实例
            poll_interval: 轮询间隔（秒）
            channel: 监控的频道
            important_only: 是否只监控重要快讯
            min_score: 最低评分过滤（1=全部, 2=重要）
        """
        self.crawler = crawler
        self.poll_interval = poll_interval
        self.channel = channel
        self.important_only = important_only
        self.min_score = min_score
        self.last_id: Optional[int] = None
        self.is_running = False

    def start(self, callback=None):
        """
        启动监控

        Args:
            callback: 回调函数，接收新快讯列表作为参数
        """
        self.is_running = True
        filter_msg = (
            "重要快讯" if self.important_only or self.min_score > 1 else "全部快讯"
        )
        print(f"🚀 开始监控华尔街见闻 {self.channel} 频道")
        print(f"   轮询间隔: {self.poll_interval} 秒")
        print(f"   过滤模式: {filter_msg} (min_score={self.min_score})")

        # 首次获取，建立基线
        initial_items = self.crawler.fetch_incremental(
            channel=self.channel,
            limit=10,
            important_only=self.important_only,
            min_score=self.min_score,
        )

        if initial_items:
            self.last_id = max(item["id"] for item in initial_items if item.get("id"))
            print(f"✅ 初始化完成，当前最新ID: {self.last_id}")

        # 开始轮询
        while self.is_running:
            try:
                time.sleep(self.poll_interval)

                # 获取增量数据
                new_items = self.crawler.fetch_incremental(
                    last_id=self.last_id,
                    channel=self.channel,
                    important_only=self.important_only,
                    min_score=self.min_score,
                )

                if new_items:
                    print(f"📰 发现 {len(new_items)} 条新快讯")

                    # 更新last_id
                    max_id = max(item["id"] for item in new_items if item.get("id"))
                    if max_id and (not self.last_id or max_id > self.last_id):
                        self.last_id = max_id

                    # 调用回调函数
                    if callback:
                        callback(new_items)
                else:
                    print("⏳ 暂无新快讯")

            except KeyboardInterrupt:
                print("\n⏹️ 监控已停止")
                self.is_running = False
                break
            except Exception as e:
                print(f"❌ 监控出错: {e}")
                time.sleep(5)  # 出错后等待5秒再继续

    def stop(self):
        """停止监控"""
        self.is_running = False
