"""公告数据模型。"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class AnnouncementCategory(str, Enum):
    """公告分类。"""

    EARNINGS_FORECAST = "业绩预告"
    EARNINGS_EXPRESS = "业绩快报"
    ANNUAL_REPORT = "年报"
    SEMI_ANNUAL_REPORT = "半年报"
    QUARTERLY_REPORT = "季报"
    EQUITY_INCENTIVE = "股权激励"
    INCREASE_HOLDING = "增持"
    DECREASE_HOLDING = "减持"
    BUYBACK = "回购"
    MAJOR_CONTRACT = "重大合同"
    RESTRUCTURING = "资产重组"
    SHAREHOLDER_MEETING = "股东大会"
    DIVIDEND = "分红"
    SUSPENSION = "停复牌"
    RISK_WARNING = "风险警示"
    OTHER = "其他"


class Announcement(BaseModel):
    """单条公告。"""

    id: str = Field(description="公告唯一 ID（来源+原始ID）")
    stock_code: str = Field(description="股票代码，如 000001")
    stock_name: str = Field(description="股票名称，如 平安银行")
    title: str = Field(description="公告标题")
    category: AnnouncementCategory = AnnouncementCategory.OTHER
    publish_time: datetime = Field(description="发布时间")
    source: str = Field(description="数据来源: cninfo / eastmoney")
    url: str = Field(description="公告原文链接")
    pdf_url: str = Field(default="", description="PDF 下载链接")
    content_text: str = Field(default="", description="公告正文（纯文本）")
    raw_meta: dict = Field(default_factory=dict, description="原始元数据")

    def __hash__(self) -> int:
        return hash(self.id)
