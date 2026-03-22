"""PDF 公告文本提取。"""

from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """从 PDF 字节流中提取纯文本。"""
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages_text = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text.strip())
        return "\n\n".join(pages_text)
    except Exception as e:
        logger.error("PDF 文本提取失败: %s", e)
        return ""
