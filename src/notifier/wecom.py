"""企业微信 Webhook 通知。"""

from __future__ import annotations

import logging

import httpx

from src.notifier.base import BaseNotifier

logger = logging.getLogger(__name__)


class WecomNotifier(BaseNotifier):
    """企业微信机器人通知。"""

    channel_name = "wecom"

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send(self, title: str, content: str) -> bool:
        if not self.webhook_url:
            logger.warning("企业微信 webhook URL 未配置")
            return False

        # 企业微信 markdown 消息
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": f"## {title}\n\n{content}",
            },
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(self.webhook_url, json=payload)
                resp.raise_for_status()
                result = resp.json()
                if result.get("errcode") != 0:
                    logger.error("企业微信发送失败: %s", result)
                    return False
                return True
        except Exception as e:
            logger.error("企业微信通知异常: %s", e)
            return False
