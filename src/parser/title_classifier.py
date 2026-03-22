"""基于公告标题的快速分类和关键信息提取。

在不下载 PDF 的情况下，通过标题即可完成初步筛选，
大幅减少需要深度分析的公告数量。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.models.announcement import Announcement, AnnouncementCategory


@dataclass
class TitleAnalysis:
    """标题分析结果。"""

    category: AnnouncementCategory
    priority: int  # 1-5, 5 最高
    key_numbers: list[str] = field(default_factory=list)
    is_positive: bool | None = None  # True=利好, False=利空, None=中性


# 高优先级关键词及其对应的情绪倾向
_PRIORITY_KEYWORDS: list[tuple[str, int, bool | None]] = [
    # (关键词, 优先级, 情绪: True=正面, False=负面, None=待定)
    ("业绩预增", 5, True),
    ("业绩大幅增长", 5, True),
    ("净利润增长", 4, True),
    ("扭亏为盈", 5, True),
    ("业绩预减", 5, False),
    ("业绩预亏", 5, False),
    ("首亏", 5, False),
    ("续亏", 4, False),
    ("大幅下降", 5, False),
    ("暂停上市", 5, False),
    ("终止上市", 5, False),
    ("立案调查", 5, False),
    ("行政处罚", 4, False),
    ("违规", 4, False),
    ("退市", 5, False),
    ("ST", 5, False),
    ("*ST", 5, False),
    ("回购", 4, True),
    ("增持", 4, True),
    ("减持", 4, False),
    ("股权激励", 4, True),
    ("高送转", 4, True),
    ("分红", 3, True),
    ("重大合同", 4, True),
    ("中标", 4, True),
    ("重组", 4, None),
    ("收购", 4, None),
    ("定增", 3, None),
    ("配股", 3, None),
    ("可转债", 3, None),
    ("停牌", 3, None),
    ("复牌", 3, None),
]

# 数字提取模式：金额、百分比、股数等
_NUMBER_PATTERNS = [
    re.compile(r"(\d+(?:\.\d+)?)\s*(?:亿|万)?\s*(?:元|股|份)"),
    re.compile(r"(?:增长|下降|增加|减少)\s*(\d+(?:\.\d+)?)\s*%"),
    re.compile(r"(\d+(?:\.\d+)?)\s*%"),
]


def analyze_title(announcement: Announcement) -> TitleAnalysis:
    """分析公告标题，快速得出优先级和情绪。"""
    title = announcement.title
    best_priority = 1
    sentiment: bool | None = None

    for keyword, priority, is_positive in _PRIORITY_KEYWORDS:
        if keyword in title:
            if priority > best_priority:
                best_priority = priority
                sentiment = is_positive

    # 提取标题中的关键数字
    numbers = []
    for pattern in _NUMBER_PATTERNS:
        for match in pattern.finditer(title):
            numbers.append(match.group(0))

    return TitleAnalysis(
        category=announcement.category,
        priority=best_priority,
        key_numbers=numbers,
        is_positive=sentiment,
    )
