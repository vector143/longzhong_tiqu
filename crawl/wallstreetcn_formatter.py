"""
华尔街见闻数据格式转换器

将华尔街见闻的快讯数据转换为统一的标准JSON格式
参考隆众资讯的JSON结构
"""

import hashlib
from typing import Dict, Any


class WallStreetCNFormatter:
    """华尔街见闻数据格式化器"""

    def __init__(self, institution: str = "华尔街见闻"):
        """
        初始化格式化器

        Args:
            institution: 机构名称
        """
        self.institution = institution

    def format_to_standard(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        将华尔街见闻的数据转换为标准格式（完全对应隆众资讯）

        Args:
            item: 原始快讯数据

        Returns:
            标准化的JSON数据（与隆众资讯字段完全一致）
        """
        # 提取基础信息
        article_id = str(item.get("id", ""))
        title = item.get("title", "") or f"快讯_{article_id}"
        content_text = item.get("content_text", "")
        publish_time = item.get("display_time_str", "")
        url = item.get("url", "")
        author_name = item.get("author_name", "")
        channels = item.get("channels", [])
        score = item.get("score", 1)

        # 生成内容摘要（用于去重）
        content_digest = hashlib.sha1(content_text.encode("utf-8")).hexdigest()

        # 确定分类
        category = self._determine_category(channels, score)

        # 确定内容类型
        content_type = "快讯" if score >= 2 else "资讯"

        # 提取日期
        date = publish_time.split(" ")[0] if publish_time else ""

        # 构建标准格式（完全对应隆众资讯的cleaned格式）
        standard_data = {
            # 隆众资讯的cleaned格式字段（按顺序）
            "cleaned_text": f"# {title}\n\n{content_text}",
            "date": date,
            "institution": self.institution,
            "title": title,
            "period": "d",  # 日度数据
            "category": category,
            "researchers": [author_name] if author_name else [],
            "content_type": content_type,
            "source_json_path": "",  # 华尔街见闻没有源JSON路径
            "content_digest": content_digest,
            "publish_time": publish_time,
            "source_url": url,
            "article_id": article_id,
        }

        return standard_data

    def _determine_category(self, channels: list, score: int) -> str:
        """
        根据频道和评分确定分类

        Args:
            channels: 频道列表
            score: 评分

        Returns:
            分类名称
        """
        # 频道映射
        channel_map = {
            "global-channel": "全球快讯",
            "forex-channel": "外汇市场",
            "us-stock-channel": "美股市场",
            "a-stock-channel": "A股市场",
            "hk-stock-channel": "港股市场",
            "commodity-channel": "大宗商品",
            "bond-channel": "债券市场",
            "crypto-channel": "数字货币",
        }

        # 如果是重要快讯，标记为重要
        if score >= 2:
            category = "重要快讯"
        elif channels:
            # 使用第一个频道作为分类
            first_channel = channels[0]
            category = channel_map.get(first_channel, "全球快讯")
        else:
            category = "全球快讯"

        return category

    def format_batch(self, items: list) -> list:
        """
        批量格式化

        Args:
            items: 快讯列表

        Returns:
            格式化后的列表
        """
        return [self.format_to_standard(item) for item in items]


def format_wallstreetcn_data(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    便捷函数：格式化单条华尔街见闻数据

    Args:
        item: 原始快讯数据

    Returns:
        标准化的JSON数据
    """
    formatter = WallStreetCNFormatter()
    return formatter.format_to_standard(item)


def format_wallstreetcn_batch(items: list) -> list:
    """
    便捷函数：批量格式化华尔街见闻数据

    Args:
        items: 快讯列表

    Returns:
        格式化后的列表
    """
    formatter = WallStreetCNFormatter()
    return formatter.format_batch(items)
