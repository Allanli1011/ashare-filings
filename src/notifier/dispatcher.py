"""通知调度器 — 根据配置分发到各通知渠道。"""

from __future__ import annotations

import logging

from src.config import NotifyConfig
from src.notifier.base import BaseNotifier
from src.notifier.console import ConsoleNotifier
from src.notifier.dingtalk import DingtalkNotifier
from src.notifier.wecom import WecomNotifier

logger = logging.getLogger(__name__)


class NotifyDispatcher:
    """通知调度器。"""

    def __init__(self, config: NotifyConfig):
        self.notifiers: list[BaseNotifier] = []
        for channel in config.channels:
            notifier = self._create_notifier(channel, config)
            if notifier:
                self.notifiers.append(notifier)

    async def dispatch(self, title: str, content: str) -> None:
        """向所有已配置的渠道发送通知。"""
        for notifier in self.notifiers:
            try:
                ok = await notifier.send(title, content)
                if ok:
                    logger.info("通知发送成功: %s", notifier.channel_name)
                else:
                    logger.warning("通知发送失败: %s", notifier.channel_name)
            except Exception as e:
                logger.error("通知渠道 %s 异常: %s", notifier.channel_name, e)

    @staticmethod
    def _create_notifier(channel: str, config: NotifyConfig) -> BaseNotifier | None:
        if channel == "console":
            return ConsoleNotifier()
        if channel == "wecom":
            return WecomNotifier(webhook_url=config.wecom.webhook_url)
        if channel == "dingtalk":
            return DingtalkNotifier(
                webhook_url=config.dingtalk.webhook_url,
                secret=config.dingtalk.secret,
            )
        logger.warning("未知通知渠道: %s", channel)
        return None
