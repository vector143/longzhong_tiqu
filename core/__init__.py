"""
核心模块 - 日志记录和命名系统

提供项目核心功能：
- IncrementalUpdateLogger: 增量更新日志记录器
- UniversalNamingSystem: 通用文件命名系统
"""

from .logging import IncrementalUpdateLogger
from .naming import UniversalNamingSystem

__all__ = ["IncrementalUpdateLogger", "UniversalNamingSystem"]
