"""
时间工具模块 - 统一的时间格式化函数
"""

import datetime
from typing import Optional, Union


def format_timestamp(timestamp_ms: int) -> str:
    """
    格式化毫秒时间戳为可读字符串

    Args:
        timestamp_ms: 毫秒时间戳

    Returns:
        格式化后的时间字符串，格式为 'YYYY-MM-DD HH:MM:SS'
    """
    timestamp_sec = timestamp_ms / 1000
    return datetime.datetime.fromtimestamp(timestamp_sec).strftime("%Y-%m-%d %H:%M:%S")


def format_publish_time(
    publish_time: Optional[Union[int, float, str]],
) -> Optional[str]:
    """
    统一的发布时间格式化函数

    支持格式：
    - 13位毫秒时间戳 (如: 1761441750966)
    - 10位秒时间戳 (如: 1761441750)
    - 字符串时间格式

    Args:
        publish_time: 发布时间（时间戳或字符串）

    Returns:
        格式化后的时间字符串 'YYYY-MM-DD HH:MM:SS'，无法解析返回原值或None
    """
    if publish_time is None:
        return None

    try:
        # 处理13位毫秒时间戳
        if isinstance(publish_time, (int, float)) and publish_time > 1000000000000:
            timestamp_sec = publish_time / 1000
            dt = datetime.datetime.fromtimestamp(timestamp_sec)
            return dt.strftime("%Y-%m-%d %H:%M:%S")

        # 处理10位秒时间戳
        elif isinstance(publish_time, (int, float)) and publish_time > 1000000000:
            dt = datetime.datetime.fromtimestamp(publish_time)
            return dt.strftime("%Y-%m-%d %H:%M:%S")

        # 字符串格式尝试解析
        elif isinstance(publish_time, str):
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y/%m/%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d",
            ]
            for fmt in formats:
                try:
                    dt = datetime.datetime.strptime(publish_time, fmt)
                    return dt.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    continue
            return publish_time  # 无法解析则原样返回

        return str(publish_time)

    except Exception:
        return str(publish_time) if publish_time else None
