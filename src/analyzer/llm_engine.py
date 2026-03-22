"""LLM 辅助分析引擎。

对规则引擎无法处理的复杂公告（如重组方案细节、
非标审计意见等），调用 LLM 进行深度语义分析。
"""

from __future__ import annotations

import json
import logging
from datetime import date

from src.config import LLMConfig
from src.models.announcement import Announcement
from src.models.signal import Signal, SignalAction, SignalStrength

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """你是一个专业的 A 股投资分析师。你的任务是分析上市公司公告，判断其对股价的影响。

请严格按以下 JSON 格式回复（不要添加其他文字）：
{
  "action": "强烈买入|买入|持有观望|卖出|强烈卖出|关注",
  "strength": "高|中|低",
  "reason": "简洁的判断理由（50字以内）",
  "key_data": {
    "提取的关键数据字段": "值"
  }
}

分析要点：
1. 关注公告中的核心数据变化（营收、利润、合同金额、持股比例等）
2. 判断对公司基本面的实质影响
3. 考虑市场预期差（超预期 vs 符合预期 vs 低于预期）
4. 区分一次性事件和持续性影响"""


class LLMEngine:
    """LLM 分析引擎。"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._call_count = 0
        self._call_date = date.today()

    async def analyze(self, announcement: Announcement) -> Signal | None:
        """使用 LLM 深度分析公告。"""
        # 每日调用预算控制
        today = date.today()
        if today != self._call_date:
            self._call_count = 0
            self._call_date = today

        if self._call_count >= self.config.daily_budget_calls:
            logger.warning("LLM 每日调用预算已耗尽 (%d)", self.config.daily_budget_calls)
            return None

        content = announcement.content_text or announcement.title
        # 截断过长的内容，节省 token
        if len(content) > 4000:
            content = content[:2000] + "\n...(内容截断)...\n" + content[-1500:]

        user_prompt = (
            f"股票: {announcement.stock_code} {announcement.stock_name}\n"
            f"公告标题: {announcement.title}\n"
            f"公告类型: {announcement.category.value}\n"
            f"发布时间: {announcement.publish_time}\n\n"
            f"公告内容:\n{content}"
        )

        try:
            result = await self._call_llm(user_prompt)
            self._call_count += 1
        except Exception as e:
            logger.error("LLM 调用失败: %s", e)
            return None

        return self._parse_result(announcement, result)

    async def _call_llm(self, user_prompt: str) -> dict:
        """调用 LLM API。"""
        if self.config.provider == "anthropic":
            return await self._call_anthropic(user_prompt)
        raise ValueError(f"不支持的 LLM 提供商: {self.config.provider}")

    async def _call_anthropic(self, user_prompt: str) -> dict:
        """调用 Anthropic Claude API。"""
        import anthropic

        api_key = self.config.api_key
        if not api_key:
            import os
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("未配置 ANTHROPIC_API_KEY")

        client = anthropic.AsyncAnthropic(api_key=api_key)

        message = await client.messages.create(
            model=self.config.model,
            max_tokens=500,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        response_text = message.content[0].text
        return json.loads(response_text)

    @staticmethod
    def _parse_result(announcement: Announcement, result: dict) -> Signal | None:
        """将 LLM 返回的 JSON 解析为 Signal。"""
        try:
            action_map = {v.value: v for v in SignalAction}
            strength_map = {v.value: v for v in SignalStrength}

            action = action_map.get(result.get("action", ""), SignalAction.WATCH)
            strength = strength_map.get(result.get("strength", ""), SignalStrength.LOW)

            return Signal(
                announcement_id=announcement.id,
                stock_code=announcement.stock_code,
                stock_name=announcement.stock_name,
                action=action,
                strength=strength,
                reason=result.get("reason", "LLM 分析"),
                key_data=result.get("key_data", {}),
            )
        except Exception as e:
            logger.error("LLM 结果解析失败: %s | raw=%s", e, result)
            return None
