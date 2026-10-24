# ChanNexus 全流程解析、问题审计与重构报告

> 审计范围：`src/chanlun`、`src/cl_myquant`、`src/cl_vnpy`、`src/cl_wtpy`、`web/chanlun_chart`、`script`、README 与构建配置。TradingView、Layui、ECharts 等已打包第三方静态产物只作为依赖识别，不逐行审计。核心 `chanlun.cl` 是 PyArmor 入口，无法从仓库源码逐行展开其算法实现；报告依据公开接口对象、调用链和文档描述其行为。

## 第一章：项目全局认知

### 1.1 项目用途

ChanNexus 是一个多市场缠论分析与量化交易平台。它把股票、期货、外汇和数字货币行情统一成 OHLCV K 线，增量计算包含关系、分型、笔、线段、中枢、走势段、背驰和买卖点，再将结果提供给 Web 图表、选股、监控、回测及实盘交易。

典型执行链如下：

```text
行情源/本地数据库
  -> Exchange 统一适配
  -> DataFrame K线标准化与周期转换
  -> FileCacheDB 缓存
  -> cl.CL 增量计算
  -> ICL / BI / XD / ZS / MMD 等领域对象
  -> 策略信号
  -> 回测统计 | Web图表 | 选股监控 | 实盘订单
```

### 1.2 技术栈

- Python 3.11；Pandas/Numpy/TA-Lib/MyTT/Scipy 用于行情和指标计算。
- Flask + Tornado + Gevent 提供 Web 服务，Flask-Login 管理会话，APScheduler 执行监控和选股任务。
- SQLite/MySQL + SQLAlchemy 保存业务数据，Redis 和本地 CSV/Pickle 作为缓存。
- PyTDX、CCXT、Futu、TQSDK、IB、QMT、CTP、Polygon、Alpaca、Baostock 等接入行情与交易。
- Pyecharts、TradingView Charting Library、ECharts 展示图表。
- VNPY、WTPY、掘金提供外部量化框架集成。
- OpenAI 兼容接口与飞书/钉钉用于 AI 分析和通知。

构建元数据存在双轨：`pyproject.toml` 声明 Python >=3.11 和完整依赖，而 `setup.py` 仍声明 Python >=3.7、包版本 2.0.1 和极少依赖，应以 `pyproject.toml` 为主并最终移除旧配置。

### 1.3 架构分层与模块依赖

| 层 | 主要模块 | 职责 |
|---|---|---|
| 领域模型 | `cl_interface.py`、`cl_analyse.py` | 定义配置、K线、分型、笔、线段、中枢、背驰、买卖点及多级别分析接口 |
| 算法实现 | `cl.py`（受保护运行时）、`cl_utils.py` | 增量缠论计算入口、指标统计、图表数据转换和辅助判断 |
| 行情网关 | `exchange/*` | 将不同供应商的代码、周期、时区、K线、Tick、余额、持仓和订单统一为 `Exchange` 接口 |
| 持久化 | `db.py`、`file_db.py`、`rd.py` | SQL 业务表、本地 K线/计算缓存、Redis 任务配置 |
| 策略与执行 | `strategy/*`、`backtesting/*`、`trader/*` | 生成开平仓操作、撮合回测、费用统计、实盘下单 |
| 应用服务 | `xuangu/*`、`monitor.py`、`tools/*` | 选股、告警、AI 分析、消息推送 |
| 展示与调度 | `web/chanlun_chart`、`script/*` | HTTP API、页面、定时任务、行情同步和进程启动 |
| 框架适配 | `cl_vnpy`、`cl_wtpy`、`cl_myquant` | 把领域策略接到第三方回测/实盘框架 |

依赖方向总体是“展示/任务 → 应用服务 → 策略/回测 → 领域接口 → 行情与持久化”，但 `cl_utils.py` 同时依赖 DB、Exchange 和图表结构，`BackTest` 同时负责执行、并发、报表和序列化，形成反向依赖与上帝对象。

### 1.4 核心数据流

1. `get_exchange(market)` 根据配置构造具体交易所，适配器输出统一字段 `code/date/open/close/high/low/volume`。
2. `Exchange` 的周期转换方法按市场交易时段重采样；`FileCacheDB` 缓存原始 K 线并丢弃可能未完成的最后一根。
3. `cl.CL.process_klines` 按 Bar 增量更新；已确认结构通常不重算，最后未确认结构会随新行情演化。
4. `ICL` 暴露 K线、分型、笔、线段、走势段、中枢、背驰和买卖点查询；`MultiLevelAnalyse` 联结父子级别。
5. `MarketDatas` 为策略提供多周期对象；`Strategy` 返回 `Operation`；`BackTestTrader` 维护 `POSITION` 并计算手续费、盈亏和退出规则。
6. 同一信号可流向回测、选股列表、监控消息或具体 `Trader` 下单实现。

### 1.5 架构优缺点

优点：领域词汇完整；增量算法适合实时与回测复用；交易所抽象覆盖市场广；策略接口与执行器基本分离；文件、SQL、Redis 多级存储便于单机部署；VNPY/WTPY/掘金适配提升可扩展性。

缺点：模块职责过宽；大量全局单例和配置导入导致测试困难；可选交易依赖在模块顶层导入；异常处理经常打印后继续；缓存使用不安全且无版本协议的 Pickle；市场周期转换大量复制；缺少正式测试目录、CI、类型检查和迁移机制；Web 路由集中在 1500 行单文件中。

## 第二章：代码逐模块梳理解读

### 2.1 领域计算模块

- `base.py`：定义市场枚举，是行情、DB、选股的共同键。
- `cl_interface.py`：领域协议核心。`Config` 控制 K线包含、分型区间、笔标准、线段拆分、中枢区间和买卖点规则；`Kline/CLKline/FX/BI/XD/ZS` 逐级组合；`MMD/BC` 表示信号；`ICL` 约束计算引擎必须提供的查询能力。边界包括未确认结构、缺口、同价高低点、少量 K线和递归级别不完整。
- `cl.py`：加载受 PyArmor 保护的 `CL` 实现。根据 README，它逐 Bar 合并包含 K线，再计算分型、笔、线段、中枢、走势段及信号。
- `cl_analyse.py`：`MultiLevelAnalyse` 把当前级别一笔/线段映射到低级别结构；`LinesFormAnalyse` 判断线段组合形态。数据不足时应返回空分析而非强造结论。
- `cl_utils.py`：批量获取计算对象、MACD 力度/背驰、中枢指标、图表配置、TradingView 数据、TD 序列、交叉判断和 Heikin-Ashi 转换。该文件目前混合领域、存储和展示职责。
- `kcharts.py`：把领域对象映射到 Pyecharts 图层，绘制 K线、笔、线段、中枢、买卖点、指标和交易订单；输入为空、指标长度不同和时间轴对齐是主要边界。

### 2.2 行情与交易所模块

- `exchange/exchange.py`：`Exchange` 抽象类定义代码列表、K线、Tick、交易时段、余额、持仓和订单协议；各 `convert_*_frequency` 处理不同市场的午休、夜盘、周/月边界。
- `exchange/__init__.py`：按市场与配置选择适配器。当前工厂直接导入具体类，某个可选 SDK 缺失可能影响对应分支。
- `exchange_tdx*`：覆盖 A/HK/US/外汇/国内外期货，分页拉取后修正代码、时间、复权和交易日；断线时重新选最快节点。边界是午休时间戳、夜盘归属日、除权数据缺失和服务器返回空页。
- `exchange_binance*`、`exchange_zb.py`：CCXT 合约/现货适配，处理代理、毫秒时间戳、分页和订单方向。需注意限频、交易对下线及精度。
- `exchange_futu.py`、`exchange_ib.py`、`exchange_qmt.py`、`exchange_tq.py`、`exchange_ctp.py`：同时覆盖行情与交易；异步回调、线程生命周期、订单状态重复通知和断线重连是关键边界。
- `exchange_baostock.py`、`exchange_polygon.py`、`exchange_alpaca.py`：历史行情补充源；供应商复权和时区语义不同。
- `exchange_db.py`：从统一 SQL K线表读取行情，适合作为其他采集器的下游。
- `stocks_bkgn.py`、`tdx_a_codes.py`：行业概念板块与证券代码元数据。

### 2.3 持久化与公共基础模块

- `db.py`：SQLAlchemy 表模型和 `DB` 门面，保存缓存、自选组、告警任务/记录、TradingView 标记、订单、图表配置和 AI 记录。当前既定义模型又承担仓储和表维护。
- `file_db.py`：保存行情 CSV、缠论对象 Pickle 和通用缓存；配置摘要决定计算缓存是否可复用，行情错位或 OHLCV 变化会触发全量重算。边界是并发读写半文件、缓存版本升级和损坏文件。
- `rd.py`：Redis 对象/字节缓存和任务配置。
- `config.py`：部署、数据库、交易所账号和消息配置；本次已将敏感 AI/Web 配置改为环境变量入口并清除已提交真实值。
- `fun.py`：日志、单例和时间转换；本次修复了时区参数失效、Handler 继承误判和并发首次调用重复构造。
- `utils.py`：代理配置以及钉钉/飞书签名、消息发送。

### 2.4 回测、策略与实盘模块

- `backtesting/base.py`：`POSITION` 保存持仓与开平仓记录；`Operation` 描述策略意图；`MarketDatas/Trader/Strategy` 是三类扩展协议；费用函数区分 A 股和美股。
- `backtest_klines.py`：控制回放时间窗口和各周期 K线可见范围，避免策略看到未来数据。
- `klines_generator.py`：由基础周期合成高周期数据。
- `backtest_trader.py`：执行开仓、加仓、减仓、清仓，维护止盈止损和交易结果。边界是同 Bar 多信号、价格为零、部分成交、做空方向和手续费最小值。
- `backtest.py`：编排单/多标的回测、参数优化、缓存、并行运行及报表，是目前最重的协调对象。
- `optimize.py`：生成参数笛卡尔积；组合数可能指数增长。
- `signal_to_trade.py`：把已有信号记录重放为交易，便于隔离信号质量与执行规则。
- `strategy/*.py`：各策略围绕笔/线段买卖点、背驰、中枢突破、多级别一买二买三买形成 `Operation`。共同规则是仅使用已暴露 K线、按 `uid` 管理独立仓位、在信号消失或结构破坏时退出。
- `trader/*.py`：将 `BackTestTrader` 的操作映射到 A 股、港股、期货、币和 QMT/CTP 接口；实盘必须处理可用余额、最小手数、涨跌停、订单拒绝和重连后的状态对账。

### 2.5 选股、监控、Web 与框架集成

- `xuangu/xuangu.py`：函数式选股条件集合；每个函数读取指定级别结构并返回命中原因。
- `xuangu_by_same.py`：提取走势特征并用 DTW 搜索相似形态；全市场两两距离成本较高。
- `monitor.py`：定时计算自选标的信号、生成图像并发送飞书消息。
- `tools/ai_analyse.py`：组织行情/指标提示词，调用硅基流动或 OpenRouter，结果写 DB。
- `web/chanlun_chart/cl_app`：应用工厂、登录、行情 UDF API、设置、自选、告警、选股和 AI 路由；三个任务模块承载 APScheduler 作业。
- `cl_vnpy`、`cl_wtpy`、`cl_myquant`：在外部框架的 Bar/订单回调与本项目 `MarketDatas/Trader/Strategy` 之间做适配。
- `script/crontab`、`script/trader`：各市场数据同步、批量选股和实盘守护启动脚本。

## 第三章：全项目问题排查

### 3.1 高风险

1. **仓库曾包含真实 API/飞书密钥**：任何有仓库读取权的人都可能调用外部服务。已清除工作树中的值，但历史仍存在；必须立即在服务端撤销并轮换，之后清理 Git 历史。
2. **固定 Flask `secret_key`**：可伪造登录会话。本次改为环境变量，未配置时生成进程级随机值。
3. **登录直接比较且默认空密码**：直接比较存在微小时序泄露；空密码配合 `0.0.0.0` 会公开全部管理接口。本次使用常量时间比较；部署时仍必须设置强密码并用反向代理限制来源。
4. **Pickle 反序列化**：`file_db.py`、回测配置、WTPY 测试缓存会执行恶意对象。缓存目录必须仅允许服务账号写入；长期应改为 Parquet/JSON + schema version。
5. **敏感设置经 Web 表单存储**：数据库访问控制或日志配置不当会泄露飞书密钥。应加密静态字段并对设置接口增加 CSRF。

### 3.2 正确性与隐藏 Bug

1. `fun.timeint_to_str/timeint_to_datetime` 接受 `tz` 却使用系统本地时区，本次已修复；这会造成跨时区 Bar 错位。
2. `str_to_datetime` 对无时区字符串调用 `astimezone`，其结果依赖机器时区，本次改为显式本地化。
3. `get_logger` 把 `FileHandler` 当成已有控制台 Handler，且控制台没有 formatter，本次已修复。
4. `singleton` 在多线程 Web/行情任务首次调用时可能创建多个连接，本次加锁。
5. `get_tdx_klines` 无条件丢弃最后一行；若文件已只保存完成 Bar，会少一根数据。需要在缓存协议中显式保存 `is_closed`。
6. Pickle 写入不是原子替换，并发读最多重试后失败；应写临时文件、`fsync` 后 `replace`。
7. 多个行情适配器捕获宽泛异常后返回空数据，调用方无法区分“无行情”和“供应商故障”。
8. 市场交易时间存在硬编码 TODO，节假日、半日市和期货夜盘归属可能错误。
9. `setup.py` 与 `pyproject.toml` 的版本、Python 要求和包列表冲突，传统安装可能遗漏子包。
10. 许多示例逻辑位于模块 `__main__` 且直接连接实盘服务，误运行风险高。

### 3.3 性能问题

1. `BackTest`、全市场选股大量复制 DataFrame 和触发 GC；应采用按标的流式迭代和只读列数组。
2. `cl_utils.py` 多次线性扫描笔/线段；可为日期、index 和 uid 建索引。
3. `xuangu_by_same` 的 DTW 对样本量呈高成本增长；应先以长度、波动率、方向向量粗筛，再并行精排。
4. QMT 自定义周线存在全量转换 TODO；应仅重算最后一个未闭合周期。
5. 文件缓存通过随机概率触发目录全扫描，造成不可预测延迟；应改为独立计划任务。
6. Web 单次请求可能同步计算多级别与绘图；应以参数摘要缓存并设置并发上限。
7. 参数优化直接生成笛卡尔积，容易耗尽内存；应返回迭代器并设置最大组合数。

### 3.4 可维护性与耦合

- Web 1500 行单文件应拆成 auth、chart、settings、watchlist、alerts、AI 六个 Blueprint。
- `db.py` 应拆模型、Session 管理和按聚合根划分的 Repository。
- `cl_utils.py` 应拆纯领域指标、缓存服务和 TradingView DTO 映射。
- 交易所适配器重复分页、标准化、重试和错误打印，应抽 `KlineNormalizer`、`RetryPolicy` 和统一异常层。
- `BackTest` 应拆 `BacktestEngine`、`ResultAggregator`、`ReportRenderer`、`OptimizationRunner`。
- 顶层导入全部可选 SDK 使最小部署困难，应在工厂分支延迟导入并给出明确依赖错误。
- 缺少单元/契约/集成测试；金融逻辑尤其需要固定 K线金样测试和未来函数检测。

## 第四章：分层次代码优化改写

### 4.1 本次已完成的轻度优化

改动均已直接落在完整可运行源码中：

- `src/chanlun/config.py`：清除明文 AI/飞书值；新增 `CHANLUN_AI_TOKEN`、`CHANLUN_OPENROUTER_AI_KEY`、`CHANLUN_WEB_SECRET_KEY` 环境变量入口。
- `web/chanlun_chart/cl_app/__init__.py`：随机/外部会话密钥；登录使用 `hmac.compare_digest`。
- `src/chanlun/fun.py`：显式时区转换、线程安全单例、正确识别日志 Handler 并统一格式。
- `tests/test_fun.py`：覆盖时区往返、并发单例和日志 Handler 回归。

部署示例：

```bash
export CHANLUN_WEB_SECRET_KEY="$(openssl rand -hex 32)"
export CHANLUN_AI_TOKEN="你的新密钥"
export CHANLUN_OPENROUTER_AI_KEY="你的新密钥"
```

### 4.2 推荐的深度重构目标结构

```text
chanlun/
  domain/          # 纯领域对象、缠论规则、策略信号
  application/     # 行情计算、选股、监控、回测用例
  ports/           # MarketDataPort、OrderPort、RepositoryPort
  adapters/
    market_data/   # TDX/CCXT/Futu/... 实现
    persistence/   # SQL/Redis/File 实现
    trading/       # CTP/QMT/... 实现
  presentation/
    web/           # Flask Blueprints 与 DTO
```

重构顺序应保持行为可验证：先为 `Exchange` 建契约测试和固定数据集；再抽行情标准化与缓存协议；随后拆 Web Blueprint 和 Repository；最后才拆 `BackTest` 与 `cl_utils`。核心算法必须先建立“输入 K线 → 分型/笔/线段/中枢/信号”金样快照，否则一次性改写 3 万行会引入无法察觉的交易偏差。

### 4.3 完整可运行代码与改动边界

优化后的完整代码即当前工作树，而非报告中省略上下文的片段。可用以下命令验证：

```bash
PYTHONPATH=src python3 -m unittest -v tests/test_fun.py
python3 -m compileall -q src web/chanlun_chart script
```

本轮有意不改动用户已有修改的 `cl_interface.py`、`tools/ai_analyse.py`、`utils.py` 和新增测试脚本，也不改写受保护的 `cl.py`。这使安全与公共层修复可独立审阅、回滚和上线。

### 4.4 后续验收标准

1. 所有交易所适配器通过相同 OHLCV schema、时区、排序、去重和空数据契约测试。
2. 固定金样数据在重构前后产生相同分型、笔、线段、中枢、背驰和买卖点。
3. 回测严格禁止读取当前时刻之后的数据，同配置结果可复现。
4. 缓存采用原子写、schema/version 校验，外部输入不再使用 Pickle。
5. Web 开启强密码、HTTPS、CSRF、安全 Cookie 和请求限速，仓库扫描不再发现密钥。
6. CI 至少执行 compileall、pytest、Ruff、类型检查与依赖漏洞扫描。
