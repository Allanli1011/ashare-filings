"""规则引擎测试。"""

from datetime import datetime

from src.analyzer.rule_engine import RuleEngine
from src.models.announcement import Announcement, AnnouncementCategory
from src.models.signal import SignalAction


def _make_ann(title: str, category: AnnouncementCategory) -> Announcement:
    return Announcement(
        id="test_001",
        stock_code="000001",
        stock_name="测试股票",
        title=title,
        category=category,
        publish_time=datetime.now(),
        source="test",
        url="https://example.com",
    )


def test_earnings_forecast_positive():
    engine = RuleEngine()
    ann = _make_ann("2024年度业绩预增公告 净利润增长120%", AnnouncementCategory.EARNINGS_FORECAST)
    signal = engine.analyze(ann)
    assert signal is not None
    assert signal.action == SignalAction.BUY


def test_earnings_forecast_negative():
    engine = RuleEngine()
    ann = _make_ann("2024年度业绩预亏公告", AnnouncementCategory.EARNINGS_FORECAST)
    signal = engine.analyze(ann)
    assert signal is not None
    assert signal.action == SignalAction.SELL


def test_increase_holding():
    engine = RuleEngine()
    ann = _make_ann("关于控股股东增持公司股份的公告", AnnouncementCategory.INCREASE_HOLDING)
    signal = engine.analyze(ann)
    assert signal is not None
    assert signal.action == SignalAction.BUY


def test_risk_warning_delisting():
    engine = RuleEngine()
    ann = _make_ann("关于公司股票可能被终止上市的风险提示", AnnouncementCategory.RISK_WARNING)
    signal = engine.analyze(ann)
    assert signal is not None
    assert signal.action == SignalAction.STRONG_SELL


def test_dividend():
    engine = RuleEngine()
    ann = _make_ann("2024年度利润分配方案", AnnouncementCategory.DIVIDEND)
    signal = engine.analyze(ann)
    assert signal is not None
    assert signal.action == SignalAction.WATCH
