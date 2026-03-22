"""钉钉 Webhook 通知。"""

from __future__ import annotations

import hashlib
import hmac
import base64
import logging
import time
import urllib.parse

import httpx

from src.notifier.base import BaseNotifier

logger = logging.getLogger(__name__)


class DingtalkNotifier(BaseNotifier):
    """钉钉机器人通知。"""

    channel_name = "dingtalk"

    def __init__(self, webhook_url: str, secret: str = ""):
        self.webhook_url = webhook_url
        self.secret = secret

    def _sign_url(self) -> str:
        """钉钉加签。"""
        if not self.secret:
            return self.webhook_url

        timestamp = str(round(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            self.secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return f"{self.webhook_url}&timestamp={timestamp}&sign={sign}"

    async def send(self, title: str, content: str) -> bool:
        if not self.webhook_url:
            logger.warning("钉钉 webhook URL 未配置")
            return False

        url = self._sign_url()
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": f"## {title}\n\n{content}",
            },
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                result = resp.json()
                if result.get("errcode") != 0:
                    logger.error("钉钉发送失败: %s", result)
                    return False
                return True
        except Exception as e:
            logger.error("钉钉通知异常: %s", e)
            return False
