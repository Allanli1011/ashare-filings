"""分析引擎调度器 — 协调规则引擎和 LLM 引擎。

工作流程:
1. 标题快速分析 → 确定优先级
2. 优先级 >= 3 的公告 → 规则引擎处理
3. 规则引擎无法处理或结果模糊 → LLM 深度分析（仅 hybrid/llm 模式）
"""

from __future__ import annotations

import logging
from typing import Literal

from src.analyzer.llm_engine import LLMEngine
from src.analyzer.rule_engine import RuleEngine
from src.config import AnalyzerConfig
from src.models.announcement import Announcement, AnnouncementCategory
from src.models.signal import Signal, SignalAction
from src.parser.title_classifier import analyze_title

logger = logging.getLogger(__name__)

# 这些类型的公告规则引擎处理不了，需要 LLM
_NEEDS_LLM_CATEGORIES = {
    AnnouncementCategory.RESTRUCTURING,
    AnnouncementCategory.OTHER,
}

# 标题优先级低于此值的直接跳过
_MIN_PRIORITY = 2


class AnalysisEngine:
    """分析引擎主入口。"""

    def __init__(self, config: AnalyzerConfig):
        self.mode: Literal["rule", "llm", "hybrid"] = config.mode
        self.rule_engine = RuleEngine()
        self.llm_engine = LLMEngine(config.llm) if self.mode != "rule" else None

    async def analyze_batch(self, announcements: list[Announcement]) -> list[Signal]:
        """批量分析公告，返回有价值的投资信号。"""
        signals: list[Signal] = []

        for ann in announcements:
            # Step 1: 标题快速筛选
            title_analysis = analyze_title(ann)
            if title_analysis.priority < _MIN_PRIORITY:
                continue

            # Step 2: 规则引擎
            signal = self.rule_engine.analyze(ann)

            # Step 3: 如果规则引擎结果为观望/关注，且配置了 LLM，则深度分析
            if self._should_use_llm(ann, signal):
                llm_signal = await self._try_llm(ann)
                if llm_signal:
                    signal = llm_signal

            if signal and signal.is_actionable:
                signals.append(signal)
                logger.info("生成信号: %s", signal.summary())

        return signals

    def _should_use_llm(self, ann: Announcement, signal: Signal | None) -> bool:
        """判断是否需要调用 LLM。"""
        if self.llm_engine is None:
            return False
        if self.mode == "rule":
            return False
        if self.mode == "llm":
            return True
        # hybrid 模式：规则引擎无结果或结果为观望时使用 LLM
        if signal is None:
            return ann.category in _NEEDS_LLM_CATEGORIES
        return signal.action in (SignalAction.WATCH, SignalAction.HOLD)

    async def _try_llm(self, ann: Announcement) -> Signal | None:
        """尝试 LLM 分析，失败时静默返回 None。"""
        try:
            return await self.llm_engine.analyze(ann)
        except Exception as e:
            logger.error("LLM 分析失败 [%s]: %s", ann.id, e)
            return None
