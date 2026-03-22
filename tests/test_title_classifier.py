"""标题分类器测试。"""

from datetime import datetime

from src.models.announcement import Announcement, AnnouncementCategory
from src.parser.title_classifier import analyze_title


def _make_ann(title: str) -> Announcement:
    return Announcement(
        id="test",
        stock_code="600000",
        stock_name="测试",
        title=title,
        category=AnnouncementCategory.OTHER,
        publish_time=datetime.now(),
        source="test",
        url="https://example.com",
    )


def test_positive_earnings():
    result = analyze_title(_make_ann("2024年度业绩预增公告 净利润增长200%"))
    assert result.priority >= 4
    assert result.is_positive is True


def test_negative_earnings():
    result = analyze_title(_make_ann("关于公司首亏的风险提示公告"))
    assert result.priority >= 4
    assert result.is_positive is False


def test_delisting_risk():
    result = analyze_title(_make_ann("关于*ST退市风险的公告"))
    assert result.priority == 5
    assert result.is_positive is False


def test_number_extraction():
    result = analyze_title(_make_ann("关于回购股份的公告 回购金额不超过5亿元"))
    assert len(result.key_numbers) > 0


def test_low_priority():
    result = analyze_title(_make_ann("关于召开股东大会的通知"))
    assert result.priority <= 2
