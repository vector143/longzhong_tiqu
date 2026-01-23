"""
通用文件命名系统

提供项目统一的文件命名规则和映射管理。
支持线程安全的并发写入。
"""

import csv
import datetime
import os
import re
import shutil
import threading
from typing import Optional, Set, Union

import pandas as pd

from utils.time_utils import format_publish_time


class UniversalNamingSystem:
    """通用命名系统 - 线程安全版本"""

    def __init__(self, project_code: str = "OIL"):
        self.project_code = project_code
        self.mapping_file = f"{project_code}_filename_mapping.csv"
        self.existing_mappings: Set[str] = self._load_existing_mappings()
        self._lock = threading.Lock()

    def generate_universal_name(
        self, original_title: str, article_id: str, file_type: str = "word"
    ) -> str:
        """生成通用文件名：项目_日期_ID.扩展名"""
        date_str = self._extract_date(original_title)
        ext = ".docx" if file_type == "word" else ".html"
        return f"{self.project_code}_{date_str}_{article_id}{ext}"

    def _extract_date(self, title: str) -> str:
        """从标题中提取日期"""
        patterns = [
            r"(\d{4})年(\d{1,2})月(\d{1,2})日",
            r"(\d{4})(\d{2})(\d{2})",
            r"(\d{4})-(\d{1,2})-(\d{1,2})",
        ]
        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                year, month, day = match.groups()
                return f"{year}{month.zfill(2)}{day.zfill(2)}"
        return datetime.datetime.now().strftime("%Y%m%d")

    def _load_existing_mappings(self) -> Set[str]:
        """加载已存在的映射关系"""
        mappings: Set[str] = set()
        if os.path.exists(self.mapping_file):
            try:
                df = pd.read_csv(self.mapping_file)
                mappings = set(df["new_filename"].tolist())
                print(f"📁 加载已有映射: {len(mappings)} 条记录")
            except Exception as e:
                print(f"⚠️ 加载映射文件失败: {e}")
        return mappings

    def load_existing_article_ids(self) -> Set[str]:
        """
        加载已存在的文章ID集合（用于增量爬取去重）

        Returns:
            已爬取的文章ID集合

        Note:
            此方法线程安全，会处理文件不存在、损坏等异常情况
        """
        with self._lock:
            if not os.path.exists(self.mapping_file):
                print("📁 映射文件不存在，将创建新文件")
                return set()

            try:
                df = pd.read_csv(self.mapping_file)

                if "article_id" not in df.columns:
                    print("⚠️ 映射文件缺少 article_id 列，将从空集合开始")
                    return set()

                # 统一转换为字符串，过滤空值
                article_ids = set(df["article_id"].dropna().astype(str).tolist())
                print(f"📁 加载已有文章ID: {len(article_ids)} 条记录")
                return article_ids

            except pd.errors.EmptyDataError:
                print("⚠️ 映射文件为空，将从空集合开始")
                return set()

            except pd.errors.ParserError as e:
                print(f"❌ 映射文件损坏: {e}")
                # 备份损坏文件
                backup_path = f"{self.mapping_file}.corrupted.{int(datetime.datetime.now().timestamp())}"
                shutil.copy(self.mapping_file, backup_path)
                print(f"📦 已备份损坏文件到: {backup_path}")
                return set()

            except Exception as e:
                print(f"⚠️ 加载文章ID失败: {e}")
                return set()

    def save_mapping(
        self,
        original_title: str,
        new_filename: str,
        article_id: str,
        file_type: str,
        upload_status: str,
        local_saved: bool = False,
        publish_time: Optional[Union[int, float, str]] = None,
    ) -> None:
        """保存文件名映射到CSV（线程安全）"""
        with self._lock:
            if new_filename in self.existing_mappings:
                print(f"⏭️ 跳过已存在的映射: {new_filename}")
                return

            # 使用统一的时间格式化函数
            formatted_publish_time = (
                format_publish_time(publish_time) if publish_time else "无发布时间"
            )

            mapping_data = {
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "original_title": original_title,
                "new_filename": new_filename,
                "article_id": article_id,
                "file_type": file_type,
                "upload_status": upload_status,
                "local_saved": "是" if local_saved else "否",
                "publish_time": formatted_publish_time,
            }

            file_exists = os.path.exists(self.mapping_file)
            with open(self.mapping_file, "a", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=mapping_data.keys())
                if not file_exists:
                    writer.writeheader()
                writer.writerow(mapping_data)

            self.existing_mappings.add(new_filename)
            print(f"💾 保存映射: {new_filename}")
