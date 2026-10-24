# ChanNexus 公开契约推演与独立核心实现

## 第一阶段：项目整体架构推演

### 1.1 业务定位与完整链路

项目是“多市场行情接入 + 缠论结构计算 + 信号策略 + 回测/实盘 + Web 展示”的量化系统。证据来自 `README.md` 功能列表、`exchange/` 统一行情接口、`backtesting/` 执行模型、`strategy/` 信号规则、`trader/` 实盘适配及 `web/chanlun_chart` 路由。

```text
TDX/CCXT/Futu/TQ/IB/QMT/CTP/DB
  -> Exchange.klines() 标准 OHLCV DataFrame
  -> FileCacheDB 行情/计算缓存
  -> CL(code, frequency, config).process_klines(df)
  -> Kline -> CLKline -> FX -> BI -> XD/ZSD -> ZS -> BC/MMD
  -> Strategy.open()/close() 生成 Operation
  -> BackTestTrader 或具体 Trader
  -> 订单、持仓、报表、告警、Web 图表
```

外围职责边界：

| 模块 | 可确定职责 | 推导依据 |
|---|---|---|
| `exchange/*` | 市场代码、K线、时区、周期、Tick、交易接口适配 | `Exchange` 抽象类与各供应商实现 |
| `file_db.py/db.py/rd.py` | CSV/对象缓存、SQL 业务表、Redis 任务配置 | 各读写方法及调用方 |
| `cl_interface.py` | 核心领域对象和计算器公开协议 | `Config`、`Kline`、`FX`、`BI`、`XD`、`ZS`、`ICL` |
| `cl_utils.py/cl_analyse.py` | MACD 力度、多级别、图表 DTO 和辅助判断 | 对 `ICL` getter 的调用 |
| `strategy/*` | 把结构/买卖点转成开平仓意图 | `Strategy` 子类 |
| `backtesting/*` | 可见行情窗口、撮合、费用、持仓、报表 | `MarketDatas/Trader/POSITION/BackTest` |
| `trader/*` | 操作到真实订单的映射与对账 | 各市场 Trader |
| `web/*` | 展示、设置、调度、选股和告警 | Flask 路由和 APScheduler 任务 |

### 1.2 核心入口公开交互契约

由 `cl_interface.ICL` 和 `cookbook/docs/缠论数据对象与方法.md` 可确定：

- 构造入参：`code: str`、`frequency: str`、`config: dict`。
- 更新入参：包含 `code/date/open/close/high/low/volume` 的 Pandas DataFrame；外围适配器通常已按时间排序和完成时区修正。
- 更新语义：可以反复调用 `process_klines`；README 明确说明逐 Bar 增量处理，已确认结构通常稳定，末端未确认结构可变化或消失。
- 结构输出：源 K线、普通/缠论 K线、指标、分型、笔、线段、走势段、各层中枢、最后中枢。
- 判断服务：创建中枢、盘整背驰、趋势背驰、两个中枢趋势关系。
- 调度时机：Web 图表请求、多周期缓存更新、回测逐 Bar、实时行情回调、选股任务和监控任务均会触发计算。

## 第二阶段：核心能力的公开规则推导

### 2.1 能力、输入、输出和约束矩阵

| 能力 | 输入 | 输出 | 公开约束与依据 |
|---|---|---|---|
| K线校验 | OHLCV、日期 | `Kline[]` | `ICL.process_klines`；高低价必须包住开收价，日期排序去重 |
| 包含合并 | 相邻原始 K线、此前趋势 | `CLKline[]` | README“计算并合并缠论K线”；上涨取较高高低点，下跌取较低高低点 |
| 三 K 分型 | 连续三根合并 K线 | `FX(top/di)` | 数据对象文档规定中间 K线及三根组成对象；末端可未确认 |
| 笔 | 交替顶底分型、笔配置 | `BI[]` | 配置文档：老笔、新笔、简单笔、顶底成笔；严格分型与次高低开关 |
| 线段 | 笔的特征序列 | `XD[]` | 配置文档明确采用特征序列；至少三元素并处理缺口/破坏/特殊拆分 |
| 走势段 | 线段的特征序列 | `XD[]` | 数据对象文档明确与线段同法、输入元素换成线段 |
| 中枢 | 三条及以上相邻线 | `ZS[]` | `zg=min(high)`、`zd=max(low)` 且 `zg>=zd`；前三段或全部段重叠；每九线升一级 |
| 盘整背驰 | 中枢进入/离开线力度 | `BC(pz)` | 买卖点文档：进出段均为相应极值且离开力度减弱 |
| 趋势背驰 | 两个以上同向同级中枢、末段 | `BC(qs)` | 中枢无重叠、末段创新高低且力度减弱 |
| 一类点 | 趋势/三卖后三卖方向背驰 | `1buy/1sell` | 买卖点规则第 1 节 |
| 二类点 | 一类点后的不创新低高或段背驰 | `2buy/2sell` | 买卖点规则第 2 节 |
| 三类点 | 离开中枢后的回抽/反抽 | `3buy/3sell` | 向上离开后向下不回中枢为三买，反向为三卖 |
| 类二/类三 | 前一同向段已有对应点且当前形成重叠 | `l2/l3` 类信号 | 买卖点规则对应章节 |
| 仓位风控 | 资金、价格、信号、持仓 | 数量/退出原因 | 由 `backtesting/base.py`、`backtest_trader.py`、具体策略决定，不属于形态计算器 |

### 2.2 无法仅凭规则证明的变量

公开文档给出了业务规则，但以下细节有多种合理实现且会改变端点：同价分型优先级、包含合并的第一根方向、末端假分型处理、特征序列缺口、笔破坏确认、四种中枢在边界处的延续/重画、MACD 面积端点是否含零轴 Bar、多个配置同时启用时的优先级。因此，没有合法对照快照时，任何实现都只能声称“契约兼容、公开规则一致”，不能证明所有 Bar 上逐点相同。

## 第三阶段：外围缺陷与已实施优化

### 3.1 主要问题

1. Web 固定会话密钥、配置样例鼓励明文密钥，存在会话伪造和凭据泄露风险。
2. 时间工具接受时区却使用系统时区，会造成跨市场 Bar 错位。
3. 日志将 `FileHandler` 错认成控制台 Handler，异常路径可能没有终端输出。
4. 单例首次构造无锁，Web/调度并发可重复创建 DB 或交易所连接。
5. 文件缓存 Pickle 非原子写且可执行对象，损坏/越权写入风险高。
6. 交易所适配器重复分页、重试、字段转换并大量 `print`，无法统一区分空行情与服务故障。
7. Web、DB、`cl_utils`、`BackTest` 均为大文件多职责对象，单元测试困难。
8. `setup.py` 与 `pyproject.toml` 的 Python 版本、包和依赖不一致。

### 3.2 本工作树中的修改

- `config.py.demo`：Web/AI 密钥使用环境变量。
- `web/chanlun_chart/cl_app/__init__.py`：随机/外部会话密钥，口令常量时间比较。
- `fun.py`：显式时区、线程安全单例、日志 Handler 修复。
- `tests/test_fun.py`：公共工具回归测试。

建议后续把文件缓存改为“临时文件写入 → flush/fsync → `Path.replace`”，对象数据改为带 schema version 的 JSON/Parquet；为交易所引入统一 `MarketDataError`、结构化日志和契约测试。

## 第四阶段：独立核心实现

### 4.1 新目录

```text
src/
  chanlun_core/
    __init__.py      # 稳定公开 API
    config.py        # 显式、可校验配置
    models.py        # Bar/ChanBar/Fractal/Line/Pivot/Signal
    engine.py        # 完整计算管线
    risk.py          # 与形态解耦的仓位风控
  chanlun_core_cli.py
tests/
  test_chanlun_core.py
```

实现不导入 `chanlun.cl`。`ChanEngine` 已支持：

- DataFrame 校验、排序、日期去重和增量幂等更新；
- 趋势相关的包含 K线合并；
- 三 K 分型与同类极值淘汰；
- 四种笔距离口径的基础实现；
- 基于笔特征序列的线段；
- 三线重叠、延续、层级和完成状态中枢；
- 基础盘整背驰、一类点、三类点；
- 稳定 JSON 快照与独立风险策略。
- `chanlun.cl_rebuilt.CL` 兼容入口：复用公开 DTO，支持现有代码使用的
  `start.k.k_index`、`line_mmds()`、中枢有效性和 MACD 字段链。
- `chanlun_core.selftest`：生成趋势、震荡、反转及包含关系混合行情，执行结构
  不变量和增量幂等检查。

运行方式：

```bash
PYTHONPATH=src python3 -m chanlun_core_cli data.csv --code SH.000001 --frequency d
PYTHONPATH=src python3 -m chanlun_core_cli --self-test
PYTHONPATH=src python3 -m unittest -v tests/test_chanlun_core.py
```

现有业务可按模块逐步切换，原入口保持不动：

```python
# 原写法：from chanlun import cl
from chanlun import cl_rebuilt as cl

cd = cl.CL("SH.000001", "d", config).process_klines(klines)
```

### 4.2 与全部配置分支对齐的工程方法

要满足严格逐点一致，应提供一组仅含公开业务输出的合法基准文件：每组保存输入 OHLCV、配置及 `FX/BI/XD/ZS/MMD/BC` 的 JSON 快照。然后按以下顺序差分：

1. 合并 K线数量和每根 high/low/源 Bar 范围；
2. 分型类型、时间、值、完成状态；
3. 笔端点、方向、确认状态；
4. 特征序列和线段端点；
5. 中枢 `zg/zd/gg/dd/lines/level/done`；
6. 背驰比较线和买卖点挂载位置。

`ChanEngine.snapshot()` 已为此提供稳定输出。每个差异必须转成独立测试后再调整规则，不能用单个行情样本硬编码。当前版本是可运行的公开规则基线；复杂线段特殊拆分、走势段、四种中枢变体、趋势背驰、二类和类二/类三点仍需按上述证据驱动方式完善，不能在无基准时宣称已经逐点等同。
