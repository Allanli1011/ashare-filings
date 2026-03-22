"""策略模块测试。"""

from src.models.signal import Signal, SignalAction, SignalStrength
from src.strategy.strategy import StrategyAdvisor


def _make_signal(action: SignalAction, strength: SignalStrength) -> Signal:
    return Signal(
        announcement_id="test",
        stock_code="000001",
        stock_name="测试",
        action=action,
        strength=strength,
        reason="测试信号",
    )


def test_conservative_filters_low():
    advisor = StrategyAdvisor(risk_level="conservative")
    signals = [
        _make_signal(SignalAction.BUY, SignalStrength.HIGH),
        _make_signal(SignalAction.BUY, SignalStrength.LOW),
        _make_signal(SignalAction.SELL, SignalStrength.MEDIUM),
    ]
    report = advisor.generate_report(signals, 100, "2024-01-01")
    # 保守模式只保留高强度
    assert report.total_signals == 1


def test_aggressive_keeps_all():
    advisor = StrategyAdvisor(risk_level="aggressive")
    signals = [
        _make_signal(SignalAction.BUY, SignalStrength.LOW),
        _make_signal(SignalAction.SELL, SignalStrength.LOW),
    ]
    report = advisor.generate_report(signals, 50, "2024-01-01")
    assert report.total_signals == 2


def test_report_format():
    advisor = StrategyAdvisor()
    signals = [_make_signal(SignalAction.BUY, SignalStrength.HIGH)]
    report = advisor.generate_report(signals, 200, "2024-01-01")
    text = report.format_text()
    assert "A股公告监控日报" in text
    assert "2024-01-01" in text
