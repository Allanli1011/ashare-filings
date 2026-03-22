"""OpenClaw 配置读取测试。"""

import json
import os
from pathlib import Path

from src.utils.openclaw import (
    _resolve_env_vars,
    _strip_json5_comments,
    load_openclaw_config,
    resolve_primary_model,
    resolve_provider_model,
)

# 模拟 OpenClaw 配置（JSON5 格式，含注释和尾逗号）
_SAMPLE_CONFIG = """{
  // OpenClaw 配置
  "models": {
    "mode": "merge",
    "providers": {
      "ollama": {
        "baseUrl": "http://127.0.0.1:11434/v1",
        "apiKey": "no-key",
        "api": "openai-completions",
        "models": [
          {
            "id": "qwen2.5:14b",
            "name": "Qwen 2.5 14B",
            "contextWindow": 32000,
            "maxTokens": 8000,
          },
        ],
      },
      "anthropic": {
        "baseUrl": "https://api.anthropic.com",
        "apiKey": "${ANTHROPIC_API_KEY}",
        "api": "anthropic-messages",
        "models": [
          {
            "id": "claude-sonnet-4-20250514",
            "name": "Claude Sonnet",
          },
        ],
      },
    },
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "ollama/qwen2.5:14b",
        "fallbacks": ["anthropic/claude-sonnet-4-20250514"],
      },
    },
  },
}"""


def test_strip_json5_comments():
    raw = '{\n  // comment\n  "key": "val",\n}'
    clean = _strip_json5_comments(raw)
    data = json.loads(clean)
    assert data["key"] == "val"


def test_strip_trailing_commas():
    raw = '{"a": [1, 2,], "b": {"c": 3,},}'
    clean = _strip_json5_comments(raw)
    data = json.loads(clean)
    assert data["a"] == [1, 2]


def test_resolve_env_vars():
    os.environ["TEST_KEY_XYZ"] = "secret123"
    assert _resolve_env_vars("${TEST_KEY_XYZ}") == "secret123"
    assert _resolve_env_vars("Bearer ${TEST_KEY_XYZ}") == "Bearer secret123"
    assert _resolve_env_vars("no-vars-here") == "no-vars-here"
    del os.environ["TEST_KEY_XYZ"]


def test_load_and_resolve_primary(tmp_path: Path):
    config_file = tmp_path / "openclaw.json"
    config_file.write_text(_SAMPLE_CONFIG)

    config = load_openclaw_config(config_file)
    info = resolve_primary_model(config)

    assert info.provider_name == "ollama"
    assert info.model_id == "qwen2.5:14b"
    assert info.base_url == "http://127.0.0.1:11434/v1"
    assert info.api_type == "openai-completions"


def test_resolve_specific_provider(tmp_path: Path):
    config_file = tmp_path / "openclaw.json"
    config_file.write_text(_SAMPLE_CONFIG)

    config = load_openclaw_config(config_file)
    info = resolve_provider_model(config, "anthropic")

    assert info.provider_name == "anthropic"
    assert info.model_id == "claude-sonnet-4-20250514"
    assert info.api_type == "anthropic-messages"


def test_env_var_in_api_key(tmp_path: Path):
    os.environ["ANTHROPIC_API_KEY"] = "sk-test-key"
    config_file = tmp_path / "openclaw.json"
    config_file.write_text(_SAMPLE_CONFIG)

    config = load_openclaw_config(config_file)
    info = resolve_provider_model(config, "anthropic")

    assert info.api_key == "sk-test-key"
    del os.environ["ANTHROPIC_API_KEY"]
