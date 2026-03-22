"""公告数据采集模块。"""

from src.fetcher.base import BaseFetcher
from src.fetcher.cninfo import CninfoFetcher
from src.fetcher.eastmoney import EastmoneyFetcher

__all__ = ["BaseFetcher", "CninfoFetcher", "EastmoneyFetcher"]
