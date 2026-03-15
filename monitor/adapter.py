"""
监控适配器基类和实现

提供统一的监控接口，用于集成不同的监控源
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from threading import Event, Thread
from typing import Any, Dict, Optional
import time


class MonitorStatus(Enum):
    """监控状态枚举"""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class MonitorState:
    """监控状态数据类"""

    name: str
    status: MonitorStatus = MonitorStatus.IDLE
    last_run: Optional[datetime] = None
    last_error: Optional[str] = None
    items_count: int = 0
    total_items: int = 0
    running_time: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)


class MonitorAdapter(ABC):
    """监控适配器基类"""

    def __init__(self, name: str):
        self.name = name
        self._stop_event = Event()
        self._pause_event = Event()
        self._run_now_event = Event()
        self._thread: Optional[Thread] = None
        self._state = MonitorState(name=name)
        self._start_time: Optional[datetime] = None
        self._runtime_start_count = 0
        self._configure_runtime_metadata()

    @abstractmethod
    def _run(self):
        """监控主循环（子类实现）"""
        pass

    def _configure_runtime_metadata(
        self,
        *,
        mode: str = "threaded",
        worker_count: int = 1,
        controller_ready: bool = True,
    ) -> None:
        """初始化统一 runtime 元数据。"""
        self._state.extra["runtime_mode"] = mode
        self._state.extra["runtime_status"] = self._state.extra.get(
            "runtime_status",
            "idle",
        )
        self._state.extra["runtime_worker_count"] = worker_count
        self._state.extra["runtime_active_workers"] = self._state.extra.get(
            "runtime_active_workers",
            0,
        )
        self._state.extra["runtime_restarts"] = self._state.extra.get(
            "runtime_restarts",
            0,
        )
        self._state.extra["runtime_controller_ready"] = controller_ready
        self._state.extra["runtime_last_started_at"] = self._state.extra.get(
            "runtime_last_started_at"
        )
        self._state.extra["runtime_last_stopped_at"] = self._state.extra.get(
            "runtime_last_stopped_at"
        )

    def _runtime_default_active_workers(self) -> int:
        """返回启动时默认的活跃 worker 数。"""
        return int(self._state.extra.get("runtime_worker_count", 1))

    def _before_start(self) -> None:
        """启动前 hook，子类可重置自身 runtime 状态。"""

    def _after_stop(self) -> None:
        """停止后 hook，子类可收尾 runtime 状态。"""

    def _sync_runtime_metadata(self) -> None:
        """获取状态前同步 runtime 元数据。"""

    def _mark_runtime_starting(self) -> None:
        """标记 runtime 已进入启动阶段。"""
        if self._runtime_start_count > 0:
            self._state.extra["runtime_restarts"] = self._runtime_start_count
        self._runtime_start_count += 1
        self._state.extra["runtime_status"] = "starting"
        self._state.extra["runtime_active_workers"] = (
            self._runtime_default_active_workers()
        )
        self._state.extra["runtime_controller_ready"] = True
        self._state.extra["runtime_last_started_at"] = datetime.now()

    def _mark_runtime_running(self) -> None:
        """标记 runtime 已进入运行阶段。"""
        self._state.extra["runtime_status"] = "running"
        self._state.extra["runtime_active_workers"] = (
            self._runtime_default_active_workers()
        )

    def _mark_runtime_stopped(self) -> None:
        """标记 runtime 已停止。"""
        self._state.extra["runtime_status"] = "stopped"
        self._state.extra["runtime_active_workers"] = 0
        self._state.extra["runtime_last_stopped_at"] = datetime.now()

    def _mark_runtime_error(self) -> None:
        """标记 runtime 进入错误态。"""
        self._state.extra["runtime_status"] = "error"

    def start(self):
        """启动监控"""
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._pause_event.clear()
        self._run_now_event.clear()
        self._before_start()
        self._start_time = datetime.now()
        self._state.status = MonitorStatus.RUNNING
        self._mark_runtime_starting()
        self._thread = Thread(target=self._run_wrapper, daemon=True)
        self._thread.start()

    def _run_wrapper(self):
        """运行包装器，处理异常"""
        try:
            self._mark_runtime_running()
            self._run()
        except Exception as e:
            self._state.status = MonitorStatus.ERROR
            self._state.last_error = str(e)
            self._mark_runtime_error()

    def stop(self, timeout: float = 10.0):
        """停止监控"""
        self._stop_event.set()
        self._pause_event.clear()
        self._run_now_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        self._after_stop()
        self._mark_runtime_stopped()
        self._state.status = MonitorStatus.STOPPED

    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self._thread is not None and self._thread.is_alive()

    def get_state(self) -> MonitorState:
        """获取当前状态"""
        self._sync_runtime_metadata()
        if self._start_time and self._state.status == MonitorStatus.RUNNING:
            self._state.running_time = (
                datetime.now() - self._start_time
            ).total_seconds()
        return self._state

    def should_stop(self) -> bool:
        """检查是否应该停止"""
        return self._stop_event.is_set()

    def pause(self):
        """暂停监控轮询"""
        if self._state.status == MonitorStatus.RUNNING:
            self._state.status = MonitorStatus.PAUSED
        self._state.extra["runtime_status"] = "paused"
        self._pause_event.set()

    def resume(self):
        """恢复监控轮询"""
        self._pause_event.clear()
        if self.is_running() and self._state.status == MonitorStatus.PAUSED:
            self._state.status = MonitorStatus.RUNNING
        if self.is_running():
            self._state.extra["runtime_status"] = "running"

    def run_now(self):
        """触发下一轮立即执行"""
        self._run_now_event.set()

    def is_paused(self) -> bool:
        """检查是否已暂停"""
        return self._pause_event.is_set()

    def get_capabilities(self) -> Dict[str, bool]:
        """返回统一控制台可用能力"""
        return {
            "start": True,
            "stop": True,
            "pause": True,
            "resume": True,
            "run_now": True,
        }

    def wait_if_paused(self, poll_interval: float = 0.2) -> bool:
        """在暂停状态下阻塞等待，直到恢复或停止"""
        while self._pause_event.is_set() and not self.should_stop():
            self._state.status = MonitorStatus.PAUSED
            time.sleep(poll_interval)

        if not self.should_stop() and self.is_running():
            self._state.status = MonitorStatus.RUNNING
        return not self.should_stop()

    def wait_interval(self, seconds: int, poll_interval: float = 0.2) -> bool:
        """等待指定秒数，同时响应暂停、立即运行和停止"""
        deadline = time.time() + max(seconds, 0)
        while not self.should_stop():
            if not self.wait_if_paused(poll_interval=poll_interval):
                return False
            if self._run_now_event.is_set():
                self._run_now_event.clear()
                return True
            remaining = deadline - time.time()
            if remaining <= 0:
                return True
            time.sleep(min(poll_interval, remaining))
        return False
