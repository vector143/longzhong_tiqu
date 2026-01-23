"""
客户端模块 - Cookie管理和云存储

提供外部服务客户端：
- OilChemCookiesManager: Cookie会话管理
- AsyncMemoryQiniuUploader: 异步七牛云上传器
- UploadTask: 上传任务封装
"""

from .cookies import OilChemCookiesManager
from .qiniu_uploader import UploadTask, AsyncMemoryQiniuUploader

__all__ = ["OilChemCookiesManager", "UploadTask", "AsyncMemoryQiniuUploader"]
