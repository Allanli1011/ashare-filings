"""东方财富公告数据采集。

东方财富提供的公告 API 速度更快、结构更清晰，
适合作为巨潮的补充数据源或主力数据源。
"""

from __future__ import annotations

import logging
from datetime import date, datetime

import httpx

from src.fetcher.base import BaseFetcher
from src.models.announcement import Announcement, AnnouncementCategory

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

# 东方财富公告类型编码映射
_EM_TYPE_MAP: dict[str, AnnouncementCategory] = {
    "01010503": AnnouncementCategory.EARNINGS_FORECAST,  # 业绩预告
    "01010501": AnnouncementCategory.ANNUAL_REPORT,       # 年报
    "01010505": AnnouncementCategory.EARNINGS_EXPRESS,     # 业绩快报
    "0102": AnnouncementCategory.RESTRUCTURING,            # 重大事项
    "0108": AnnouncementCategory.DIVIDEND,                 # 分红送转
}


class EastmoneyFetcher(BaseFetcher):
    """东方财富公告采集器。"""

    source_name = "eastmoney"

    def __init__(self, base_url: str = "https://np-anotice-stock.eastmoney.com/api"):
        self.base_url = base_url
        self._client = httpx.AsyncClient(headers=_HEADERS, timeout=30, follow_redirects=True)

    async def fetch_announcements(
        self,
        target_date: date | None = None,
        stock_codes: list[str] | None = None,
    ) -> list[Announcement]:
        target_date = target_date or date.today()
        date_str = target_date.strftime("%Y-%m-%d")

        url = f"{self.base_url}/security/ann"
        params = {
            "sr": -1,
            "page_size": 50,
            "page_index": 1,
            "ann_type": "A",
            "client_source": "web",
            "f_node": "0",
            "s_node": "0",
            "begin_time": date_str,
            "end_time": date_str,
        }

        if stock_codes:
            params["stock_list"] = ",".join(stock_codes)

        announcements: list[Announcement] = []
        page = 1

        while True:
            params["page_index"] = page
            try:
                resp = await self._client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
            except (httpx.HTTPError, ValueError) as e:
                logger.error("东方财富请求失败 (page=%d): %s", page, e)
                break

            result = data.get("data", {})
            items = result.get("list", [])
            if not items:
                break

            for item in items:
                ann = self._parse_item(item)
                if ann:
                    announcements.append(ann)

            total_hits = result.get("total_hits", 0)
            if page * 50 >= total_hits:
                break
            page += 1

        logger.info("东方财富采集完成: %s, 共 %d 条", date_str, len(announcements))
        return announcements

    async def fetch_content(self, announcement: Announcement) -> str:
        """东方财富公告正文提取。"""
        if not announcement.url:
            return ""

        try:
            resp = await self._client.get(announcement.url)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.error("获取公告内容失败 [%s]: %s", announcement.id, e)
            return ""

        from src.parser.html_extractor import extract_text_from_html

        return extract_text_from_html(resp.text)

    def _parse_item(self, item: dict) -> Announcement | None:
        try:
            codes = item.get("codes", [])
            if not codes:
                return None

            stock_info = codes[0]
            stock_code = stock_info.get("stock_code", "")
            stock_name = stock_info.get("short_name", "")
            title = item.get("title", "")
            ann_id = str(item.get("art_code", ""))
            notice_date = item.get("notice_date", "")

            if not stock_code or not ann_id:
                return None

            publish_time = (
                datetime.fromisoformat(notice_date) if notice_date else datetime.now()
            )

            category = self._classify(title, item.get("columns", []))

            return Announcement(
                id=f"eastmoney_{ann_id}",
                stock_code=stock_code,
                stock_name=stock_name,
                title=title,
                category=category,
                publish_time=publish_time,
                source=self.source_name,
                url=f"https://data.eastmoney.com/notices/detail/{stock_code}/{ann_id}.html",
                raw_meta=item,
            )
        except Exception as e:
            logger.warning("解析东方财富公告条目失败: %s", e)
            return None

    @staticmethod
    def _classify(title: str, columns: list) -> AnnouncementCategory:
        """根据标题关键词判断分类。"""
        keywords_map = {
            "业绩预告": AnnouncementCategory.EARNINGS_FORECAST,
            "业绩快报": AnnouncementCategory.EARNINGS_EXPRESS,
            "年度报告": AnnouncementCategory.ANNUAL_REPORT,
            "半年度报告": AnnouncementCategory.SEMI_ANNUAL_REPORT,
            "季度报告": AnnouncementCategory.QUARTERLY_REPORT,
            "股权激励": AnnouncementCategory.EQUITY_INCENTIVE,
            "增持": AnnouncementCategory.INCREASE_HOLDING,
            "减持": AnnouncementCategory.DECREASE_HOLDING,
            "回购": AnnouncementCategory.BUYBACK,
            "重大合同": AnnouncementCategory.MAJOR_CONTRACT,
            "中标": AnnouncementCategory.MAJOR_CONTRACT,
            "重组": AnnouncementCategory.RESTRUCTURING,
            "分红": AnnouncementCategory.DIVIDEND,
            "送转": AnnouncementCategory.DIVIDEND,
            "停牌": AnnouncementCategory.SUSPENSION,
            "复牌": AnnouncementCategory.SUSPENSION,
            "风险": AnnouncementCategory.RISK_WARNING,
        }
        for keyword, cat in keywords_map.items():
            if keyword in title:
                return cat
        return AnnouncementCategory.OTHER
