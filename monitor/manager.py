"""
统一监控管理器

负责管理多个监控适配器，提供统一的启动/停止/状态查询接口
"""

from typing import Dict, List
from monitor.adapter import MonitorAdapter, MonitorState


class MonitorManager:
    """监控管理器"""

    def __init__(self):
        self._adapters: Dict[str, MonitorAdapter] = {}

    def register(self, adapter: MonitorAdapter):
        """注册监控适配器"""
        self._adapters[adapter.name] = adapter

    def start_all(self):
        """启动所有监控"""
        for adapter in self._adapters.values():
            adapter.start()

    def stop_all(self, timeout: float = 10.0):
        """停止所有监控"""
        for adapter in self._adapters.values():
            adapter.stop(timeout=timeout)

    def get_all_states(self) -> Dict[str, MonitorState]:
        """获取所有监控状态"""
        return {name: adapter.get_state() for name, adapter in self._adapters.items()}

    def get_state(self, name: str) -> MonitorState:
        """获取指定监控状态"""
        if name not in self._adapters:
            raise KeyError(f"监控 {name} 不存在")
        return self._adapters[name].get_state()

    def is_any_running(self) -> bool:
        """检查是否有任何监控在运行"""
        return any(adapter.is_running() for adapter in self._adapters.values())

    def get_adapters(self) -> List[MonitorAdapter]:
        """获取所有适配器"""
        return list(self._adapters.values())
