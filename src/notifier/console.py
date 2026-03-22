"""控制台输出（开发/调试用）。"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel

from src.notifier.base import BaseNotifier

_console = Console()


class ConsoleNotifier(BaseNotifier):
    """控制台打印通知。"""

    channel_name = "console"

    async def send(self, title: str, content: str) -> bool:
        _console.print(Panel(content, title=title, border_style="cyan"))
        return True
