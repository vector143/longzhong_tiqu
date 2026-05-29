"""
金十数据格式转换器

将金十数据的快讯数据转换为统一的标准JSON格式（与隆众资讯/华尔街见闻/Investing.com字段完全一致）
"""

import hashlib
from typing import Dict, Any, List


class Jin10Formatter:
    """金十数据格式化器"""

    CHANNEL_MAP = {
        1: "市场快讯",
        2: "期货快讯",
        3: "美港快讯",
        4: "A股快讯",
        5: "商品外汇快讯",
    }

    def __init__(self, institution: str = "金十数据"):
        self.institution = institution

    def format_to_standard(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        将金十快讯数据转换为标准格式

        Args:
            item: flash_newest.js 中的单条快讯

        Returns:
            13字段标准 cleaned JSON
        """
        article_id = str(item.get("id", ""))
        data = item.get("data", {})
        content = (data.get("content") or "").strip()
        title_en = (data.get("title") or "").strip()
        publish_time = item.get("time", "")
        channels = item.get("channel", [])
        important = item.get("important", 0)

        # 标题：优先用中文content的前50字符
        if content:
            title = content[:50]
        elif title_en:
            title = title_en[:50]
        else:
            title = f"快讯_{article_id}"

        # cleaned_text: Markdown格式
        body = content or title_en or ""
        cleaned_text = f"# {title}\n\n{body}"

        # 日期
        date = publish_time.split(" ")[0] if publish_time else ""

        # 分类：取第一个非A股的channel
        category = self._determine_category(channels)

        # 内容类型
        content_type = "快讯" if important >= 1 else "资讯"

        # 摘要
        dedup_text = content or title_en or article_id
        content_digest = hashlib.sha1(dedup_text.encode("utf-8")).hexdigest()

        # 原文链接
        source_url = f"https://www.jin10.com/flash/{article_id}"

        return {
            "cleaned_text": cleaned_text,
            "date": date,
            "institution": self.institution,
            "title": title,
            "period": "d",
            "category": category,
            "researchers": [],
            "content_type": content_type,
            "source_json_path": "",
            "content_digest": content_digest,
            "publish_time": publish_time,
            "source_url": source_url,
            "article_id": article_id,
        }

    def _determine_category(self, channels: List[int]) -> str:
        """根据频道列表确定分类，排除A股(channel 4)"""
        for ch in channels:
            if ch != 4 and ch in self.CHANNEL_MAP:
                return self.CHANNEL_MAP[ch]
        # 兜底：如果只有A股或其他未知频道
        if channels:
            return self.CHANNEL_MAP.get(channels[0], "市场快讯")
        return "市场快讯"

    def format_batch(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量格式化"""
        return [self.format_to_standard(item) for item in items]
