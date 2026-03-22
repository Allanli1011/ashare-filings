"""读取 OpenClaw 配置文件，复用已配置的模型信息。

OpenClaw 的配置文件位于 ~/.openclaw/openclaw.json（JSON5 格式），
其中 models.providers 定义了各个 LLM 提供商的 baseUrl、apiKey、api 类型等。
本模块解析该文件，提取出可供本项目 LLM 引擎直接使用的连接参数。
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"


@dataclass
class OpenClawModelInfo:
    """从 OpenClaw 配置中提取的模型连接信息。"""

    provider_name: str
    base_url: str
    api_key: str
    api_type: str  # "openai-completions", "openai-responses", "anthropic-messages"
    model_id: str


def _strip_json5_comments(text: str) -> str:
    """简易去除 JSON5 中的 // 和 /* */ 注释。"""
    # 移除单行注释（但不处理字符串内的 //）
    text = re.sub(r'(?<!:)//.*?$', '', text, flags=re.MULTILINE)
    # 移除多行注释
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    # 移除尾部逗号（JSON5 允许但标准 JSON 不允许）
    text = re.sub(r',\s*([\]}])', r'\1', text)
    return text


def _resolve_env_vars(value: str) -> str:
    """解析 ${ENV_VAR} 格式的环境变量引用。"""
    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, "")
    return re.sub(r'\$\{(\w+)}', replacer, value)


def load_openclaw_config(config_path: str | Path = "") -> dict:
    """加载并解析 openclaw.json 文件。"""
    path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
    if not path.exists():
        raise FileNotFoundError(f"OpenClaw 配置文件不存在: {path}")

    raw_text = path.read_text(encoding="utf-8")
    clean_json = _strip_json5_comments(raw_text)

    try:
        return json.loads(clean_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"OpenClaw 配置文件解析失败: {e}") from e


def resolve_primary_model(config: dict) -> OpenClawModelInfo:
    """解析 OpenClaw 配置中的 primary model 信息。

    读取 agents.defaults.model.primary（格式为 "provider/model"），
    然后从 models.providers 中找到对应 provider 的连接参数。
    """
    # 获取 primary model 引用，格式: "provider_name/model_id"
    agents = config.get("agents", {})
    defaults = agents.get("defaults", {})
    model_ref = defaults.get("model", {})

    if isinstance(model_ref, str):
        primary = model_ref
    else:
        primary = model_ref.get("primary", "")

    if not primary or "/" not in primary:
        raise ValueError(
            f"无法解析 OpenClaw primary model: '{primary}'。"
            f"期望格式: 'provider/model-id'"
        )

    provider_name, model_id = primary.split("/", 1)
    return _resolve_provider(config, provider_name, model_id)


def resolve_provider_model(config: dict, provider_name: str) -> OpenClawModelInfo:
    """解析 OpenClaw 配置中指定 provider 的第一个模型。"""
    providers = config.get("models", {}).get("providers", {})
    if provider_name not in providers:
        raise ValueError(
            f"OpenClaw 配置中未找到 provider '{provider_name}'。"
            f"可用: {list(providers.keys())}"
        )
    provider_cfg = providers[provider_name]
    models = provider_cfg.get("models", [])
    model_id = models[0]["id"] if models else ""
    return _resolve_provider(config, provider_name, model_id)


def _resolve_provider(config: dict, provider_name: str, model_id: str) -> OpenClawModelInfo:
    """从 providers 配置中提取连接信息。"""
    providers = config.get("models", {}).get("providers", {})
    if provider_name not in providers:
        raise ValueError(
            f"OpenClaw 配置中未找到 provider '{provider_name}'。"
            f"可用: {list(providers.keys())}"
        )

    provider_cfg = providers[provider_name]
    base_url = provider_cfg.get("baseUrl", "")
    api_key = provider_cfg.get("apiKey", "")
    api_type = provider_cfg.get("api", "openai-completions")

    # 解析环境变量引用
    if api_key:
        api_key = _resolve_env_vars(api_key)
    if base_url:
        base_url = _resolve_env_vars(base_url)

    return OpenClawModelInfo(
        provider_name=provider_name,
        base_url=base_url,
        api_key=api_key,
        api_type=api_type,
        model_id=model_id,
    )
