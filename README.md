# A股公告监控系统 (ashare-filings)

从每天海量的上市公司公告中，自动筛选出对投资有价值的信息并提示操作策略。

## 架构

```
数据采集 → 公告解析 → 智能分析 → 策略生成 → 消息推送
(fetcher)   (parser)   (analyzer)  (strategy)  (notifier)
                           ↕
                     SQLite 持久化
```

### 模块说明

| 模块 | 职责 | 关键文件 |
|------|------|---------|
| **fetcher** | 从巨潮资讯网 / 东方财富采集公告列表 | `cninfo.py`, `eastmoney.py` |
| **parser** | PDF/HTML 正文提取 + 标题快速分类 | `pdf_extractor.py`, `title_classifier.py` |
| **analyzer** | 规则引擎处理常见公告，LLM 处理复杂公告 | `rule_engine.py`, `llm_engine.py`, `engine.py` |
| **strategy** | 按风险偏好过滤信号，生成日报 | `strategy.py` |
| **notifier** | 控制台 / 企业微信 / 钉钉推送 | `console.py`, `wecom.py`, `dingtalk.py` |
| **storage** | SQLite 异步存储，公告去重 | `database.py` |

### 分析流水线

```
每条公告
  │
  ├─ 标题分类器打分 (priority 1-5)
  │   └─ priority < 2 → 跳过
  │
  ├─ 规则引擎（零成本，覆盖 ~80% 常见公告类型）
  │   ├─ 业绩预增/预亏 → 买入/卖出
  │   ├─ 增持/减持/回购 → 买入/卖出/观望
  │   ├─ 风险警示/退市 → 强烈卖出
  │   └─ ...
  │
  └─ LLM 引擎（仅 hybrid/llm 模式，处理规则引擎无法判断的公告）
      └─ 重组方案 / 非标审计 / 复杂合同 → 深度语义分析
```

## 快速开始

### 安装

```bash
# Python >= 3.10
pip install -e .

# 开发环境（含测试工具）
pip install -e ".[dev]"
```

### 配置

```bash
cp config.example.toml config.toml
# 编辑 config.toml，按需修改
```

### 运行

```bash
# 单次运行（采集今天的公告，分析后退出）
python -m src

# 守护进程模式（按配置间隔持续运行）
python -m src --daemon

# 指定配置文件
python -m src -c /path/to/config.toml
```

### 运行测试

```bash
pytest
```

## 配置详解

### 数据源

```toml
[sources]
enabled = ["cninfo", "eastmoney"]  # 可同时启用多个
```

- **cninfo** — 巨潮资讯网，证监会指定信息披露网站，最权威
- **eastmoney** — 东方财富，API 更快，结构更清晰

### 公告过滤

```toml
[filter]
watch_stocks = ["000001", "600519"]  # 留空 = 全市场
watch_categories = ["业绩预告", "增持", "减持", "回购", "重大合同"]
min_market_cap = 100  # 只关注 100 亿以上，0 = 不过滤
```

支持的公告类型：业绩预告、业绩快报、年报、半年报、季报、股权激励、增持、减持、回购、重大合同、资产重组、股东大会、分红、停复牌、风险警示。

### LLM 配置

支持四种模式：

**1. Anthropic Claude（默认）**

```toml
[analyzer.llm]
provider = "anthropic"
model = "claude-sonnet-4-20250514"
api_key = ""  # 或设置环境变量 ANTHROPIC_API_KEY
```

**2. OpenAI 兼容 API**

```toml
[analyzer.llm]
provider = "openai"
model = "gpt-4o"
api_key = ""  # 或设置环境变量 OPENAI_API_KEY
base_url = "https://api.openai.com/v1"
```

**3. 本地模型（Ollama / vLLM / LM Studio）**

```toml
[analyzer.llm]
provider = "local"
model = "qwen2.5:14b"
base_url = "http://localhost:11434/v1"  # Ollama 默认地址
daily_budget_calls = 1000  # 本地无费用，可调高
```

**4. 复用 OpenClaw 配置（推荐）**

如果你本地已经配置好了 OpenClaw，可以直接复用其模型设置，无需重复配置：

```toml
[analyzer.llm]
provider = "openclaw"
# openclaw_config_path = ""  # 留空 = ~/.openclaw/openclaw.json
# openclaw_provider = ""      # 留空 = 使用 primary model
                               # 指定 = "ollama", "lmstudio", "anthropic" 等
```

系统会自动从 `~/.openclaw/openclaw.json` 读取 `baseUrl`、`apiKey`、`api` 类型和模型名，并根据 `api` 类型自动选择 Anthropic 或 OpenAI 兼容协议。

### 策略与通知

```toml
[strategy]
risk_level = "moderate"  # conservative / moderate / aggressive
# conservative: 只推送高强度信号
# moderate:     推送中高强度信号
# aggressive:   推送所有信号

[notify]
channels = ["console", "wecom"]  # 可同时启用多个渠道

[notify.wecom]
webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..."

[notify.dingtalk]
webhook_url = "https://oapi.dingtalk.com/robot/send?access_token=..."
secret = ""  # 加签密钥
```

## 项目结构

```
src/
├── main.py                  # 入口，支持单次/守护进程模式
├── config.py                # TOML + 环境变量配置管理
├── models/
│   ├── announcement.py      # 公告模型（15 种分类）
│   └── signal.py            # 投资信号（6 种操作 × 3 种强度）
├── fetcher/
│   ├── base.py              # 数据源抽象基类
│   ├── cninfo.py            # 巨潮资讯网采集器
│   └── eastmoney.py         # 东方财富采集器
├── parser/
│   ├── pdf_extractor.py     # PDF 文本提取
│   ├── html_extractor.py    # HTML 文本提取
│   └── title_classifier.py  # 标题快速分类（优先级 + 情绪判断）
├── analyzer/
│   ├── engine.py            # 分析调度器（协调规则 + LLM）
│   ├── rule_engine.py       # 规则引擎（确定性判断）
│   └── llm_engine.py        # LLM 引擎（Claude / OpenAI / 本地 / OpenClaw）
├── strategy/
│   └── strategy.py          # 信号过滤 + 报告生成
├── notifier/
│   ├── dispatcher.py        # 通知调度器
│   ├── console.py           # 控制台输出
│   ├── wecom.py             # 企业微信 Webhook
│   └── dingtalk.py          # 钉钉 Webhook
├── storage/
│   └── database.py          # SQLite 异步存储
└── utils/
    ├── logging.py           # 日志配置
    └── openclaw.py          # OpenClaw 配置读取
tests/
├── test_rule_engine.py      # 规则引擎测试
├── test_title_classifier.py # 标题分类器测试
├── test_strategy.py         # 策略模块测试
└── test_openclaw.py         # OpenClaw 配置读取测试
```

## 推送效果示例

```
📊 A股公告监控日报 (2026-03-22)
━━━━━━━━━━━━━━━━━━━━
扫描公告: 1523 条 | 有效信号: 7 条

🟢 买入/关注信号:
  • [高] 600519 贵州茅台 | 买入 | 业绩预增128%
  • [中] 000858 五粮液 | 买入 | 公司回购股份，彰显信心

🔴 卖出/风险信号:
  • [高] 002456 欧菲光 | 强烈卖出 | 退市风险
  • [中] 300xxx 某科技 | 卖出 | 股东减持6.5%

━━━━━━━━━━━━━━━━━━━━
⚠️ 以上为自动分析，仅供参考，不构成投资建议。
```

## 免责声明

本系统生成的所有投资信号和策略建议仅供参考，不构成任何投资建议。投资有风险，入市需谨慎。使用者应自行承担投资决策的全部责任。
