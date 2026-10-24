# ChanNexus

ChanNexus 是一个面向多市场行情的缠论量化分析系统。项目提供独立的缠论计算核心、统一行情接口和 FastAPI 服务，可用于行情结构分析、策略研究、图表展示及量化应用集成。

## 主要能力

- 处理 K 线包含关系并生成标准化缠论 K 线
- 计算顶底分型、笔、线段、笔中枢和线段中枢
- 识别背驰及一、二、三类买卖点
- 支持批量计算和逐根增量计算
- 对重复时间 K 线执行幂等更新
- 提供 A 股、港股、美股、期货、外汇和数字货币行情适配层
- 提供结构化 FastAPI 分析接口
- 提供 TradingView 基础协议接口

## 项目结构

```text
ChanNexus/
├── src/
│   ├── chanlun_core/          # 独立缠论计算核心
│   ├── chanlun/               # 行情、策略、回测与交易模块
│   └── chanlun_core_cli.py    # 核心自检入口
├── web/chanlun_chart/
│   ├── api/                   # FastAPI 路由、模型与服务
│   └── fastapi_app.py         # FastAPI 启动入口
├── script/                    # 行情同步及辅助脚本
├── tests/                     # 自动化测试
├── requirements-web.txt       # Web 服务依赖
└── pyproject.toml             # 项目元数据与完整依赖
```

## 环境要求

- macOS
- Python 3.11
- Homebrew
- TA-Lib

建议使用独立虚拟环境运行，不要将项目依赖安装到系统 Python。

## 快速安装

### 1. 获取代码

```bash
git clone https://github.com/Ethanwu23/ChanNexus.git
cd ChanNexus
```

### 2. 创建虚拟环境

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
```

### 3. 安装依赖

先安装 macOS 系统依赖：

```bash
brew install ta-lib
```

再安装 Web 服务及默认行情模块所需的 Python 依赖：

```bash
python -m pip install -r requirements-web.txt
```

如需使用全部市场适配器、回测或交易模块，可安装完整依赖：

```bash
python -m pip install -r requirements.txt
```

不同券商或交易平台的 SDK 可能有独立的平台和账户要求，仅在启用对应模块时安装。

## 配置

### 1. 创建本地配置

```bash
cp src/chanlun/config.py.demo src/chanlun/config.py
chmod 600 src/chanlun/config.py
```

`src/chanlun/config.py` 已被 Git 忽略，用于保存当前设备的运行配置。

### 2. 常用配置项

| 配置项 | 说明 | 默认值 |
| --- | --- | --- |
| `WEB_HOST` | Web 服务监听地址 | `0.0.0.0` |
| `WEB_PORT` | Web 服务监听端口 | `9910` |
| `DATA_PATH` | 行情、缓存、日志和数据库目录 | `.channexus` |
| `DB_TYPE` | 数据库类型，可选 SQLite 或 MySQL | `sqlite` |
| `DB_DATABASE` | SQLite 文件名或 MySQL 数据库名 | `chanlun_klines` |
| `EXCHANGE_*` | 各市场使用的行情适配器 | 按市场配置 |

当 `DATA_PATH` 以 `.` 开头时，数据目录位于当前用户主目录。例如默认配置对应：

```text
~/.channexus
```

### 3. 凭证管理

- 不要在源码、README、Notebook 或提交记录中填写真实密钥。
- 优先通过环境变量或未纳入版本控制的本地配置提供凭证。
- 提交代码前检查 `git status`，确认本地配置、日志和数据文件未进入提交范围。
- 密钥一旦意外提交，应立即在服务提供方撤销并重新生成。

## 启动 FastAPI 服务

```bash
source .venv/bin/activate
export PYTHONPATH="$PWD/src"
python web/chanlun_chart/fastapi_app.py
```

服务地址由 `WEB_HOST` 和 `WEB_PORT` 决定。默认端口为 `9910`。

启动后可访问：

| 地址 | 用途 |
| --- | --- |
| `http://127.0.0.1:9910/api/docs` | Swagger API 文档 |
| `http://127.0.0.1:9910/api/openapi.json` | OpenAPI 定义 |
| `http://127.0.0.1:9910/api/v1/health` | 服务健康检查 |

健康检查：

```bash
curl http://127.0.0.1:9910/api/v1/health
```

正常响应：

```json
{
  "status": "ok",
  "service": "ChanNexus"
}
```

## 缠论分析接口

### 请求

```text
POST /api/v1/analysis
Content-Type: application/json
```

请求字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `code` | string | 标的代码 |
| `frequency` | string | K 线周期，例如 `1m`、`30m`、`d` |
| `config` | object | 可选的缠论计算参数 |
| `klines` | array | 按时间排列的 OHLCV 数据 |

单根 K 线字段：

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `date` | ISO 8601 datetime | 建议携带时区 |
| `open` | number | 必须位于最高价和最低价之间 |
| `close` | number | 必须位于最高价和最低价之间 |
| `high` | number | 不得小于最低价 |
| `low` | number | 不得大于最高价 |
| `volume` | number | 不得小于零 |

调用示例：

```bash
curl -X POST "http://127.0.0.1:9910/api/v1/analysis" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "DEMO.TEST",
    "frequency": "d",
    "config": {
      "bi_type": "new",
      "min_bi_raw_bars": 5,
      "strict_fractal": true
    },
    "klines": [
      {
        "date": "2026-01-05T15:00:00+08:00",
        "open": 10.0,
        "high": 11.0,
        "low": 9.8,
        "close": 10.8,
        "volume": 100000
      },
      {
        "date": "2026-01-06T15:00:00+08:00",
        "open": 10.8,
        "high": 11.5,
        "low": 10.5,
        "close": 11.2,
        "volume": 120000
      },
      {
        "date": "2026-01-07T15:00:00+08:00",
        "open": 11.2,
        "high": 11.3,
        "low": 10.2,
        "close": 10.4,
        "volume": 150000
      }
    ]
  }'
```

### 计算参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `bi_type` | `new` | 笔计算口径，可选 `old`、`new`、`simple`、`top_bottom` |
| `min_bi_raw_bars` | `5` | 构成笔所需的最少原始 K 线数量 |
| `strict_fractal` | `true` | 是否使用严格分型条件 |
| `allow_sub_extreme_fractal` | `false` | 是否允许次级极值分型 |
| `pivot_overlap` | `first_three` | 中枢重叠区间计算方式 |
| `pivot_relation` | `zg_zd` | 中枢关系判定方式 |
| `macd_fast` | `12` | MACD 快线周期 |
| `macd_slow` | `26` | MACD 慢线周期 |
| `macd_signal` | `9` | MACD 信号线周期 |

### 响应

响应采用稳定的结构化 JSON，主要字段包括：

| 字段 | 说明 |
| --- | --- |
| `schema_version` | 响应结构版本 |
| `counts` | 各类缠论对象数量统计 |
| `source_bars` | 标准化后的原始 K 线 |
| `chan_bars` | 处理包含关系后的缠论 K 线 |
| `fractals` | 顶底分型 |
| `bis` | 笔及其信号信息 |
| `segments` | 线段及其信号信息 |
| `bi_pivots` | 笔中枢 |
| `segment_pivots` | 线段中枢 |

输入会按照 `date` 排序。同一时间存在多条 K 线时保留最后一条，因此同一批数据重复提交不会产生重复 K 线。

## Python 调用

核心计算模块可以脱离 Web 服务直接使用：

```python
import pandas as pd

from chanlun_core import ChanConfig, ChanEngine


klines = pd.DataFrame(
    [
        {
            "date": "2026-01-05T15:00:00+08:00",
            "open": 10.0,
            "high": 11.0,
            "low": 9.8,
            "close": 10.8,
            "volume": 100000,
        },
        {
            "date": "2026-01-06T15:00:00+08:00",
            "open": 10.8,
            "high": 11.5,
            "low": 10.5,
            "close": 11.2,
            "volume": 120000,
        },
        {
            "date": "2026-01-07T15:00:00+08:00",
            "open": 11.2,
            "high": 11.3,
            "low": 10.2,
            "close": 10.4,
            "volume": 150000,
        },
    ]
)

engine = ChanEngine(
    code="DEMO.TEST",
    frequency="d",
    config=ChanConfig(),
)
engine.process_klines(klines)

result = engine.snapshot()
print(result["counts"])
```

可以多次调用 `process_klines()` 输入新数据。计算器会按时间合并数据，并重新生成确定性的派生结构。

## TradingView 接口

| 接口 | 说明 |
| --- | --- |
| `GET /tv/config` | 返回支持的市场、周期及图表能力 |
| `GET /tv/time` | 返回服务器 Unix 时间戳 |

可用市场和周期取决于已安装依赖及当前行情适配器配置。

## 运行自检

安装依赖并设置 `PYTHONPATH` 后，可执行内置模拟行情自检：

```bash
source .venv/bin/activate
export PYTHONPATH="$PWD/src"
python -m chanlun_core_cli --self-test
```

命令应输出合法 JSON，且进程退出状态为 `0`。

## 常见问题

### 无法导入项目模块

确认当前目录为项目根目录，并设置：

```bash
export PYTHONPATH="$PWD/src"
```

### TA-Lib 安装失败

确认系统库和虚拟环境中的 Python 包均已安装：

```bash
brew install ta-lib
python -m pip install TA-Lib
```

### 端口被占用

修改 `src/chanlun/config.py` 中的 `WEB_PORT`，或检查占用默认端口的进程：

```bash
lsof -nP -iTCP:9910 -sTCP:LISTEN
```

### 行情接口不可用

检查以下项目：

1. 对应市场适配器是否已正确配置。
2. 可选 SDK 是否已安装并支持当前系统架构。
3. 网络、代理和接口访问权限是否正常。
4. 标的代码和周期格式是否符合行情源要求。

## 部署安全

当前 FastAPI 分析接口不提供用户认证，不应直接暴露到公网。需要远程访问时，应在服务前增加具备 TLS、身份认证、访问控制和限流能力的反向代理。

仅在本机使用时，建议将 `WEB_HOST` 设置为：

```python
WEB_HOST = "127.0.0.1"
```

## 使用说明

缠论结构和交易信号属于技术分析结果，不构成投资建议。实盘使用前应通过历史数据、模拟交易和风险控制规则进行独立验证。
