"""
Investing.com 数据格式化器

将 Investing.com 的新闻数据转换为项目统一格式（完全对应隆众资讯格式）
"""

from typing import Any, Dict
from datetime import datetime
import hashlib
import re


class InvestingFormatter:
    """Investing.com 数据格式化器"""

    def __init__(self, institution: str = "Investing.com"):
        """
        初始化格式化器

        Args:
            institution: 机构名称
        """
        self.institution = institution

    def format_to_standard(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        将 Investing.com 数据转换为隆众标准格式（完全对应隆众资讯的cleaned格式）

        Args:
            item: Investing.com 原始数据

        Returns:
            标准格式的数据字典（与隆众资讯字段完全一致）
        """
        # 提取基础信息
        article_id = item.get("id", "")
        if not article_id:
            article_id = str(hash(item.get("url", "")))[-10:]

        title = item.get("title", "").strip()
        content = item.get("content", "")
        if not content:
            content = item.get("summary", "")

        # 解析时间
        publish_time = item.get("publish_time", "")
        date_str = self._parse_date(publish_time)
        publish_time_full = self._format_publish_time(publish_time)

        # 构建 cleaned_text（Markdown格式：# 标题 + 内容）
        cleaned_text = f"# {title}\n\n{content}"

        # 生成稳定摘要（用于去重）
        # 列表页常只有 summary，详情页才有完整正文；去重键必须在两种状态下保持一致。
        content_digest = hashlib.sha1(
            self._build_dedup_key(item, title, content).encode("utf-8")
        ).hexdigest()

        # 确定分类
        category = self._determine_category(item.get("category", ""))

        # 提取作者
        author = item.get("author", "")
        researchers = [author] if author else []

        # 构建标准格式（完全对应隆众资讯的cleaned格式）
        standard_data = {
            # 隆众资讯的cleaned格式字段（按顺序）
            "cleaned_text": cleaned_text,
            "date": date_str,
            "institution": self.institution,
            "title": title,
            "period": "d",  # 日度数据
            "category": category,
            "researchers": researchers,
            "content_type": "资讯",
            "source_json_path": "",  # Investing.com 没有源JSON路径
            "content_digest": content_digest,
            "publish_time": publish_time_full,
            "source_url": item.get("url", ""),
            "article_id": article_id,
        }

        return standard_data

    def _build_dedup_key(self, item: Dict[str, Any], title: str, content: str) -> str:
        """
        构建稳定去重键

        优先使用 article_id / URL，确保列表态与详情态命中同一条文章。
        只有在缺少稳定标识时才退回标题+内容。
        """
        article_id = str(item.get("id") or item.get("article_id") or "").strip()
        source_url = str(item.get("url") or item.get("source_url") or "").strip()

        if article_id and source_url:
            return f"{article_id}|{source_url}"
        if article_id:
            return article_id
        if source_url:
            return source_url

        return f"{title}|{content}"

    def _determine_category(self, channel: str) -> str:
        """
        根据频道确定分类

        Args:
            channel: 频道名称

        Returns:
            分类名称
        """
        category_map = {
            "commodities": "大宗商品",
            "economic-indicators": "经济指标",
            "economy": "宏观经济",
            "latest": "最新资讯",
        }

        return category_map.get(channel, "大宗商品")

    def _parse_date(self, time_str: str) -> str:
        """
        解析日期字符串

        Args:
            time_str: 时间字符串

        Returns:
            日期字符串，格式为 "YYYY-MM-DD"
        """
        if not time_str:
            return datetime.now().strftime("%Y-%m-%d")

        try:
            # 尝试解析 ISO 格式
            if "T" in time_str:
                dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-%d")

            # 尝试解析常见格式
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y/%m/%d %H:%M:%S",
                "%Y-%m-%d",
            ]

            for fmt in formats:
                try:
                    dt = datetime.strptime(time_str, fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue

            # 尝试提取日期
            date_match = re.search(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})", time_str)
            if date_match:
                date_str = date_match.group(1).replace("/", "-")
                return date_str

        except Exception:
            pass

        return datetime.now().strftime("%Y-%m-%d")

    def _format_publish_time(self, time_str: str) -> str:
        """
        格式化发布时间

        Args:
            time_str: 时间字符串

        Returns:
            格式化的时间字符串，格式为 "YYYY-MM-DD HH:MM:SS"
        """
        if not time_str:
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            # 尝试解析 ISO 格式
            if "T" in time_str:
                dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-%d %H:%M:%S")

            # 尝试解析常见格式
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y/%m/%d %H:%M:%S",
            ]

            for fmt in formats:
                try:
                    dt = datetime.strptime(time_str, fmt)
                    return dt.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    continue

            # 如果只有日期，补充时间
            if re.match(r"^\d{4}-\d{2}-\d{2}$", time_str):
                return f"{time_str} 00:00:00"

        except Exception:
            pass

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _parse_datetime(self, time_str: str) -> tuple:
        """
        解析时间字符串

        Args:
            time_str: 时间字符串

        Returns:
            (日期, 时间) 元组，格式为 ("YYYY-MM-DD", "HH:MM:SS")
        """
        if not time_str:
            now = datetime.now()
            return now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")

        try:
            # 尝试解析 ISO 格式: 2024-01-15T10:30:00Z
            if "T" in time_str:
                dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M:%S")

            # 尝试解析常见格式
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y/%m/%d %H:%M:%S",
                "%d-%m-%Y %H:%M",
                "%m/%d/%Y %H:%M",
                "%Y-%m-%d",
            ]

            for fmt in formats:
                try:
                    dt = datetime.strptime(time_str, fmt)
                    return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M:%S")
                except ValueError:
                    continue

            # 尝试提取日期和时间
            date_match = re.search(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})", time_str)
            time_match = re.search(r"(\d{1,2}:\d{2}(?::\d{2})?)", time_str)

            date_str = date_match.group(1).replace("/", "-") if date_match else ""
            time_str_parsed = time_match.group(1) if time_match else ""

            if date_str:
                if not time_str_parsed:
                    time_str_parsed = "00:00:00"
                elif len(time_str_parsed) == 5:  # HH:MM
                    time_str_parsed += ":00"
                return date_str, time_str_parsed

        except Exception as e:
            print(f"⚠️ 时间解析失败: {time_str}, 错误: {e}")

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def format_batch(self, items: list) -> list:
        """
        批量格式化

        Args:
            items: 新闻列表

        Returns:
            格式化后的列表
        """
        return [self.format_to_standard(item) for item in items]


def format_investing_data(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    便捷函数：格式化单条Investing.com数据

    Args:
        item: 原始新闻数据

    Returns:
        标准化的JSON数据
    """
    formatter = InvestingFormatter()
    return formatter.format_to_standard(item)


def format_investing_batch(items: list) -> list:
    """
    便捷函数：批量格式化Investing.com数据

    Args:
        items: 新闻列表

    Returns:
        格式化后的列表
    """
    formatter = InvestingFormatter()
    return formatter.format_batch(items)
