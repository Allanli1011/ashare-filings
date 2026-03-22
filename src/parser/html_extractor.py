"""HTML 公告文本提取。"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


def extract_text_from_html(html: str) -> str:
    """从 HTML 页面提取正文纯文本。"""
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")

        # 移除 script/style 标签
        for tag in soup(["script", "style", "header", "footer", "nav"]):
            tag.decompose()

        # 尝试找公告正文容器
        content_div = (
            soup.find("div", class_="detail-body")
            or soup.find("div", id="ContentBody")
            or soup.find("article")
            or soup.body
        )

        if content_div is None:
            return ""

        text = content_div.get_text(separator="\n", strip=True)
        # 压缩多余空行
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text
    except Exception as e:
        logger.error("HTML 文本提取失败: %s", e)
        return ""
