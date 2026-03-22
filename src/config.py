"""全局配置管理，支持 TOML 文件 + 环境变量。"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class SourceCninfo(BaseModel):
    base_url: str = "http://www.cninfo.com.cn/new/disclosure"


class SourceEastmoney(BaseModel):
    base_url: str = "https://np-anotice-stock.eastmoney.com/api"


class SourcesConfig(BaseModel):
    enabled: list[str] = ["cninfo"]
    cninfo: SourceCninfo = SourceCninfo()
    eastmoney: SourceEastmoney = SourceEastmoney()


class FilterConfig(BaseModel):
    watch_stocks: list[str] = []
    watch_categories: list[str] = [
        "业绩预告", "业绩快报", "年报", "半年报", "季报",
        "股权激励", "增持", "减持", "回购", "重大合同",
        "资产重组", "分红", "停复牌", "风险警示",
    ]
    min_market_cap: float = 0


class LLMConfig(BaseModel):
    provider: Literal["anthropic", "openai", "local"] = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    api_key: str = ""
    base_url: str = ""  # OpenAI 兼容 API 地址，如 http://localhost:11434/v1
    daily_budget_calls: int = 200


class AnalyzerConfig(BaseModel):
    mode: Literal["rule", "llm", "hybrid"] = "hybrid"
    llm: LLMConfig = LLMConfig()


class StrategyConfig(BaseModel):
    risk_level: Literal["conservative", "moderate", "aggressive"] = "moderate"


class WecomConfig(BaseModel):
    webhook_url: str = ""


class DingtalkConfig(BaseModel):
    webhook_url: str = ""
    secret: str = ""


class EmailConfig(BaseModel):
    smtp_host: str = ""
    smtp_port: int = 465
    username: str = ""
    password: str = ""
    recipients: list[str] = []


class NotifyConfig(BaseModel):
    channels: list[str] = ["console"]
    wecom: WecomConfig = WecomConfig()
    dingtalk: DingtalkConfig = DingtalkConfig()
    email: EmailConfig = EmailConfig()


class AppConfig(BaseSettings):
    """应用主配置。"""

    poll_interval_minutes: int = 30
    db_path: str = "data/filings.db"
    log_level: str = "INFO"
    sources: SourcesConfig = SourcesConfig()
    filter: FilterConfig = FilterConfig()
    analyzer: AnalyzerConfig = AnalyzerConfig()
    strategy: StrategyConfig = StrategyConfig()
    notify: NotifyConfig = NotifyConfig()

    model_config = {"env_prefix": "ASHARE_", "env_nested_delimiter": "__"}


def load_config(path: str | Path = "config.toml") -> AppConfig:
    """从 TOML 文件加载配置，环境变量可覆盖。"""
    config_path = Path(path)
    if config_path.exists():
        with open(config_path, "rb") as f:
            raw = tomllib.load(f)
        # 将 [general] 段的字段提升到顶层
        general = raw.pop("general", {})
        merged = {**general, **raw}
        return AppConfig(**merged)
    return AppConfig()
