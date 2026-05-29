"""
金十数据快讯爬虫

从 flash_newest.js 接口获取实时快讯，支持频道过滤和ID去重
"""

import json
import logging
from typing import List, Dict, Any, Optional, Set, Tuple

import requests

logger = logging.getLogger(__name__)

FLASH_URL = "https://www.jin10.com/flash_newest.js"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class Jin10Crawler:
    """金十快讯爬虫"""

    def __init__(
        self,
        include_channels: Tuple[int, ...] = (1, 2, 3, 5),
        skip_vip: bool = True,
    ):
        """
        Args:
            include_channels: 要保留的频道ID，默认排除4(A股)
            skip_vip: 是否跳过VIP锁定条目
        """
        self.include_channels = set(include_channels)
        self.skip_vip = skip_vip
        self.last_id: Optional[str] = None
        self.total_fetched: int = 0

    def fetch_raw(self) -> List[Dict[str, Any]]:
        """
        获取原始快讯数据

        Returns:
            原始快讯列表（50条）

        Raises:
            requests.RequestException: 网络错误
            json.JSONDecodeError: 数据解析错误
        """
        resp = requests.get(
            FLASH_URL,
            headers={
                "User-Agent": USER_AGENT,
                "Referer": "https://www.jin10.com/",
            },
            timeout=30,
        )
        resp.raise_for_status()

        text = resp.text.strip()
        if text.startswith("var newest = "):
            text = text[len("var newest = "):]
        if text.endswith(";"):
            text = text[:-1]

        return json.loads(text)

    def fetch_latest(self) -> List[Dict[str, Any]]:
        """
        获取增量快讯（自动过滤和去重）

        1. 请求 flash_newest.js
        2. 过滤：跳过不关心的频道
        3. 过滤：跳过VIP锁定且内容为空的条目
        4. 去重：只保留 id > last_id 的条目
        5. 更新 last_id

        Returns:
            新增快讯列表（已按时间正序排列）
        """
        raw_items = self.fetch_raw()
        new_items = []

        for item in raw_items:
            if not self._should_include(item):
                continue
            if not self._is_new(item):
                continue
            new_items.append(item)

        # 更新 last_id
        if raw_items:
            all_ids = [item["id"] for item in raw_items if item.get("id")]
            if all_ids:
                current_max = max(all_ids)
                if self.last_id is None or current_max > self.last_id:
                    self.last_id = current_max

        self.total_fetched += len(new_items)
        return new_items

    def init_baseline(self) -> List[Dict[str, Any]]:
        """
        初始化基线：获取当前快照并记录last_id，不返回数据
        """
        raw_items = self.fetch_raw()
        if raw_items:
            ids = [item["id"] for item in raw_items if item.get("id")]
            if ids:
                self.last_id = max(ids)
        return []

    def _should_include(self, item: Dict[str, Any]) -> bool:
        """检查条目是否应该被包含"""
        channels = item.get("channel", [])

        # 如果设定了频道过滤，检查是否有交集
        if self.include_channels:
            if not any(ch in self.include_channels for ch in channels):
                return False

        # 跳过VIP锁定且内容为空的条目
        if self.skip_vip:
            data = item.get("data", {})
            if data.get("lock") and not data.get("content"):
                return False

        return True

    def _is_new(self, item: Dict[str, Any]) -> bool:
        """检查条目是否是新的（id > last_id）"""
        if self.last_id is None:
            return True
        item_id = item.get("id", "")
        return item_id > self.last_id
