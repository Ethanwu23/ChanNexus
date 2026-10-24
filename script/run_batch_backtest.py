"""批量任务模板：隔离输出、限制并发、完整记录失败堆栈。

将 run_one 中的示例计算替换为具体 BackTest 配置即可。
"""

import argparse
import concurrent.futures
import json
import os
import traceback
from datetime import datetime
from pathlib import Path

import pandas as pd

from chanlun import cl


def run_one(csv: str, output_dir: str) -> dict:
    path = Path(csv)
    try:
        data = pd.read_csv(path)
        data["date"] = pd.to_datetime(data["date"])
        cd = cl.CL(path.stem, "d", {}).process_klines(data)
        result = {
            "file": str(path), "ok": True, "bars": len(cd.get_src_klines()),
            "fxs": len(cd.get_fxs()), "bis": len(cd.get_bis()),
            "xds": len(cd.get_xds()), "zss": len(cd.get_bi_zss()),
        }
    except Exception as exc:
        result = {"file": str(path), "ok": False, "error": str(exc), "traceback": traceback.format_exc()}
    target = Path(output_dir) / f"{path.stem}.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", help="一个或多个 CSV")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    parser.add_argument("--output", default=f"data/batch-{datetime.now():%Y%m%d-%H%M%S}")
    args = parser.parse_args()
    Path(args.output).mkdir(parents=True, exist_ok=True)
    if args.workers == 1:
        # 单进程模式便于调试，且不使用 POSIX semaphore。
        results = [run_one(item, args.output) for item in args.inputs]
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(run_one, item, args.output) for item in args.inputs]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
    summary = {"total": len(results), "ok": sum(item["ok"] for item in results), "failed": sum(not item["ok"] for item in results)}
    (Path(args.output) / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
