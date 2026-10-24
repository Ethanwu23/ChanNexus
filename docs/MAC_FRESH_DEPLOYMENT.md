# ChanNexus：macOS 全新部署、测试与排障

以下命令默认仓库位于 `$HOME/projects/ChanNexus`，新核心已经固定为 `chanlun.cl` 的实现，不再需要旧运行时。本工作树已执行过清理脚本；本节命令用于在其他副本重复清理和自检。

## 1. 清理旧运行时

脚本会永久删除旧文件；已确认有备份时直接执行：

```bash
export PROJECT_ROOT="$HOME/projects/ChanNexus"
cd "$PROJECT_ROOT"
chmod +x script/cleanup_legacy_runtime.sh
./script/cleanup_legacy_runtime.sh "$PROJECT_ROOT"
```

清理后校验：

```bash
test ! -e src/pyarmor_runtime_005445
test ! -e src/.pyarmor.ikey
! grep -RIn '__pyarmor__\|pyarmor_runtime' src/chanlun --include='*.py'
PYTHONPATH="$PWD/src" python3 -c 'from chanlun import cl; print(cl.__file__, cl.CL)'
```

预期入口文件为 `src/chanlun/cl.py`，`CL` 来自 `chanlun.cl_rebuilt`。

## 2. Python 环境、依赖、目录和配置

### 2.1 安装系统组件

```bash
xcode-select -p || xcode-select --install
python3.11 -V
uname -m
```

Apple Silicon 应显示 `arm64`；Intel Mac 显示 `x86_64`。Python 和二进制扩展必须与系统架构一致。

若后续安装 TA-Lib 时提示缺少系统库，再执行：

```bash
brew install ta-lib libomp
```

### 2.2 创建 `chanlun-rewrite` 虚拟环境

```bash
export PROJECT_ROOT="$HOME/projects/ChanNexus"
cd "$PROJECT_ROOT"
mkdir -p "$HOME/.venvs"
python3.11 -m venv "$HOME/.venvs/chanlun-rewrite"
source "$HOME/.venvs/chanlun-rewrite/bin/activate"
python -m pip install --upgrade pip setuptools wheel
python -V
python -c 'import platform,sys; print(platform.machine(), sys.executable)'
```

以后每个新终端先执行：

```bash
cd "$HOME/projects/ChanNexus"
source "$HOME/.venvs/chanlun-rewrite/bin/activate"
export PYTHONPATH="$PWD/src"
```

### 2.3 安装依赖

不要在 macOS 直接运行 `uv sync`：当前 `pyproject.toml` 的 TA-Lib source 指向 Windows wheel；旧锁文件已随旧运行环境删除。完成平台依赖整理后，可在 Mac 上重新生成新的锁文件。

算法和测试最小依赖：

```bash
python -m pip install \
  'numpy==1.26.4' 'pandas==2.1.0' 'scipy>=1.15.3' \
  pytz tzlocal TA-Lib
```

Web图表、新核心和默认行情源的一键依赖：

```bash
python -m pip install -r requirements-web.txt
python -m pip install package/pytdx-1.72r2-py3-none-any.whl
python script/scan_dependencies.py
```

所有市场、回测与可选框架的全项目依赖：

```bash
python -m pip install -r requirements.txt
python -m pip install package/pytdx-1.72r2-py3-none-any.whl
python -m pip check
```

依赖扫描器会遍历 `src/`、`web/` 和 `script/`。VNPY、WTPY、QMT、CTP、
掘金等未启用框架允许显示 `MISSING`；基础Web实际导入的依赖必须全部为 `OK`。

若 CTP、QMT、VNPY 或 WTPY 等平台 SDK 在 Mac 安装失败，而本机不使用对应实盘接口，可以先跳过该 SDK。基础 Web 依赖可单独安装：

```bash
python -m pip install \
  flask flask-login tornado gevent apscheduler sqlalchemy pymysql redis dbutils \
  requests tenacity prettytable tqdm pyecharts pyarrow matplotlib \
  ccxt baostock akshare openai lark-oapi MyTT dtaidistance
```

### 2.4 配置与数据目录

```bash
cd "$PROJECT_ROOT"
test -f src/chanlun/config.py || cp src/chanlun/config.py.demo src/chanlun/config.py
chmod 600 src/chanlun/config.py
mkdir -p "$HOME/.channexus"/{logs,klines,cl_data,cache_pkl,backtests}
chmod -R u+rwX,go-rwx "$HOME/.channexus"
export CHANLUN_WEB_SECRET_KEY="$(openssl rand -hex 32)"
```

首次本机启动建议配置：

```python
WEB_HOST = "127.0.0.1"
WEB_PORT = 9910
LOGIN_PWD = ""
DATA_PATH = ".channexus"
DB_TYPE = "sqlite"
DB_DATABASE = "chanlun_klines"
REDIS_HOST = ""
PROXY_HOST = ""
```

配置检查：

```bash
PYTHONPATH="$PWD/src" python - <<'PY'
from chanlun import cl, config
from chanlun.config import get_data_path
print("核心:", cl.CL)
print("WEB:", config.WEB_HOST)
print("DB:", config.DB_TYPE, config.DB_DATABASE)
print("DATA:", get_data_path().resolve())
assert config.WEB_HOST in ("127.0.0.1", "localhost")
PY
```

## 3. 三层测试

### 3.1 单元和算法自测

```bash
cd "$PROJECT_ROOT"
source "$HOME/.venvs/chanlun-rewrite/bin/activate"
export PYTHONPATH="$PWD/src"
chmod +x script/run_local_tests.sh
./script/run_local_tests.sh
```

等价的展开命令：

```bash
python -m compileall -q src web/chanlun_chart script
python -m unittest -v tests/test_chanlun_core.py tests/test_cl_rebuilt.py tests/test_fun.py tests/test_web_entry.py
python -m chanlun_core_cli --self-test > /tmp/chanlun-selftest.json
python -m json.tool /tmp/chanlun-selftest.json | sed -n '1,60p'
```

预期：16项测试通过；模拟行情生成360根源K线，且合并K、分型、笔、线段和中枢数量均合理。

依赖自检和单库导入验证：

```bash
python script/scan_dependencies.py
python - <<'PY'
import pandas, pytz, numpy, talib, loguru, dotenv, tornado, pinyin
print('pandas', pandas.__version__)
print('numpy', numpy.__version__)
print('TA-Lib', talib.__version__)
print('tornado', tornado.version)
print('八项基础依赖导入正常')
PY
```

### 3.2 模块联调

核心兼容接口：

```bash
python - <<'PY'
from chanlun import cl
from chanlun_core.selftest import simulated_klines
cd = cl.CL('SIM.TEST', 'd', {'bi_type':'bi_type_dd'}).process_klines(simulated_klines())
print(len(cd.get_src_klines()), len(cd.get_cl_klines()))
print(len(cd.get_fxs()), len(cd.get_bis()), len(cd.get_xds()))
print(len(cd.get_bi_zss()), len(cd.get_xd_zss()))
assert len(cd.get_idx()['macd']['hist']) == len(cd.get_src_klines())
assert cd.get_bis()[-1].start.k.k_index >= 0
PY
```

SQLite：

```bash
python - <<'PY'
from chanlun.db import db
db.cache_set('__smoke_test', 'ok')
assert db.cache_get('__smoke_test') == 'ok'
print('数据库缓存正常')
PY
```

Flask应用构造，不监听端口：

```bash
PYTHONPATH="$PWD/src:$PWD/web/chanlun_chart" python - <<'PY'
from cl_app import create_app
app = create_app({'TESTING': True})
rules = list(app.url_map.iter_rules())
print('路由数:', len(rules))
assert len(rules) > 10
PY
```

行情适配器应按实际市场单独测试，网络失败与算法失败分开处理：

```bash
python - <<'PY'
from chanlun.base import Market
from chanlun.exchange import get_exchange
ex = get_exchange(Market.A)
print(type(ex).__name__, len(ex.all_stocks()))
PY
```

### 3.3 全项目启动

```bash
lsof -nP -iTCP:9910 -sTCP:LISTEN || true
cd "$PROJECT_ROOT"
source "$HOME/.venvs/chanlun-rewrite/bin/activate"
export PYTHONPATH="$PWD/src"
export CHANLUN_WEB_SECRET_KEY="${CHANLUN_WEB_SECRET_KEY:-$(openssl rand -hex 32)}"
python web/chanlun_chart/app.py nobrowser 2>&1 | tee "$HOME/.channexus/logs/web-console.log"
```

另开终端验证：

```bash
curl -I --max-time 10 http://127.0.0.1:9910/login
tail -n 100 "$HOME/.channexus/logs/web-console.log"
```

通过标准：进程持续运行、控制台出现 `启动成功`、9910端口处于LISTEN、HTTP
返回200或登录跳转状态，且日志没有 `DEPENDENCY_ERROR`、Traceback或进程退出。

浏览器访问 `http://127.0.0.1:9910`。停止服务使用启动终端的 `Ctrl+C`。

后台运行：

```bash
cd "$PROJECT_ROOT"
nohup env PYTHONPATH="$PWD/src" CHANLUN_WEB_SECRET_KEY="$CHANLUN_WEB_SECRET_KEY" \
  "$HOME/.venvs/chanlun-rewrite/bin/python" web/chanlun_chart/app.py nobrowser \
  >> "$HOME/.channexus/logs/web-out.log" \
  2>> "$HOME/.channexus/logs/web-error.log" &
echo $! > "$HOME/.channexus/web.pid"
```

安全停止：

```bash
kill "$(cat "$HOME/.channexus/web.pid")"
```

## 4. 无旧程序时的人工算法校验

没有历史快照时不能做逐点参照，应从结构不变量、标准形态和经济合理性三方面验收。

### 4.1 自动不变量

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
python -m chanlun_core_cli --self-test > /tmp/selftest.json
```

检查：日期有序无重复；合并K不多于源K；顶底分型交替；笔方向交替；线段至少三笔；中枢满足 `zg >= zd`；重复和分批喂入结果一致。

### 4.2 建立新的固定基准

```bash
mkdir -p tests/golden
cp /tmp/selftest.json tests/golden/selftest.json
python -m chanlun_core_cli --self-test > /tmp/selftest-new.json
diff -u tests/golden/selftest.json /tmp/selftest-new.json
```

只有明确修改算法规则时才能更新基准，并记录分型、笔、线段或信号为什么变化。

### 4.3 人工图形检查表

至少构造并画出以下行情：单边上涨、单边下跌、箱体震荡、V形反转、倒V反转、相邻K线包含、跳空、最后一笔未确认、三笔重叠、离开中枢后不回抽。

逐层检查：

1. 包含合并方向是否符合前序趋势。
2. 顶分型中间K线高点最高，底分型低点最低。
3. 笔端点是交替分型，并满足配置的最小K线数。
4. 线段由至少三笔构成，端点位于有效笔端点。
5. 中枢前三线存在公共价格区间，`zg=min(high)`、`zd=max(low)`。
6. 三买必须是向上离开后向下回抽不进入 `zg`；三卖反向。
7. 背驰必须同时检查价格创新高低和力度减弱，不能只看MACD。
8. 末端未完成结构允许变化，历史确认结构不应无故漂移。

### 4.4 K线质量门禁

```bash
PYTHONPATH="$PWD/src" python script/check_market_csv.py /path/to/klines.csv
```

## 5. 常见错误

| 错误 | 原因与解决 |
|---|---|
| `No module named chanlun` | `export PYTHONPATH="$PROJECT_ROOT/src"` |
| `[DEPENDENCY_ERROR] 缺少Python模块` | 复制提示中的pip命令，并确认使用chanlun-rewrite解释器 |
| `No module named chanlun.config` | 复制 `config.py.demo` 为 `config.py` |
| Python版本错误 | 激活 `chanlun-rewrite` 后检查 `which python; python -V` |
| `incompatible architecture` | arm64/x86_64混装；删除并重建 `~/.venvs/chanlun-rewrite` |
| TA-Lib编译失败 | `brew install ta-lib` 后重新 `pip install TA-Lib` |
| 缺少 scipy/tzlocal | `python -m pip install scipy tzlocal` |
| 缺少 pytdx | 安装仓库 `package/pytdx-1.72r2-py3-none-any.whl` |
| CTP/QMT/VNPY安装失败 | 对应SDK不支持Mac；不用该接口时跳过 |
| 仍出现旧运行时异常 | 检查 `src/chanlun/cl.py` 和清理脚本校验结果 |
| 9910端口占用 | 修改 `config.WEB_PORT`，再用 `lsof -nP -iTCP:9910 -sTCP:LISTEN` 检查 |
| SQLite locked | 避免多进程共写；子进程分别输出文件再汇总 |
| Redis拒绝连接 | 启动Redis或设置 `REDIS_HOST=''` |
| 行情为空 | 检查交易时段、代码、周期和数据源网络，不要归因于算法 |
| datetime比较失败 | 统一 `pd.to_datetime` 与市场时区，禁止字符串日期排序 |
| K线字段错误 | 必须有 `date/open/close/high/low/volume` |
| 分型/笔末端变化 | 区分未完成结构和确认结构；检查配置是否改变 |
| 回测不复现 | 固定输入排序、随机种子、配置和并发合并顺序 |
| Web白屏 | 查浏览器Network/Console及Web错误日志 |
| macOS杀进程 | 检查内存、二进制架构并降低并发和数据窗口 |

快速诊断：

```bash
which python
python -V
python -m pip -V
python -m pip check
python -c 'import platform; print(platform.machine())'
python -c 'from chanlun import cl; print(cl.__file__, cl.CL)'
python script/scan_dependencies.py
git status --short
grep -RInE 'ERROR|CRITICAL|Traceback|Exception' "$HOME/.channexus/logs" | tail -n 100
log show --last 10m --style compact --predicate 'process == "Python" OR process == "python3"' | tail -n 100
```

## 6. 日志和批量回测脚本

建议日志目录：

```text
~/.channexus/logs/web-out.log
~/.channexus/logs/web-error.log
~/.channexus/logs/algorithm.log
~/.channexus/logs/market-data.log
~/.channexus/logs/backtest.log
```

日志必须包含市场、代码、周期、任务ID、最后K线时间和异常堆栈；禁止记录密码、Token和完整账号。

```bash
tail -F "$HOME/.channexus/logs/web-out.log" "$HOME/.channexus/logs/web-error.log"
grep -RInE 'ERROR|CRITICAL|Traceback' "$HOME/.channexus/logs" | tail -n 200
```

批量算法/回测模板：

```bash
export PYTHONPATH="$PROJECT_ROOT/src"
python script/run_batch_backtest.py data/history/*.csv \
  --workers 4 \
  --output "$HOME/.channexus/backtests/run-$(date +%Y%m%d-%H%M%S)"
```

脚本会为每个标的生成独立JSON和汇总文件，避免多个进程竞争SQLite。将其中 `run_one()` 替换成具体 `BackTest` 配置即可复用并发、异常和输出框架。

批量回测应逐步扩大：

```text
1标的 × 1个月 × 1组参数
3标的 × 1年 × 3组参数
完整标的池 × 完整区间 × 分批参数
```

运行前记录环境：

```bash
RUN_DIR="$HOME/.channexus/backtests/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$RUN_DIR"
python -V > "$RUN_DIR/environment.txt"
python -m pip freeze >> "$RUN_DIR/environment.txt"
git rev-parse HEAD >> "$RUN_DIR/environment.txt"
```

资源监控：

```bash
ps -Ao pid,ppid,%cpu,%mem,rss,etime,command | grep -E 'python|chanlun' | grep -v grep
top -o mem
du -sh "$HOME/.channexus"/* 2>/dev/null | sort -h
```

CPU密集任务并发建议不超过 `os.cpu_count() - 1`；完整DataFrame不要反复在进程间复制；历史行情优先保存为Parquet；参数组合分批生成，不一次展开巨大笛卡尔积。
