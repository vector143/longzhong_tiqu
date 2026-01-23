"""
跨平台键盘监听模块

提供：
- 非阻塞键盘输入监听
- 快捷键回调注册
- 线程安全启动/停止

支持平台：
- Windows: msvcrt.kbhit + msvcrt.getch
- Unix/Linux/macOS: select + termios + tty
"""

from __future__ import annotations

import os
import sys
import threading
import time
from typing import Callable, Dict, List, Optional

# 平台特定导入
if os.name == "nt":
    import msvcrt
else:
    import select
    import termios
    import tty


class KeyboardListener:
    """
    跨平台键盘监听器（线程安全）

    在后台线程中轮询键盘输入，触发已注册的快捷键回调。

    Example:
        listener = KeyboardListener()
        listener.register_key('q', on_quit)
        listener.register_key('r', on_refresh)
        listener.start()
        # ... 运行主逻辑 ...
        listener.stop()
    """

    def __init__(self, poll_interval: float = 0.05) -> None:
        """
        初始化监听器

        Args:
            poll_interval: 轮询间隔（秒），默认 50ms

        Raises:
            ValueError: poll_interval 必须为正数
        """
        if poll_interval <= 0:
            raise ValueError("poll_interval 必须为正数")

        self._poll_interval = poll_interval
        self._callbacks: Dict[str, List[Callable[[], None]]] = {}
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._running = False

        # Unix 终端设置
        self._stdin_fd: Optional[int] = None
        self._stdin_old_settings: Optional[list] = None
        self._stdin_available = True

    @property
    def is_running(self) -> bool:
        """监听器是否正在运行"""
        with self._lock:
            return self._running

    def register_key(self, key: str, callback: Callable[[], None]) -> None:
        """
        注册快捷键回调

        同一个键可以注册多个回调，按注册顺序依次执行。

        Args:
            key: 单字符键值（如 'q', 'r', 'p'）
            callback: 无参回调函数

        Raises:
            ValueError: key 必须为非空字符串
            TypeError: callback 必须可调用
        """
        if not isinstance(key, str) or not key:
            raise ValueError("key 必须为非空字符串")
        if not callable(callback):
            raise TypeError("callback 必须可调用")

        with self._lock:
            if key not in self._callbacks:
                self._callbacks[key] = []
            self._callbacks[key].append(callback)

    def unregister_key(
        self, key: str, callback: Optional[Callable[[], None]] = None
    ) -> None:
        """
        取消快捷键回调注册

        Args:
            key: 键值
            callback: 要移除的回调，None 表示移除该键的所有回调
        """
        with self._lock:
            if key not in self._callbacks:
                return

            if callback is None:
                del self._callbacks[key]
            else:
                try:
                    self._callbacks[key].remove(callback)
                    if not self._callbacks[key]:
                        del self._callbacks[key]
                except ValueError:
                    pass  # 回调不存在，忽略

    def start(self) -> None:
        """
        启动监听（非阻塞）

        创建后台线程进行键盘监听。重复调用无效。
        """
        with self._lock:
            if self._running:
                return

            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run,
                name="KeyboardListener",
                daemon=True,
            )
            self._running = True
            self._thread.start()

    def stop(self) -> None:
        """
        停止监听并恢复终端状态

        等待后台线程结束（最多 1 秒超时）。
        """
        with self._lock:
            if not self._running:
                return

            self._stop_event.set()
            thread = self._thread

        # 等待线程结束（不在锁内等待，避免死锁）
        if thread and thread is not threading.current_thread():
            thread.join(timeout=1.0)

        with self._lock:
            self._running = False
            self._thread = None

        # 恢复终端设置
        self._restore_terminal()

    def _run(self) -> None:
        """后台监听线程主循环"""
        try:
            # Unix 下设置终端为 cbreak 模式
            if os.name != "nt":
                self._setup_terminal()

            while not self._stop_event.is_set():
                key = self._read_key()
                if key:
                    self._dispatch(key)
                    continue
                time.sleep(self._poll_interval)

        finally:
            self._restore_terminal()
            with self._lock:
                self._running = False

    def _dispatch(self, key: str) -> None:
        """分发按键事件到回调"""
        with self._lock:
            # 只匹配精确的键，不做大小写合并
            # 调用者需要分别注册大小写键
            callbacks = list(self._callbacks.get(key, []))

        for callback in callbacks:
            try:
                callback()
            except Exception as exc:
                print(f"⚠️ 快捷键回调异常: {exc}")

    def _read_key(self) -> Optional[str]:
        """读取按键（跨平台）"""
        if os.name == "nt":
            return self._read_key_windows()
        return self._read_key_unix()

    def _read_key_windows(self) -> Optional[str]:
        """Windows 下读取按键"""
        if not msvcrt.kbhit():
            return None

        data = msvcrt.getch()

        # 特殊键（功能键等）以 0x00 或 0xe0 开头
        if data in (b"\x00", b"\xe0"):
            if msvcrt.kbhit():
                msvcrt.getch()  # 消费扩展码
            return None

        try:
            text = data.decode(errors="ignore")
        except Exception:
            return None

        return text or None

    def _setup_terminal(self) -> None:
        """Unix 下设置终端为 cbreak 模式"""
        if not sys.stdin.isatty():
            self._stdin_available = False
            return

        self._stdin_fd = sys.stdin.fileno()
        try:
            self._stdin_old_settings = termios.tcgetattr(self._stdin_fd)
            tty.setcbreak(self._stdin_fd)
        except Exception:
            self._stdin_available = False

    def _restore_terminal(self) -> None:
        """恢复 Unix 终端设置"""
        if os.name == "nt":
            return
        if not self._stdin_available:
            return
        if self._stdin_fd is None or self._stdin_old_settings is None:
            return

        try:
            termios.tcsetattr(
                self._stdin_fd,
                termios.TCSADRAIN,
                self._stdin_old_settings,
            )
        except Exception:
            pass  # 忽略恢复失败

    def _read_key_unix(self) -> Optional[str]:
        """Unix 下读取按键"""
        if not self._stdin_available:
            return None
        if self._stdin_fd is None:
            return None

        # 使用 select 检查是否有输入
        ready, _, _ = select.select([sys.stdin], [], [], 0)
        if not ready:
            return None

        try:
            char = sys.stdin.read(1)
        except Exception:
            return None

        return char or None
