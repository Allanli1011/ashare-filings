"""A股公告监控系统主入口。

支持两种运行模式:
  1. 单次运行: python -m src.main          （采集一次并退出）
  2. 定时运行: python -m src.main --daemon  （按间隔持续运行）
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import date

from src.analyzer.engine import AnalysisEngine
from src.config import AppConfig, load_config
from src.fetcher.base import BaseFetcher
from src.fetcher.cninfo import CninfoFetcher
from src.fetcher.eastmoney import EastmoneyFetcher
from src.notifier.dispatcher import NotifyDispatcher
from src.storage.database import Database
from src.strategy.strategy import StrategyAdvisor
from src.utils.logging import setup_logging

logger = logging.getLogger(__name__)


def _build_fetchers(config: AppConfig) -> list[BaseFetcher]:
    """根据配置创建数据源。"""
    fetchers: list[BaseFetcher] = []
    for source in config.sources.enabled:
        if source == "cninfo":
            fetchers.append(CninfoFetcher(config.sources.cninfo.base_url))
        elif source == "eastmoney":
            fetchers.append(EastmoneyFetcher(config.sources.eastmoney.base_url))
        else:
            logger.warning("未知数据源: %s", source)
    return fetchers


async def run_once(config: AppConfig) -> None:
    """执行一次完整的采集-分析-推送流程。"""
    db = Database(config.db_path)
    await db.init()

    fetchers = _build_fetchers(config)
    analyzer = AnalysisEngine(config.analyzer)
    advisor = StrategyAdvisor(config.strategy.risk_level)
    dispatcher = NotifyDispatcher(config.notify)

    today = date.today()
    watch_stocks = config.filter.watch_stocks or None

    # Step 1: 采集公告
    all_announcements = []
    for fetcher in fetchers:
        try:
            announcements = await fetcher.fetch_announcements(today, watch_stocks)
            all_announcements.extend(announcements)
        except Exception as e:
            logger.error("数据源 %s 采集失败: %s", fetcher.source_name, e)

    if not all_announcements:
        logger.info("今日无新公告")
        return

    # Step 2: 去重（同一公告可能在多个源出现）+ 过滤已处理
    new_announcements = await db.filter_new(all_announcements)
    logger.info("新公告: %d / %d", len(new_announcements), len(all_announcements))

    if not new_announcements:
        logger.info("无新公告需要处理")
        return

    # Step 3: 按类型过滤
    watch_categories = set(config.filter.watch_categories)
    filtered = [
        ann for ann in new_announcements
        if ann.category.value in watch_categories
    ]
    logger.info("类型过滤后: %d 条", len(filtered))

    # Step 4: 分析
    signals = await analyzer.analyze_batch(filtered)

    # Step 5: 持久化
    for ann in new_announcements:
        await db.save_announcement(ann)
    for signal in signals:
        await db.save_signal(signal)

    # Step 6: 生成报告并推送
    report = advisor.generate_report(
        signals=signals,
        total_announcements=len(all_announcements),
        report_date=today.isoformat(),
    )
    report_text = report.format_text()

    await dispatcher.dispatch("A股公告监控", report_text)
    logger.info("本轮处理完成")


async def run_daemon(config: AppConfig) -> None:
    """定时运行模式。"""
    interval = config.poll_interval_minutes * 60
    logger.info("守护进程模式启动，间隔 %d 分钟", config.poll_interval_minutes)

    while True:
        try:
            await run_once(config)
        except Exception as e:
            logger.error("运行异常: %s", e)
        await asyncio.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="A股公告监控系统")
    parser.add_argument(
        "--config", "-c", default="config.toml", help="配置文件路径"
    )
    parser.add_argument(
        "--daemon", "-d", action="store_true", help="守护进程模式（定时运行）"
    )
    args = parser.parse_args()

    config = load_config(args.config)
    setup_logging(config.log_level)

    if args.daemon:
        asyncio.run(run_daemon(config))
    else:
        asyncio.run(run_once(config))


if __name__ == "__main__":
    main()
