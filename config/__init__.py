"""
配置管理模块

提供项目统一配置管理：
- Settings: 配置类（支持环境变量覆盖）
- get_settings: 获取配置单例
"""

from .settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
