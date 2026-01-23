"""
七牛云异步上传器 - 提供内存数据的异步批量上传功能
"""

import datetime
import queue
import threading
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

from qiniu import Auth, put_data


class UploadTask:
    """上传任务封装"""

    def __init__(
        self,
        file_data: bytes,
        filename: str,
        file_type: str,
        article_info: Optional[Dict[str, Any]] = None,
    ):
        self.file_data = file_data
        self.filename = filename
        self.file_type = file_type
        self.article_info = article_info or {}
        self.create_time = datetime.datetime.now()
        self.retry_count = 0

    def __str__(self) -> str:
        return (
            f"UploadTask({self.filename}, {self.file_type}, size:{len(self.file_data)})"
        )


class AsyncMemoryQiniuUploader:
    """异步内存七牛云上传器"""

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        prefix: str = "crawled_articles",
        max_upload_workers: int = 3,
    ):
        self.auth = Auth(access_key, secret_key)
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.upload_queue: queue.Queue = queue.Queue()
        self.uploaded_files: List[Dict[str, Any]] = []
        self.failed_uploads: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._stats_lock = threading.Lock()
        self.stats: Dict[str, Any] = {
            "total_submitted": 0,
            "total_success": 0,
            "total_failed": 0,
            "current_queue_size": 0,
            "upload_speed": 0,
        }
        self.max_upload_workers = max_upload_workers
        self.upload_workers: List[threading.Thread] = []
        self.is_running = False
        print(f"✅ 异步上传器初始化: {max_upload_workers}个上传线程")

    def start_upload_workers(self) -> None:
        """启动上传工作线程"""
        if self.is_running:
            return
        self.is_running = True
        for i in range(self.max_upload_workers):
            worker = threading.Thread(
                target=self._upload_worker, name=f"UploadWorker-{i + 1}", daemon=True
            )
            worker.start()
            self.upload_workers.append(worker)
        print(f"🚀 启动 {self.max_upload_workers} 个上传线程")

    def stop_upload_workers(self) -> None:
        """停止上传工作线程"""
        self.is_running = False
        for _ in range(self.max_upload_workers):
            self.upload_queue.put(None)
        for worker in self.upload_workers:
            worker.join(timeout=5)
        self.upload_workers.clear()
        print("🛑 上传线程已停止")

    def submit_upload_task(
        self,
        file_data: bytes,
        filename: str,
        file_type: str,
        article_info: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """提交上传任务到队列"""
        task = UploadTask(file_data, filename, file_type, article_info)
        with self._stats_lock:
            self.stats["total_submitted"] += 1
            self.stats["current_queue_size"] = self.upload_queue.qsize()
        self.upload_queue.put(task)
        print(f"📤 提交上传任务: {filename} (队列大小: {self.upload_queue.qsize()})")
        return True

    def _upload_worker(self) -> None:
        """上传工作线程"""
        thread_name = threading.current_thread().name
        while self.is_running:
            try:
                task = self.upload_queue.get(timeout=1)
                if task is None:
                    self.upload_queue.task_done()
                    break
                print(f"🧵 {thread_name} 处理上传: {task.filename}")
                success = self._execute_upload(task)
                with self._stats_lock:
                    if success:
                        self.stats["total_success"] += 1
                    else:
                        self.stats["total_failed"] += 1
                    self.stats["current_queue_size"] = self.upload_queue.qsize()
                self.upload_queue.task_done()
                time.sleep(0.1)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ 上传工作线程异常: {e}")

    def _execute_upload(self, task: UploadTask) -> bool:
        """执行实际上传操作"""
        try:
            qiniu_key = self._build_safe_key(task.filename, task.file_type)
            print(
                f"📤 {threading.current_thread().name} 上传: {task.filename} -> {qiniu_key}"
            )
            print(
                f"   数据大小: {len(task.file_data)} bytes, 重试次数: {task.retry_count}"
            )
            token = self.auth.upload_token(self.bucket_name, qiniu_key, 3600)
            start_time = time.time()
            ret, info = put_data(token, qiniu_key, task.file_data)
            upload_time = time.time() - start_time
            print(f"📡 上传响应状态码: {info.status_code}, 耗时: {upload_time:.2f}s")

            if info.status_code == 200:
                print(f"✅ 上传成功: {qiniu_key}")
                with self._lock:
                    self.uploaded_files.append(
                        {
                            "filename": task.filename,
                            "qiniu_key": qiniu_key,
                            "file_type": task.file_type,
                            "upload_time": upload_time,
                            "article_info": task.article_info,
                        }
                    )
                return True
            else:
                print(f"❌ 上传失败 {info.status_code}: {qiniu_key}")
                return self._handle_retry(task, f"状态码: {info.status_code}")
        except Exception as e:
            print(f"💥 上传异常: {e}")
            return self._handle_retry(task, str(e))

    def _handle_retry(self, task: UploadTask, error: str) -> bool:
        """处理重试逻辑"""
        if task.retry_count < 2:
            task.retry_count += 1
            print(f"🔄 重试上传 ({task.retry_count}/2): {task.filename}")
            self.upload_queue.put(task)
        else:
            with self._lock:
                self.failed_uploads.append(
                    {
                        "filename": task.filename,
                        "error": error,
                        "retry_count": task.retry_count,
                    }
                )
        return False

    def _build_safe_key(self, filename: str, file_type: str) -> str:
        """构建安全的存储路径"""
        subdir = "html" if file_type == "html" else "word"
        return f"{self.prefix}/{subdir}/{filename}".replace("\\", "/")

    def wait_for_completion(self, timeout: int = 300) -> None:
        """等待所有上传任务完成"""
        print(f"⏳ 等待上传队列清空... (当前队列: {self.upload_queue.qsize()})")
        start_time = time.time()
        while not self.upload_queue.empty():
            if time.time() - start_time > timeout:
                print(f"⚠️ 上传等待超时，剩余 {self.upload_queue.qsize()} 个任务")
                break
            remaining = self.upload_queue.qsize()
            if remaining > 0:
                print(f"📊 上传进度: 剩余 {remaining} 个任务")
            time.sleep(2)
        self.upload_queue.join()
        print("✅ 所有上传任务已完成")

    def get_upload_stats(self) -> Dict[str, Any]:
        """获取上传统计"""
        with self._stats_lock:
            stats = self.stats.copy()
            stats["uploaded_files_count"] = len(self.uploaded_files)
            stats["failed_uploads_count"] = len(self.failed_uploads)
            stats["queue_size"] = self.upload_queue.qsize()
        return stats

    def get_detailed_stats(self) -> Dict[str, Any]:
        """获取详细统计"""
        stats = self.get_upload_stats()
        file_type_stats: Dict[str, int] = defaultdict(int)
        for item in self.uploaded_files:
            file_type_stats[item["file_type"]] += 1
        stats["file_type_breakdown"] = dict(file_type_stats)
        return stats
