#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
cd "$PROJECT_ROOT"

echo "项目目录: $PROJECT_ROOT"
test -f src/chanlun/cl_rebuilt.py
grep -q 'from chanlun.cl_rebuilt import CL' src/chanlun/cl.py

echo "即将删除的旧运行时文件："
find src/pyarmor_runtime_005445 -type f -print 2>/dev/null || true
find src -maxdepth 2 -type f \( -name '.pyarmor*' -o -name '*.rkey' -o -name '*.ikey' \) -print 2>/dev/null || true

rm -rf src/pyarmor_runtime_005445
rm -f src/.pyarmor.ikey

if find src -type f \( -name '*.rkey' -o -name '*.ikey' \) -print -quit | grep -q .; then
  echo "仍发现授权/构建密钥文件，请人工检查" >&2
  exit 1
fi

if grep -RIl '__pyarmor__\|pyarmor_runtime' src/chanlun --include='*.py' | grep -q .; then
  echo "业务源码仍包含旧运行时引用" >&2
  grep -RIn '__pyarmor__\|pyarmor_runtime' src/chanlun --include='*.py' >&2
  exit 1
fi

PYTHONPATH="$PROJECT_ROOT/src" "$PYTHON_BIN" - <<'PY'
from chanlun import cl
from chanlun.cl_rebuilt import CL
assert cl.CL is CL
print("核心入口校验通过:", cl.CL)
PY

echo "旧运行时清理完成"
