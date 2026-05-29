"""
金十数据快讯爬虫

从 flash_newest.js 接口获取实时快讯，支持频道过滤和ID去重
"""

import json
import logging
import time
from typing import List, Dict, Any, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

FLASH_URL = "https://www.jin10.com/flash_newest.js"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
MAX_RETRIES = 3
RETRY_BACKOFF = 1.0


class Jin10Crawler:
    """金十快讯爬虫"""

    def __init__(
        self,
        include_channels: Tuple[int, ...] = (1, 2, 3, 5),
        skip_vip: bool = True,
    ):
        self.include_channels = set(include_channels)
        self.skip_vip = skip_vip
        self.last_id: Optional[int] = None
        self.total_fetched: int = 0
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": USER_AGENT,
            "Referer": "https://www.jin10.com/",
        })

    def fetch_raw(self) -> List[Dict[str, Any]]:
        """获取原始快讯数据，带重试"""
        last_exc = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = self._session.get(FLASH_URL, timeout=30)
                resp.raise_for_status()

                text = resp.text.strip()
                if text.startswith("var newest = "):
                    text = text[len("var newest = "):]
                if text.endswith(";"):
                    text = text[:-1]

                return json.loads(text)
            except (requests.RequestException, json.JSONDecodeError) as e:
                last_exc = e
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_BACKOFF * (2 ** attempt)
                    logger.warning("金十请求失败(尝试 %d/%d)，%s后重试: %s",
                                   attempt + 1, MAX_RETRIES, wait, e)
                    time.sleep(wait)

        raise last_exc

    def fetch_latest(self) -> List[Dict[str, Any]]:
        """
        获取增量快讯（自动过滤和去重）

        Returns:
            新增快讯列表
        """
        raw_items = self.fetch_raw()
        new_items = []

        for item in raw_items:
            if not self._should_include(item):
                continue
            if not self._is_new(item):
                continue
            new_items.append(item)

        if raw_items:
            all_ids = [self._parse_id(item["id"]) for item in raw_items if item.get("id")]
            if all_ids:
                current_max = max(all_ids)
                if self.last_id is None or current_max > self.last_id:
                    self.last_id = current_max

        self.total_fetched += len(new_items)
        return new_items

    def init_baseline(self) -> List[Dict[str, Any]]:
        """初始化基线：获取当前快照并记录last_id，不返回数据"""
        raw_items = self.fetch_raw()
        if raw_items:
            ids = [self._parse_id(item["id"]) for item in raw_items if item.get("id")]
            if ids:
                self.last_id = max(ids)
        return []

    def _should_include(self, item: Dict[str, Any]) -> bool:
        channels = item.get("channel", [])

        if self.include_channels:
            if not any(ch in self.include_channels for ch in channels):
                return False

        if self.skip_vip:
            data = item.get("data", {})
            if data.get("lock") and not data.get("content"):
                return False

        return True

    def _is_new(self, item: Dict[str, Any]) -> bool:
        if self.last_id is None:
            return True
        return self._parse_id(item.get("id", "")) > self.last_id

    @staticmethod
    def _parse_id(raw_id) -> int:
        try:
            return int(raw_id)
        except (ValueError, TypeError):
            return 0
