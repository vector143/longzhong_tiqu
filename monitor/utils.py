"""
监控工具函数

包含：
- 指数退避重试装饰器
- 令牌桶限流器
- 线程安全集合
- PID 文件管理器
- 磁盘空间检查
"""

from __future__ import annotations

import atexit
import functools
import os
import shutil
import threading
import time
from collections.abc import Iterator, MutableSet
from pathlib import Path
from typing import Callable, Iterable, Optional, Set, Tuple, Type, TypeVar, Union

T = TypeVar("T")

# 默认 PID 文件路径：项目根目录下的 .monitor.pid
DEFAULT_PID_FILE = Path(__file__).resolve().parents[1] / ".monitor.pid"


class ThreadSafeSet(MutableSet[str]):
    """
    线程安全的字符串集合

    封装标准 set，提供线程安全的增删查操作。
    迭代时返回快照，避免并发修改异常。

    Example:
        ids = ThreadSafeSet(["a", "b", "c"])
        ids.add("d")
        if "a" in ids:
            print("found")
    """

    def __init__(self, iterable: Optional[Iterable[str]] = None) -> None:
        """
        初始化线程安全集合

        Args:
            iterable: 初始元素，可选
        """
        self._set: Set[str] = set(iterable) if iterable else set()
        self._lock = threading.RLock()

    def __contains__(self, value: object) -> bool:
        """检查元素是否存在"""
        with self._lock:
            return value in self._set

    def __len__(self) -> int:
        """获取集合大小"""
        with self._lock:
            return len(self._set)

    def __iter__(self) -> Iterator[str]:
        """迭代集合（返回快照）"""
        with self._lock:
            snapshot = tuple(self._set)
        return iter(snapshot)

    def add(self, value: str) -> None:
        """添加元素"""
        with self._lock:
            self._set.add(value)

    def discard(self, value: str) -> None:
        """移除元素（如果存在）"""
        with self._lock:
            self._set.discard(value)

    def update(self, *others: Iterable[str]) -> None:
        """批量添加元素"""
        with self._lock:
            for other in others:
                self._set.update(other)

    def snapshot(self) -> Set[str]:
        """获取当前集合的快照副本"""
        with self._lock:
            return set(self._set)

    def clear(self) -> None:
        """清空集合"""
        with self._lock:
            self._set.clear()


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 5.0,
    max_delay: float = 60.0,
    retry_exceptions: Tuple[Type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    指数退避重试装饰器

    Args:
        max_retries: 最大重试次数（不含首次调用）
        base_delay: 初始延迟秒数
        max_delay: 最大延迟秒数上限
        retry_exceptions: 可重试的异常类型元组

    Returns:
        装饰后的函数

    Example:
        @retry_with_backoff(max_retries=3, base_delay=1.0)
        def unstable_request():
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            attempt = 0
            delay = base_delay

            while True:
                try:
                    return func(*args, **kwargs)
                except retry_exceptions as e:
                    if attempt >= max_retries:
                        print(f"❌ 重试 {max_retries} 次后仍失败: {e}")
                        raise

                    attempt += 1
                    print(
                        f"⚠️ 第 {attempt}/{max_retries} 次重试，{delay:.1f}秒后继续: {e}"
                    )
                    time.sleep(delay)
                    delay = min(delay * 2, max_delay)

        return wrapper

    return decorator


class TokenBucketRateLimiter:
    """
    令牌桶限流器（线程安全）

    通过令牌桶算法控制请求速率，支持：
    - 每分钟最大请求数限制
    - 最小请求间隔控制

    Attributes:
        requests_per_minute: 每分钟允许的请求数
        min_interval: 两次请求之间的最小间隔（秒）
    """

    def __init__(
        self, requests_per_minute: int = 30, min_interval: float = 0.5
    ) -> None:
        """
        初始化限流器

        Args:
            requests_per_minute: 每分钟请求数，必须为正整数
            min_interval: 最小请求间隔（秒），必须非负

        Raises:
            ValueError: 参数不合法时抛出
        """
        if requests_per_minute <= 0:
            raise ValueError("requests_per_minute 必须为正整数")
        if min_interval < 0:
            raise ValueError("min_interval 必须非负")

        self._capacity = float(requests_per_minute)
        self._tokens = self._capacity
        self._fill_rate = self._capacity / 60.0  # 每秒补充的令牌数
        self._min_interval = float(min_interval)
        self._lock = threading.Lock()
        self._last_refill = time.monotonic()
        self._last_grant: Optional[float] = None

    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        获取一个令牌

        Args:
            blocking: 是否阻塞等待
            timeout: 阻塞超时时间（秒），None 表示无限等待

        Returns:
            是否成功获取令牌
        """
        start_time = time.monotonic()

        while True:
            if self._try_acquire():
                return True

            if not blocking:
                return False

            # 检查超时
            if timeout is not None:
                elapsed = time.monotonic() - start_time
                if elapsed >= timeout:
                    return False

            # 短暂等待后重试
            time.sleep(0.05)

    def _try_acquire(self) -> bool:
        """尝试获取一个令牌（非阻塞）"""
        now = time.monotonic()

        with self._lock:
            self._refill(now)

            # 检查最小间隔
            if self._min_interval > 0 and self._last_grant is not None:
                if now - self._last_grant < self._min_interval:
                    return False

            # 检查令牌是否充足
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                self._last_grant = now
                return True

            return False

    def _refill(self, now: float) -> None:
        """补充令牌"""
        elapsed = now - self._last_refill
        if elapsed <= 0:
            return

        self._tokens = min(self._capacity, self._tokens + elapsed * self._fill_rate)
        self._last_refill = now

    def get_available_tokens(self) -> float:
        """获取当前可用令牌数"""
        now = time.monotonic()
        with self._lock:
            self._refill(now)
            return self._tokens


class PidFileManager:
    """
    PID 文件管理器

    用于防止监控进程重复启动：
    - 创建 PID 文件记录当前进程
    - 检测已有进程是否存活
    - 进程退出时自动清理

    支持上下文管理器用法：
        with PidFileManager() as pid_manager:
            # 运行监控逻辑
            ...
    """

    def __init__(self, pid_file: Optional[Union[str, Path]] = None) -> None:
        """
        初始化 PID 文件管理器

        Args:
            pid_file: PID 文件路径，默认为项目根目录下的 .monitor.pid
        """
        self._pid_file = Path(pid_file) if pid_file is not None else DEFAULT_PID_FILE
        self._pid: Optional[int] = None
        self._lock = threading.Lock()
        self._cleanup_registered = False

    def __enter__(self) -> "PidFileManager":
        self.create()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup()

    def create(self) -> None:
        """
        创建 PID 文件

        如果已有存活进程，抛出 RuntimeError。
        如果存在过期 PID 文件（进程已死），自动清理后创建新文件。

        Raises:
            RuntimeError: 已有监控进程在运行
        """
        with self._lock:
            if self._pid_file.exists():
                existing_pid = self._read_pid()

                if existing_pid is not None and self._is_process_alive(existing_pid):
                    raise RuntimeError(
                        f"监控进程已在运行 (PID: {existing_pid})，"
                        f"如确认无运行进程，请删除 {self._pid_file}"
                    )

                # 清理过期 PID 文件
                print(f"🧹 清理过期 PID 文件: {self._pid_file}")
                self._safe_unlink()

            # 写入当前进程 PID
            self._pid = os.getpid()
            self._pid_file.write_text(str(self._pid), encoding="utf-8")
            print(f"📝 创建 PID 文件: {self._pid_file} (PID: {self._pid})")

            # 注册退出清理（仅注册一次）
            if not self._cleanup_registered:
                atexit.register(self.cleanup)
                self._cleanup_registered = True

    def cleanup(self) -> None:
        """清理 PID 文件（仅清理当前进程创建的）"""
        with self._lock:
            if not self._pid_file.exists():
                return

            existing_pid = self._read_pid()

            # 只清理自己创建的 PID 文件
            if existing_pid is None or existing_pid == os.getpid():
                self._safe_unlink()
                print(f"🧹 已清理 PID 文件: {self._pid_file}")

            self._pid = None

    def force_cleanup(self) -> None:
        """
        强制清理 PID 文件（忽略进程存活状态）

        用于 --force 参数场景，无论 PID 文件记录的进程是否存活都会删除。
        """
        with self._lock:
            if not self._pid_file.exists():
                return

            self._safe_unlink()
            self._pid = None
            print(f"🧹 已强制清理 PID 文件: {self._pid_file}")

    def is_running(self) -> bool:
        """
        检查是否有监控进程在运行

        Returns:
            True 表示有进程在运行
        """
        if not self._pid_file.exists():
            return False

        existing_pid = self._read_pid()
        if existing_pid is None:
            return False

        return self._is_process_alive(existing_pid)

    def is_stale(self) -> bool:
        """
        检查 PID 文件是否过期（进程已死但文件残留）

        Returns:
            True 表示 PID 文件过期
        """
        if not self._pid_file.exists():
            return False

        existing_pid = self._read_pid()
        if existing_pid is None:
            return True  # 文件内容无效视为过期

        return not self._is_process_alive(existing_pid)

    def get_running_pid(self) -> Optional[int]:
        """获取正在运行的进程 PID，如无则返回 None"""
        if not self._pid_file.exists():
            return None

        existing_pid = self._read_pid()
        if existing_pid is None:
            return None

        if self._is_process_alive(existing_pid):
            return existing_pid

        return None

    def _read_pid(self) -> Optional[int]:
        """读取 PID 文件内容"""
        try:
            content = self._pid_file.read_text(encoding="utf-8").strip()
        except OSError:
            return None

        if not content:
            return None

        try:
            return int(content)
        except ValueError:
            return None

    @staticmethod
    def _is_process_alive(pid: int) -> bool:
        """检查进程是否存活（跨平台）"""
        if pid <= 0:
            return False

        # L6: Windows 平台使用 Win32 API
        if os.name == "nt":
            try:
                import ctypes
                from ctypes import wintypes

                PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                STILL_ACTIVE = 259

                handle = ctypes.windll.kernel32.OpenProcess(
                    PROCESS_QUERY_LIMITED_INFORMATION,
                    False,
                    pid,
                )
                if not handle:
                    return False

                try:
                    exit_code = wintypes.DWORD()
                    if not ctypes.windll.kernel32.GetExitCodeProcess(
                        handle,
                        ctypes.byref(exit_code),
                    ):
                        return False
                    return exit_code.value == STILL_ACTIVE
                finally:
                    ctypes.windll.kernel32.CloseHandle(handle)
            except Exception:
                # 如果 ctypes 调用失败，保守返回 False
                return False

        # Unix/Linux/macOS: 使用信号 0 检测
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            # 进程存在但无权限发送信号
            return True
        except OSError:
            return False

        return True

    def _safe_unlink(self) -> None:
        """安全删除 PID 文件"""
        try:
            self._pid_file.unlink()
        except FileNotFoundError:
            pass


def check_disk_space(
    path: Union[str, Path] = ".", threshold_mb: float = 100.0
) -> Tuple[bool, float]:
    """
    检查磁盘空间是否充足

    Args:
        path: 要检查的路径
        threshold_mb: 最小空间阈值（MB）

    Returns:
        (是否满足阈值, 剩余空间MB)

    Example:
        ok, free_mb = check_disk_space(".", threshold_mb=100)
        if not ok:
            print(f"磁盘空间不足！剩余: {free_mb:.1f}MB")
    """
    try:
        usage = shutil.disk_usage(path)
        free_mb = usage.free / (1024 * 1024)
        return free_mb >= threshold_mb, free_mb
    except OSError as e:
        print(f"⚠️ 检查磁盘空间失败: {e}")
        # 无法检查时假设空间充足
        return True, float("inf")
