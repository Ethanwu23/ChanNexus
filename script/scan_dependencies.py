"""静态扫描Python导入，并检查当前解释器能否找到第三方模块。"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import sys
from pathlib import Path


PIP_NAMES = {
    "MyTT": "mytt", "akshare": "akshare", "alpaca": "alpaca-py",
    "apscheduler": "apscheduler", "baostock": "baostock", "ccxt": "ccxt",
    "dotenv": "python-dotenv", "dtaidistance": "dtaidistance",
    "empyrical": "empyrical-reloaded", "flask": "flask",
    "flask_login": "flask-login", "futu": "futu-api", "gm": "gm",
    "ib_insync": "ib-insync", "lark_oapi": "lark-oapi", "loguru": "loguru",
    "numpy": "numpy", "openai": "openai", "openctp_ctp": "openctp-ctp",
    "pandas": "pandas", "pinyin": "pinyin", "playwright": "playwright",
    "polygon": "polygon-api-client", "prettytable": "prettytable",
    "pyecharts": "pyecharts", "pyfolio": "pyfolio-reloaded",
    "pymysql": "pymysql", "pyquery": "pyquery", "pytdx": "pytdx",
    "pytz": "pytz", "redis": "redis", "requests": "requests",
    "rqdatac": "rqdatac", "sqlalchemy": "sqlalchemy", "talib": "TA-Lib",
    "tenacity": "tenacity", "tornado": "tornado", "tqdm": "tqdm",
    "tqsdk": "tqsdk", "tzlocal": "tzlocal", "vnpy": "vnpy",
    "vnpy_ctabacktester": "vnpy_ctabacktester", "vnpy_ctastrategy": "vnpy_ctastrategy",
    "vnpy_ctp": "vnpy_ctp", "vnpy_datamanager": "vnpy_datamanager",
    "vnpy_portfoliostrategy": "vnpy_portfoliostrategy", "wtpy": "wtpy",
    "xtquant": "xtquant",
}


def scan(root: Path) -> list[dict]:
    local = {item.name for item in (root / "src").iterdir() if item.is_dir()}
    local.update({"chanlun", "cl_app"})
    found: dict[str, set[str]] = {}
    for base in (root / "src", root / "web", root / "script"):
        for path in base.rglob("*.py"):
            if "static" in path.parts or "__pycache__" in path.parts:
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (UnicodeDecodeError, SyntaxError):
                continue
            modules = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    modules.add(node.module.split(".")[0])
            for module in modules - set(sys.stdlib_module_names) - local:
                found.setdefault(module, set()).add(str(path.relative_to(root)))
    return [
        {
            "module": module,
            "pip": PIP_NAMES.get(module, module.replace("_", "-")),
            "installed": importlib.util.find_spec(module) is not None,
            "used_by": sorted(paths),
        }
        for module, paths in sorted(found.items())
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="存在缺失依赖时返回状态1")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    dependencies = scan(root)
    missing = [item for item in dependencies if not item["installed"]]
    if args.json:
        print(json.dumps(dependencies, ensure_ascii=False, indent=2))
    else:
        for item in dependencies:
            state = "OK" if item["installed"] else "MISSING"
            print(f'{state:7} import {item["module"]:<25} pip install {item["pip"]}')
        if missing:
            packages = " ".join(sorted({item["pip"] for item in missing}))
            print("\n缺失依赖一键安装：")
            print(f'"{sys.executable}" -m pip install {packages}')
        print(f"\n共发现 {len(dependencies)} 个第三方模块，缺失 {len(missing)} 个")
    return 1 if args.check and missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
