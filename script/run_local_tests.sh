#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$ROOT"
export PYTHONPATH="$ROOT/src"

python -m compileall -q src web/chanlun_chart script
python -m unittest -v \
  tests/test_chanlun_core.py \
  tests/test_characterization.py \
  tests/test_cl_rebuilt.py \
  tests/test_fastapi_app.py \
  tests/test_fun.py \
  tests/test_web_contract.py \
  tests/test_web_entry.py
python -m chanlun_core_cli --self-test > /tmp/chanlun-selftest.json
python -m json.tool /tmp/chanlun-selftest.json >/dev/null
echo "单元测试、语法检查、模拟行情自测全部通过"
