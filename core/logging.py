"""
增量更新日志记录器

记录爬取会话的开始、统计信息、结束和错误信息。
日志以JSON格式追加写入日志文件。
"""

import datetime
import json
from typing import List, Dict, Any, Optional

from utils.time_utils import format_publish_time


class IncrementalUpdateLogger:
    """增量更新日志记录器"""

    def __init__(self, log_file: str = "incremental_update.log"):
        self.log_file = log_file
        self.session_start_time = datetime.datetime.now()

    def log_session_start(
        self,
        keyword: str,
        days_back: Optional[int] = None,
        hours_back: Optional[int] = None,
    ) -> None:
        """记录会话开始"""
        if hours_back is not None:
            time_range_desc = f"最近{hours_back}小时"
        elif days_back is not None:
            time_range_desc = f"最近{days_back}天"
        else:
            time_range_desc = "全部数据"

        log_entry = {
            "timestamp": self.session_start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "type": "SESSION_START",
            "keyword": keyword,
            "time_range": time_range_desc,
            "message": f"开始增量爬取: {keyword} ({time_range_desc})",
        }
        self._write_log(log_entry)
        print(f"📝 {log_entry['message']}")

    def log_articles_stats(self, articles: List[Dict[str, Any]]) -> None:
        """记录文章统计信息"""
        if not articles:
            return

        publish_times = []
        for article in articles:
            publish_time = article.get("publishTime")
            if publish_time:
                formatted_time = format_publish_time(publish_time)
                if formatted_time:
                    publish_times.append(formatted_time)

        if publish_times:
            time_range_msg = f"{min(publish_times)} 至 {max(publish_times)}"
        else:
            time_range_msg = "无发布时间信息"

        log_entry = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "ARTICLES_STATS",
            "total_articles": len(articles),
            "publish_time_range": time_range_msg,
            "html_files": sum(
                1 for a in articles if a.get("upload_status", {}).get("html")
            ),
            "word_files": sum(
                1 for a in articles if a.get("upload_status", {}).get("word")
            ),
            "message": f"爬取完成: 共{len(articles)}篇文章, 发布时间范围: {time_range_msg}",
        }
        self._write_log(log_entry)
        print(f"📊 {log_entry['message']}")

    def log_session_end(self, total_articles: int, elapsed_time: float) -> None:
        """记录会话结束"""
        log_entry = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "SESSION_END",
            "total_articles": total_articles,
            "elapsed_seconds": round(elapsed_time, 2),
            "message": f"会话结束: 处理{total_articles}篇文章, 耗时{elapsed_time:.2f}秒",
        }
        self._write_log(log_entry)
        print(f"✅ {log_entry['message']}")

    def log_error(self, error_message: str) -> None:
        """记录错误信息"""
        log_entry = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "ERROR",
            "message": error_message,
        }
        self._write_log(log_entry)
        print(f"❌ 错误: {error_message}")

    def _write_log(self, log_entry: Dict[str, Any]) -> None:
        """写入日志文件"""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"⚠️ 写入日志失败: {e}")
