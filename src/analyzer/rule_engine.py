"""基于规则的公告分析引擎。

对大部分常见公告类型，用确定性规则即可给出合理判断，
不需要消耗 LLM token。LLM 仅用于复杂/模糊公告的深度分析。
"""

from __future__ import annotations

import logging
import re

from src.models.announcement import Announcement, AnnouncementCategory
from src.models.signal import Signal, SignalAction, SignalStrength

logger = logging.getLogger(__name__)


class RuleEngine:
    """规则引擎：基于公告类型和关键词生成投资信号。"""

    def analyze(self, announcement: Announcement) -> Signal | None:
        """分析单条公告，返回信号或 None（表示不产生信号）。"""
        handlers = {
            AnnouncementCategory.EARNINGS_FORECAST: self._handle_earnings_forecast,
            AnnouncementCategory.EARNINGS_EXPRESS: self._handle_earnings_express,
            AnnouncementCategory.INCREASE_HOLDING: self._handle_increase_holding,
            AnnouncementCategory.DECREASE_HOLDING: self._handle_decrease_holding,
            AnnouncementCategory.BUYBACK: self._handle_buyback,
            AnnouncementCategory.EQUITY_INCENTIVE: self._handle_equity_incentive,
            AnnouncementCategory.MAJOR_CONTRACT: self._handle_major_contract,
            AnnouncementCategory.RISK_WARNING: self._handle_risk_warning,
            AnnouncementCategory.DIVIDEND: self._handle_dividend,
            AnnouncementCategory.RESTRUCTURING: self._handle_restructuring,
        }

        handler = handlers.get(announcement.category)
        if handler:
            return handler(announcement)
        return None

    def _handle_earnings_forecast(self, ann: Announcement) -> Signal:
        title = ann.title
        content = ann.content_text or title

        # 提取增长/下降百分比
        pct_match = re.search(r"(?:增长|增加|上升)\s*(\d+(?:\.\d+)?)\s*%", content)
        decline_match = re.search(r"(?:下降|减少|下滑)\s*(\d+(?:\.\d+)?)\s*%", content)

        if any(w in title for w in ("预增", "扭亏", "大幅增长")):
            pct = float(pct_match.group(1)) if pct_match else 0
            strength = SignalStrength.HIGH if pct > 50 else SignalStrength.MEDIUM
            return self._make_signal(ann, SignalAction.BUY, strength, f"业绩预增{pct}%")

        if any(w in title for w in ("预减", "预亏", "首亏", "续亏", "大幅下降")):
            pct = float(decline_match.group(1)) if decline_match else 0
            strength = SignalStrength.HIGH if pct > 50 else SignalStrength.MEDIUM
            return self._make_signal(ann, SignalAction.SELL, strength, f"业绩预减{pct}%")

        return self._make_signal(ann, SignalAction.WATCH, SignalStrength.LOW, "业绩预告待定")

    def _handle_earnings_express(self, ann: Announcement) -> Signal:
        title = ann.title
        if any(w in title for w in ("增长", "盈利")):
            return self._make_signal(ann, SignalAction.BUY, SignalStrength.MEDIUM, "业绩快报利好")
        if any(w in title for w in ("下降", "亏损")):
            return self._make_signal(ann, SignalAction.SELL, SignalStrength.MEDIUM, "业绩快报利空")
        return self._make_signal(ann, SignalAction.WATCH, SignalStrength.LOW, "业绩快报中性")

    def _handle_increase_holding(self, ann: Announcement) -> Signal:
        return self._make_signal(
            ann, SignalAction.BUY, SignalStrength.MEDIUM,
            "股东/高管增持，看好公司发展"
        )

    def _handle_decrease_holding(self, ann: Announcement) -> Signal:
        title = ann.title
        # 大比例减持更严重
        pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", title)
        pct = float(pct_match.group(1)) if pct_match else 0
        strength = SignalStrength.HIGH if pct > 5 else SignalStrength.MEDIUM
        action = SignalAction.SELL if pct > 2 else SignalAction.WATCH
        return self._make_signal(ann, action, strength, f"股东减持{pct}%")

    def _handle_buyback(self, ann: Announcement) -> Signal:
        return self._make_signal(
            ann, SignalAction.BUY, SignalStrength.MEDIUM,
            "公司回购股份，彰显信心"
        )

    def _handle_equity_incentive(self, ann: Announcement) -> Signal:
        return self._make_signal(
            ann, SignalAction.BUY, SignalStrength.MEDIUM,
            "股权激励方案，绑定核心团队利益"
        )

    def _handle_major_contract(self, ann: Announcement) -> Signal:
        return self._make_signal(
            ann, SignalAction.BUY, SignalStrength.MEDIUM,
            "重大合同/中标，业务增长预期"
        )

    def _handle_risk_warning(self, ann: Announcement) -> Signal:
        title = ann.title
        if any(w in title for w in ("退市", "终止上市", "*ST")):
            return self._make_signal(ann, SignalAction.STRONG_SELL, SignalStrength.HIGH, "退市风险")
        return self._make_signal(ann, SignalAction.SELL, SignalStrength.HIGH, "风险警示")

    def _handle_dividend(self, ann: Announcement) -> Signal:
        return self._make_signal(
            ann, SignalAction.WATCH, SignalStrength.LOW,
            "分红方案公告"
        )

    def _handle_restructuring(self, ann: Announcement) -> Signal:
        return self._make_signal(
            ann, SignalAction.WATCH, SignalStrength.MEDIUM,
            "资产重组，需关注具体方案"
        )

    @staticmethod
    def _make_signal(
        ann: Announcement,
        action: SignalAction,
        strength: SignalStrength,
        reason: str,
    ) -> Signal:
        return Signal(
            announcement_id=ann.id,
            stock_code=ann.stock_code,
            stock_name=ann.stock_name,
            action=action,
            strength=strength,
            reason=reason,
        )
