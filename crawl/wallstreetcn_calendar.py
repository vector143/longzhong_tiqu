"""
华尔街见闻财经日历爬虫模块

实时爬取华尔街见闻财经日历数据
支持按地区、重要性、类型筛选
"""

import time
from typing import Any, Dict, List, Optional
import requests
from datetime import datetime, timedelta


class WallStreetCNCalendarCrawler:
    """华尔街见闻财经日历爬虫"""

    BASE_URL = "https://api-one-wscn.awtmt.com"
    API_ENDPOINT = "/apiv1/finance/macrodatas"

    # 地区映射
    COUNTRY_MAP = {
        "中国": "CN",
        "日本": "JP",
        "欧元区": "EU",
        "美国": "US",
    }

    # 日历类型映射（注意：API中宏观数据和财经事件都可能标记为FE或MD）
    CALENDAR_TYPE_MAP = {
        "宏观": ["MD", "FE"],  # 宏观数据可能包含在两种类型中
        "财报": ["FE"],  # Financial Events
        "假期": ["FE"],  # Financial Events (包含假期)
        "全部": ["MD", "FE"],  # 所有类型
    }

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
                "Referer": "https://wallstreetcn.com/calendar",
                "Origin": "https://wallstreetcn.com",
            }
        )

    def fetch_calendar(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        countries: Optional[List[str]] = None,
        min_importance: int = 2,
        calendar_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        获取财经日历数据

        Args:
            start_date: 开始日期 (YYYY-MM-DD)，默认今天
            end_date: 结束日期 (YYYY-MM-DD)，默认7天后
            countries: 国家列表，如 ["中国", "美国", "日本", "欧元区"]
            min_importance: 最低重要性 (1-5星)，默认2星
            calendar_types: 日历类型列表，如 ["宏观"]

        Returns:
            包含日历数据和元数据的字典
            {
                'success': bool,
                'data': List[Dict],  # 日历事件列表
                'total': int,        # 总数
                'error': str         # 错误信息（如果有）
            }
        """
        try:
            # 默认日期范围
            if not start_date:
                start_date = datetime.now().strftime("%Y-%m-%d")
            if not end_date:
                end_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

            # 构建请求参数
            params = {
                "start": start_date,
                "end": end_date,
            }

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
                    "total": 0,
                    "error": result.get("message", "Unknown error"),
                }

            data = result.get("data", {})
            items = data.get("items", [])

            # 应用过滤条件
            filtered_items = self._filter_items(
                items, countries, min_importance, calendar_types
            )

            return {
                "success": True,
                "data": filtered_items,
                "total": len(filtered_items),
                "error": None,
            }

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "data": [],
                "total": 0,
                "error": str(e),
            }

    def _filter_items(
        self,
        items: List[Dict],
        countries: Optional[List[str]],
        min_importance: int,
        calendar_types: Optional[List[str]],
    ) -> List[Dict]:
        """
        过滤日历事件

        Args:
            items: 原始事件列表
            countries: 国家列表
            min_importance: 最低重要性
            calendar_types: 日历类型列表

        Returns:
            过滤后的事件列表
        """
        filtered = []

        for item in items:
            # 重要性过滤
            importance = item.get("importance", 0)
            if importance < min_importance:
                continue

            # 国家过滤
            if countries:
                country = item.get("country", "")
                if country not in countries:
                    continue

            # 类型过滤
            if calendar_types:
                calendar_type = item.get("calendar_type", "")
                # 检查是否匹配任何指定的类型
                type_match = False
                for ct in calendar_types:
                    expected_types = self.CALENDAR_TYPE_MAP.get(ct, [ct])
                    # 如果映射值是字符串，转为列表
                    if isinstance(expected_types, str):
                        expected_types = [expected_types]
                    # 检查是否匹配
                    if calendar_type in expected_types:
                        type_match = True
                        break
                if not type_match:
                    continue

            filtered.append(item)

        return filtered

    def parse_calendar_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析单条日历事件，转换为统一格式

        Args:
            item: API返回的原始日历数据

        Returns:
            标准化的日历数据
        """
        return {
            "id": item.get("id"),
            "title": item.get("title", ""),
            "country": item.get("country", ""),
            "country_id": item.get("country_id", ""),
            "event": item.get("event", ""),
            "importance": item.get("importance", 0),
            "calendar_type": item.get("calendar_type", ""),
            "public_date": item.get("public_date", 0),
            "observation_date": item.get("observation_date", ""),
            "period": item.get("period", ""),
            "actual": item.get("actual", ""),
            "forecast": item.get("forecast", ""),
            "previous": item.get("previous", ""),
            "revised": item.get("revised", ""),
            "unit": item.get("unit", ""),
            "foresight": item.get("foresight", ""),
            "flag_uri": item.get("flag_uri", ""),
            "source": "华尔街见闻财经日历",
        }

    def fetch_and_parse(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        countries: Optional[List[str]] = None,
        min_importance: int = 2,
        calendar_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取并解析财经日历数据

        Args:
            start_date: 开始日期
            end_date: 结束日期
            countries: 国家列表
            min_importance: 最低重要性
            calendar_types: 日历类型列表

        Returns:
            解析后的日历事件列表
        """
        result = self.fetch_calendar(
            start_date=start_date,
            end_date=end_date,
            countries=countries,
            min_importance=min_importance,
            calendar_types=calendar_types,
        )

        if not result["success"]:
            print(f"❌ 获取日历数据失败: {result['error']}")
            return []

        # 解析数据
        parsed_items = []
        for item in result["data"]:
            try:
                parsed = self.parse_calendar_item(item)
                parsed_items.append(parsed)
            except Exception as e:
                print(f"⚠️ 解析日历事件失败: {e}")
                continue

        return parsed_items


class WallStreetCNCalendarMonitor:
    """华尔街见闻财经日历监控器"""

    def __init__(
        self,
        crawler: WallStreetCNCalendarCrawler,
        poll_interval: int = 3600,
        countries: Optional[List[str]] = None,
        min_importance: int = 2,
        calendar_types: Optional[List[str]] = None,
    ):
        """
        初始化监控器

        Args:
            crawler: 爬虫实例
            poll_interval: 轮询间隔（秒），默认1小时
            countries: 监控的国家列表
            min_importance: 最低重要性
            calendar_types: 日历类型列表
        """
        self.crawler = crawler
        self.poll_interval = poll_interval
        self.countries = countries or ["中国", "美国", "日本", "欧元区"]
        self.min_importance = min_importance
        self.calendar_types = calendar_types or ["宏观"]
        self.seen_ids = set()
        self.is_running = False

    def start(self, callback=None):
        """
        启动监控

        Args:
            callback: 回调函数，接收新日历事件列表作为参数
        """
        self.is_running = True
        print("🚀 开始监控华尔街见闻财经日历")
        print(f"   监控地区: {', '.join(self.countries)}")
        print(f"   最低重要性: {self.min_importance}星")
        print(f"   日历类型: {', '.join(self.calendar_types)}")
        print(f"   轮询间隔: {self.poll_interval} 秒")

        # 首次获取，建立基线
        initial_items = self.crawler.fetch_and_parse(
            countries=self.countries,
            min_importance=self.min_importance,
            calendar_types=self.calendar_types,
        )

        if initial_items:
            self.seen_ids = {item["id"] for item in initial_items if item.get("id")}
            print(f"✅ 初始化完成，已记录 {len(self.seen_ids)} 个事件")

        # 开始轮询
        while self.is_running:
            try:
                time.sleep(self.poll_interval)

                # 获取最新数据
                items = self.crawler.fetch_and_parse(
                    countries=self.countries,
                    min_importance=self.min_importance,
                    calendar_types=self.calendar_types,
                )

                # 过滤新事件
                new_items = [
                    item for item in items if item.get("id") not in self.seen_ids
                ]

                if new_items:
                    print(f"📅 发现 {len(new_items)} 个新日历事件")

                    # 更新seen_ids
                    for item in new_items:
                        if item.get("id"):
                            self.seen_ids.add(item["id"])

                    # 调用回调函数
                    if callback:
                        callback(new_items)
                else:
                    print("⏳ 暂无新日历事件")

            except KeyboardInterrupt:
                print("\n⏹️ 监控已停止")
                self.is_running = False
                break
            except Exception as e:
                print(f"❌ 监控出错: {e}")
                time.sleep(60)  # 出错后等待1分钟再继续

    def stop(self):
        """停止监控"""
        self.is_running = False
