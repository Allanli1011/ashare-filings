"""投资信号模型。"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SignalAction(str, Enum):
    """操作建议。"""

    STRONG_BUY = "强烈买入"
    BUY = "买入"
    HOLD = "持有观望"
    SELL = "卖出"
    STRONG_SELL = "强烈卖出"
    WATCH = "关注"


class SignalStrength(str, Enum):
    """信号强度。"""

    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"


class Signal(BaseModel):
    """投资信号 — 由分析引擎对公告解读后生成。"""

    announcement_id: str
    stock_code: str
    stock_name: str
    action: SignalAction
    strength: SignalStrength
    reason: str = Field(description="判断理由")
    key_data: dict = Field(default_factory=dict, description="关键数据提取")
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def is_actionable(self) -> bool:
        """是否需要采取行动（非观望）。"""
        return self.action not in (SignalAction.HOLD, SignalAction.WATCH)

    def summary(self) -> str:
        return (
            f"[{self.strength.value}] {self.stock_code} {self.stock_name} "
            f"| {self.action.value} | {self.reason}"
        )
