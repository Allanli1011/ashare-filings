"""数据采集基类。"""

from __future__ import annotations

import abc
from datetime import date

from src.models.announcement import Announcement


class BaseFetcher(abc.ABC):
    """公告数据源抽象基类。"""

    source_name: str = ""

    @abc.abstractmethod
    async def fetch_announcements(
        self,
        target_date: date | None = None,
        stock_codes: list[str] | None = None,
    ) -> list[Announcement]:
        """获取指定日期的公告列表。

        Args:
            target_date: 目标日期，默认今天。
            stock_codes: 限定股票代码列表，None 表示全市场。

        Returns:
            公告列表。
        """

    @abc.abstractmethod
    async def fetch_content(self, announcement: Announcement) -> str:
        """获取公告正文内容。

        Args:
            announcement: 公告对象。

        Returns:
            纯文本正文内容。
        """
