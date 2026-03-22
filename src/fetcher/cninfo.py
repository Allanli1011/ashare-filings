"""巨潮资讯网数据采集。

巨潮资讯网 (cninfo.com.cn) 是中国证监会指定的信息披露网站，
提供最权威、最完整的上市公司公告数据。
"""

from __future__ import annotations

import logging
from datetime import date, datetime

import httpx

from src.fetcher.base import BaseFetcher
from src.models.announcement import Announcement, AnnouncementCategory

logger = logging.getLogger(__name__)

# 巨潮公告类型到内部分类的映射
_CNINFO_CATEGORY_MAP: dict[str, AnnouncementCategory] = {
    "业绩预告": AnnouncementCategory.EARNINGS_FORECAST,
    "业绩快报": AnnouncementCategory.EARNINGS_EXPRESS,
    "年度报告": AnnouncementCategory.ANNUAL_REPORT,
    "半年度报告": AnnouncementCategory.SEMI_ANNUAL_REPORT,
    "第一季度报告": AnnouncementCategory.QUARTERLY_REPORT,
    "第三季度报告": AnnouncementCategory.QUARTERLY_REPORT,
    "股权激励": AnnouncementCategory.EQUITY_INCENTIVE,
    "股份回购": AnnouncementCategory.BUYBACK,
    "资产重组": AnnouncementCategory.RESTRUCTURING,
    "分配方案": AnnouncementCategory.DIVIDEND,
    "风险提示": AnnouncementCategory.RISK_WARNING,
}

# 巨潮资讯网请求头，模拟浏览器避免被拦截
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "http://www.cninfo.com.cn/new/disclosure",
}


class CninfoFetcher(BaseFetcher):
    """巨潮资讯网公告采集器。"""

    source_name = "cninfo"

    def __init__(self, base_url: str = "http://www.cninfo.com.cn/new/disclosure"):
        self.base_url = base_url
        self._client = httpx.AsyncClient(headers=_HEADERS, timeout=30, follow_redirects=True)

    async def fetch_announcements(
        self,
        target_date: date | None = None,
        stock_codes: list[str] | None = None,
    ) -> list[Announcement]:
        target_date = target_date or date.today()
        date_str = target_date.strftime("%Y-%m-%d")

        # 巨潮资讯网公告列表查询接口
        url = f"{self.base_url}/cn/search/announceSearch"
        payload = {
            "pageNum": 1,
            "pageSize": 50,
            "column": "szse",  # 深交所，后续可扩展上交所
            "tabName": "fulltext",
            "seDate": f"{date_str}~{date_str}",
            "isHLtitle": "true",
        }

        if stock_codes:
            payload["stock"] = ",".join(stock_codes)

        announcements: list[Announcement] = []
        page = 1

        while True:
            payload["pageNum"] = page
            try:
                resp = await self._client.post(url, data=payload)
                resp.raise_for_status()
                data = resp.json()
            except (httpx.HTTPError, ValueError) as e:
                logger.error("巨潮资讯网请求失败 (page=%d): %s", page, e)
                break

            items = data.get("announcements", [])
            if not items:
                break

            for item in items:
                ann = self._parse_item(item)
                if ann:
                    announcements.append(ann)

            total_pages = data.get("totalpages", 1)
            if page >= total_pages:
                break
            page += 1

        logger.info("巨潮资讯网采集完成: %s, 共 %d 条", date_str, len(announcements))
        return announcements

    async def fetch_content(self, announcement: Announcement) -> str:
        """下载公告 PDF 并提取文本。"""
        if not announcement.pdf_url:
            return ""

        try:
            resp = await self._client.get(announcement.pdf_url)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.error("下载公告 PDF 失败 [%s]: %s", announcement.id, e)
            return ""

        # PDF 文本提取（延迟导入，仅在需要时加载）
        try:
            from src.parser.pdf_extractor import extract_text_from_pdf_bytes

            return extract_text_from_pdf_bytes(resp.content)
        except ImportError:
            logger.warning("PDF 解析模块不可用，跳过内容提取")
            return ""

    def _parse_item(self, item: dict) -> Announcement | None:
        """将巨潮原始 JSON 条目转为 Announcement。"""
        try:
            sec_code = item.get("secCode", "")
            sec_name = item.get("secName", "")
            title = item.get("announcementTitle", "").replace("<em>", "").replace("</em>", "")
            ann_id = item.get("announcementId", "")
            ann_time = item.get("announcementTime", 0)

            if not sec_code or not ann_id:
                return None

            # 巨潮的时间戳是毫秒级
            publish_time = datetime.fromtimestamp(ann_time / 1000) if ann_time else datetime.now()

            category = self._classify(title, item.get("announcementType", ""))

            pdf_url = ""
            if ann_id:
                pdf_url = f"http://static.cninfo.com.cn/finalpage/2024-01-01/{ann_id}.PDF"

            return Announcement(
                id=f"cninfo_{ann_id}",
                stock_code=sec_code,
                stock_name=sec_name,
                title=title,
                category=category,
                publish_time=publish_time,
                source=self.source_name,
                url=f"http://www.cninfo.com.cn/new/disclosure/detail?annoId={ann_id}",
                pdf_url=pdf_url,
                raw_meta=item,
            )
        except Exception as e:
            logger.warning("解析巨潮公告条目失败: %s", e)
            return None

    @staticmethod
    def _classify(title: str, ann_type: str) -> AnnouncementCategory:
        """根据标题和类型字段推断公告分类。"""
        combined = f"{title} {ann_type}"
        for keyword, cat in _CNINFO_CATEGORY_MAP.items():
            if keyword in combined:
                return cat

        # 通过标题关键词补充判断
        if any(w in title for w in ("增持", "增加持股")):
            return AnnouncementCategory.INCREASE_HOLDING
        if any(w in title for w in ("减持", "减少持股")):
            return AnnouncementCategory.DECREASE_HOLDING
        if "重大合同" in title or "中标" in title:
            return AnnouncementCategory.MAJOR_CONTRACT
        if "停牌" in title or "复牌" in title:
            return AnnouncementCategory.SUSPENSION

        return AnnouncementCategory.OTHER
