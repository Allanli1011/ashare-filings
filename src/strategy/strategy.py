"""策略建议生成器。

将原始信号转化为带有操作建议的策略报告，
并根据风险偏好过滤和调整信号。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal

from src.models.signal import Signal, SignalAction, SignalStrength

logger = logging.getLogger(__name__)


@dataclass
class StrategyReport:
    """策略报告 — 最终推送给用户的内容。"""

    date: str
    total_announcements: int
    total_signals: int
    buy_signals: list[Signal] = field(default_factory=list)
    sell_signals: list[Signal] = field(default_factory=list)
    watch_signals: list[Signal] = field(default_factory=list)

    def format_text(self) -> str:
        """格式化为可读文本。"""
        lines = [
            f"📊 A股公告监控日报 ({self.date})",
            "━━━━━━━━━━━━━━━━━━━━",
            f"扫描公告: {self.total_announcements} 条 | 有效信号: {self.total_signals} 条",
            "",
        ]

        if self.buy_signals:
            lines.append("🟢 买入/关注信号:")
            for s in self.buy_signals:
                lines.append(f"  • {s.summary()}")
            lines.append("")

        if self.sell_signals:
            lines.append("🔴 卖出/风险信号:")
            for s in self.sell_signals:
                lines.append(f"  • {s.summary()}")
            lines.append("")

        if self.watch_signals:
            lines.append("🟡 观察信号:")
            for s in self.watch_signals:
                lines.append(f"  • {s.summary()}")
            lines.append("")

        if not (self.buy_signals or self.sell_signals or self.watch_signals):
            lines.append("今日无重要信号。")

        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append("⚠️ 以上为自动分析，仅供参考，不构成投资建议。")
        return "\n".join(lines)


class StrategyAdvisor:
    """策略顾问 — 根据风险偏好过滤和排列信号。"""

    def __init__(self, risk_level: Literal["conservative", "moderate", "aggressive"] = "moderate"):
        self.risk_level = risk_level

    def generate_report(
        self,
        signals: list[Signal],
        total_announcements: int,
        report_date: str,
    ) -> StrategyReport:
        """生成策略报告。"""
        filtered = self._filter_by_risk(signals)
        sorted_signals = sorted(filtered, key=self._signal_sort_key, reverse=True)

        buy_signals = [
            s for s in sorted_signals
            if s.action in (SignalAction.STRONG_BUY, SignalAction.BUY)
        ]
        sell_signals = [
            s for s in sorted_signals
            if s.action in (SignalAction.STRONG_SELL, SignalAction.SELL)
        ]
        watch_signals = [
            s for s in sorted_signals
            if s.action in (SignalAction.WATCH, SignalAction.HOLD)
        ]

        return StrategyReport(
            date=report_date,
            total_announcements=total_announcements,
            total_signals=len(sorted_signals),
            buy_signals=buy_signals,
            sell_signals=sell_signals,
            watch_signals=watch_signals,
        )

    def _filter_by_risk(self, signals: list[Signal]) -> list[Signal]:
        """根据风险偏好过滤信号。"""
        if self.risk_level == "conservative":
            # 保守：只保留高强度信号
            return [s for s in signals if s.strength == SignalStrength.HIGH]
        if self.risk_level == "moderate":
            # 中等：保留中高强度信号
            return [s for s in signals if s.strength in (SignalStrength.HIGH, SignalStrength.MEDIUM)]
        # 激进：保留所有信号
        return signals

    @staticmethod
    def _signal_sort_key(signal: Signal) -> tuple[int, int]:
        """信号排序：强度 > 操作类型。"""
        strength_order = {SignalStrength.HIGH: 3, SignalStrength.MEDIUM: 2, SignalStrength.LOW: 1}
        action_order = {
            SignalAction.STRONG_BUY: 5, SignalAction.STRONG_SELL: 5,
            SignalAction.BUY: 4, SignalAction.SELL: 4,
            SignalAction.WATCH: 2, SignalAction.HOLD: 1,
        }
        return (
            strength_order.get(signal.strength, 0),
            action_order.get(signal.action, 0),
        )
