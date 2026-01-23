"""
配置设置模块

集中管理所有配置项，支持环境变量覆盖。
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# 尝试加载 .env 文件（如果 python-dotenv 可用）
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


@dataclass
class QiniuConfig:
    """七牛云配置"""

    access_key: str = ""
    secret_key: str = ""
    bucket_name: str = ""
    prefix: str = "crawled_articles"
    base_url: str = ""

    @property
    def is_configured(self) -> bool:
        """检查七牛云是否已配置"""
        return bool(self.access_key and self.secret_key and self.bucket_name)

    def to_dict(self) -> Dict[str, str]:
        """转换为字典格式（兼容旧接口）"""
        return {
            "access_key": self.access_key,
            "secret_key": self.secret_key,
            "bucket_name": self.bucket_name,
            "prefix": self.prefix,
            "base_url": self.base_url,
        }


@dataclass
class CrawlerConfig:
    """爬虫配置"""

    cookies_file: str = "cookies_tang.json"
    base_dir: str = "articles"
    project_code: str = "OIL"
    log_file: str = "incremental_update.log"
    default_pages: int = 10
    default_delay: float = 0.3
    max_crawl_workers: int = 5
    max_upload_workers: int = 3


@dataclass
class OutputConfig:
    """输出配置"""

    save_locally: bool = False
    upload_to_qiniu: bool = True
    default_formats: List[str] = field(default_factory=lambda: ["html", "word"])


@dataclass
class CleanedConfig:
    """
    Cleaned 格式输出配置

    用于将资讯 JSON 转换为 Finreport cleaned 标准格式。
    """

    enable: bool = True  # 是否启用转换
    output_dir: str = "output/report/cleaned"  # 输出目录
    on_duplicate: str = "skip"  # 重复处理: skip/overwrite/new_version
    filename_max_length: int = 180  # 文件名最大长度


@dataclass
class MonitorConfig:
    """监控配置"""

    # 轮询设置
    poll_interval_minutes: int = 10  # 轮询间隔(分钟)
    max_pages_per_poll: int = 3  # 每次轮询最大页数
    early_stop_threshold: int = 10  # 连续旧文章数触发提前停止
    default_keyword: str = "原油"  # 默认搜索关键词

    # UI 设置
    ui_refresh_interval: float = 1.0  # UI刷新频率(秒)
    recent_articles_limit: int = 20  # 最近文章显示数量
    poll_history_limit: int = 10  # 轮询历史保留数量
    interactive: bool = True  # 是否启用交互模式

    # 会话管理
    validate_session_before_poll: bool = True  # 每次轮询前验证会话

    # 重试设置
    max_retries: int = 3  # 最大重试次数
    retry_base_delay: float = 5.0  # 重试基础延迟(秒)

    # 速率限制
    requests_per_minute: int = 30  # 每分钟最大请求数
    min_request_interval: float = 0.5  # 最小请求间隔(秒)

    # 日志设置
    log_level: str = "INFO"  # 日志级别
    log_to_file: bool = False  # 是否输出到文件
    log_file_path: str = "monitor.log"  # 日志文件路径

    # 磁盘检查
    min_disk_space_mb: int = 100  # 最小磁盘空间(MB)


@dataclass
class Settings:
    """
    项目统一配置类

    支持通过环境变量覆盖配置项。
    环境变量命名规则：大写下划线格式。
    """

    qiniu: QiniuConfig = field(default_factory=QiniuConfig)
    crawler: CrawlerConfig = field(default_factory=CrawlerConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    cleaned: CleanedConfig = field(default_factory=CleanedConfig)
    monitor: MonitorConfig = field(default_factory=MonitorConfig)

    def __post_init__(self):
        """从环境变量加载配置"""
        self._load_from_env()

    def _load_from_env(self) -> None:
        """从环境变量加载配置"""
        # 七牛云配置（使用安全解析，忽略空值）
        self.qiniu.access_key = self._parse_str_env(
            "QINIU_ACCESS_KEY", self.qiniu.access_key
        )
        self.qiniu.secret_key = self._parse_str_env(
            "QINIU_SECRET_KEY", self.qiniu.secret_key
        )
        self.qiniu.bucket_name = self._parse_str_env(
            "QINIU_BUCKET_NAME", self.qiniu.bucket_name
        )
        self.qiniu.prefix = self._parse_str_env("QINIU_PREFIX", self.qiniu.prefix)
        self.qiniu.base_url = self._parse_str_env("QINIU_BASE_URL", self.qiniu.base_url)

        # 爬虫配置（字符串型使用安全解析）
        self.crawler.cookies_file = self._parse_str_env(
            "COOKIES_FILE", self.crawler.cookies_file
        )
        self.crawler.base_dir = self._parse_str_env(
            "ARTICLES_BASE_DIR", self.crawler.base_dir
        )
        self.crawler.project_code = self._parse_str_env(
            "PROJECT_CODE", self.crawler.project_code
        )
        self.crawler.log_file = self._parse_str_env("LOG_FILE", self.crawler.log_file)

        # 数值型环境变量（带容错）
        self.crawler.default_pages = self._parse_int_env(
            "DEFAULT_PAGES", self.crawler.default_pages
        )
        self.crawler.default_delay = self._parse_float_env(
            "DEFAULT_DELAY", self.crawler.default_delay
        )
        self.crawler.max_crawl_workers = self._parse_int_env(
            "MAX_CRAWL_WORKERS", self.crawler.max_crawl_workers
        )
        self.crawler.max_upload_workers = self._parse_int_env(
            "MAX_UPLOAD_WORKERS", self.crawler.max_upload_workers
        )

        # 输出配置
        save_local_env = os.getenv("SAVE_LOCALLY", "").lower()
        if save_local_env:
            self.output.save_locally = save_local_env in ("true", "1", "yes")

        upload_qiniu_env = os.getenv("UPLOAD_TO_QINIU", "").lower()
        if upload_qiniu_env:
            self.output.upload_to_qiniu = upload_qiniu_env in ("true", "1", "yes")

        output_formats_env = os.getenv("OUTPUT_FORMATS", "")
        if output_formats_env:
            self.output.default_formats = [
                f.strip() for f in output_formats_env.split(",")
            ]

        # Cleaned 输出配置
        cleaned_enable_env = os.getenv("CLEANED_ENABLE", "").lower()
        if cleaned_enable_env:
            self.cleaned.enable = cleaned_enable_env in ("true", "1", "yes")

        self.cleaned.output_dir = self._parse_str_env(
            "CLEANED_OUTPUT_DIR", self.cleaned.output_dir
        )

        cleaned_on_duplicate = os.getenv("CLEANED_ON_DUPLICATE", "").strip().lower()
        if cleaned_on_duplicate:
            if cleaned_on_duplicate in ("skip", "overwrite", "new_version"):
                self.cleaned.on_duplicate = cleaned_on_duplicate
            else:
                print(
                    f"⚠️ 环境变量 CLEANED_ON_DUPLICATE 值非法: '{cleaned_on_duplicate}'，"
                    f"使用默认值 {self.cleaned.on_duplicate}"
                )

        # 监控配置
        self.monitor.poll_interval_minutes = self._parse_int_env(
            "MONITOR_POLL_INTERVAL", self.monitor.poll_interval_minutes
        )
        self.monitor.max_pages_per_poll = self._parse_int_env(
            "MONITOR_MAX_PAGES", self.monitor.max_pages_per_poll
        )
        self.monitor.early_stop_threshold = self._parse_int_env(
            "MONITOR_EARLY_STOP", self.monitor.early_stop_threshold
        )
        self.monitor.default_keyword = self._parse_str_env(
            "MONITOR_KEYWORD", self.monitor.default_keyword
        )
        self.monitor.max_retries = self._parse_int_env(
            "MONITOR_MAX_RETRIES", self.monitor.max_retries
        )
        self.monitor.log_level = self._parse_str_env(
            "MONITOR_LOG_LEVEL", self.monitor.log_level
        )

        interactive_env = os.getenv("MONITOR_INTERACTIVE", "").lower()
        if interactive_env:
            self.monitor.interactive = interactive_env in ("true", "1", "yes")

    @staticmethod
    def _parse_str_env(key: str, default: str) -> str:
        """
        安全解析字符串型环境变量

        忽略空值和纯空白值，返回默认值。
        """
        value = os.getenv(key)
        if value is None:
            return default
        value = value.strip()
        return value if value else default

    @staticmethod
    def _parse_int_env(key: str, default: int) -> int:
        """安全解析整数型环境变量"""
        value = os.getenv(key)
        if not value:
            return default
        try:
            return int(value)
        except ValueError:
            print(f"⚠️ 环境变量 {key} 值非法: '{value}'，使用默认值 {default}")
            return default

    @staticmethod
    def _parse_float_env(key: str, default: float) -> float:
        """安全解析浮点型环境变量"""
        value = os.getenv(key)
        if not value:
            return default
        try:
            return float(value)
        except ValueError:
            print(f"⚠️ 环境变量 {key} 值非法: '{value}'，使用默认值 {default}")
            return default

    def get_qiniu_config(self) -> Optional[Dict[str, str]]:
        """获取七牛云配置字典（兼容旧接口）"""
        if self.qiniu.is_configured:
            return self.qiniu.to_dict()
        return None


# 全局配置单例
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """获取配置单例"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """重新加载配置"""
    global _settings
    _settings = Settings()
    return _settings
