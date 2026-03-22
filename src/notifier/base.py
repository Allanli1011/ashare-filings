"""通知推送基类。"""

from __future__ import annotations

import abc


class BaseNotifier(abc.ABC):
    """通知渠道基类。"""

    channel_name: str = ""

    @abc.abstractmethod
    async def send(self, title: str, content: str) -> bool:
        """发送通知。

        Args:
            title: 通知标题。
            content: 通知正文。

        Returns:
            是否发送成功。
        """
