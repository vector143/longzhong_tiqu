"""
统一监控管理器

负责管理多个监控适配器，提供统一的启动/停止/状态查询与单源控制接口
"""

from typing import Dict, List, Optional
from monitor.adapter import MonitorAdapter, MonitorState


class MonitorManager:
    """监控管理器"""

    def __init__(self):
        self._adapters: Dict[str, MonitorAdapter] = {}
        self._selected_name: Optional[str] = None

    def register(self, adapter: MonitorAdapter):
        """注册监控适配器"""
        self._adapters[adapter.name] = adapter
        if self._selected_name is None:
            self._selected_name = adapter.name

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

    def get_selected_name(self) -> Optional[str]:
        """获取当前选中的监控源名称"""
        if self._selected_name in self._adapters:
            return self._selected_name
        if not self._adapters:
            return None
        self._selected_name = next(iter(self._adapters))
        return self._selected_name

    def get_selected_adapter(self) -> MonitorAdapter:
        """获取当前选中的监控适配器"""
        selected_name = self.get_selected_name()
        if selected_name is None:
            raise KeyError("当前没有已注册的监控源")
        return self._adapters[selected_name]

    def get_selected_state(self) -> MonitorState:
        """获取当前选中的监控状态"""
        return self.get_selected_adapter().get_state()

    def select_source(self, name: str) -> MonitorState:
        """选择指定监控源"""
        if name not in self._adapters:
            raise KeyError(f"监控 {name} 不存在")
        self._selected_name = name
        return self._adapters[name].get_state()

    def select_next(self) -> Optional[str]:
        """切换到下一个监控源"""
        names = list(self._adapters)
        if not names:
            self._selected_name = None
            return None
        current = self.get_selected_name()
        if current is None:
            self._selected_name = names[0]
            return self._selected_name
        index = names.index(current)
        self._selected_name = names[(index + 1) % len(names)]
        return self._selected_name

    def select_previous(self) -> Optional[str]:
        """切换到上一个监控源"""
        names = list(self._adapters)
        if not names:
            self._selected_name = None
            return None
        current = self.get_selected_name()
        if current is None:
            self._selected_name = names[-1]
            return self._selected_name
        index = names.index(current)
        self._selected_name = names[(index - 1) % len(names)]
        return self._selected_name

    def is_any_running(self) -> bool:
        """检查是否有任何监控在运行"""
        return any(adapter.is_running() for adapter in self._adapters.values())

    def get_adapters(self) -> List[MonitorAdapter]:
        """获取所有适配器"""
        return list(self._adapters.values())

    def get_summary(self) -> Dict[str, int]:
        """获取统一控制台顶部汇总"""
        states = self.get_all_states()
        return {
            "sources": len(states),
            "running": sum(
                1 for state in states.values() if state.status.value == "running"
            ),
            "paused": sum(
                1 for state in states.values() if state.status.value == "paused"
            ),
            "errors": sum(
                1 for state in states.values() if state.status.value == "error"
            ),
            "total_items": sum(state.total_items for state in states.values()),
        }

    def pause_selected(self) -> None:
        """暂停当前选中的监控源"""
        self.get_selected_adapter().pause()

    def resume_selected(self) -> None:
        """恢复当前选中的监控源"""
        self.get_selected_adapter().resume()

    def toggle_selected_pause(self) -> None:
        """切换当前选中源的暂停/恢复状态"""
        adapter = self.get_selected_adapter()
        if adapter.is_paused():
            adapter.resume()
            return
        adapter.pause()

    def run_selected_now(self) -> None:
        """触发当前选中源立即执行"""
        self.get_selected_adapter().run_now()

    def start_selected(self) -> None:
        """启动当前选中的监控源"""
        self.get_selected_adapter().start()

    def stop_selected(self, timeout: float = 10.0) -> None:
        """停止当前选中的监控源"""
        self.get_selected_adapter().stop(timeout=timeout)
