"""为新旧核心生成可比较的公开业务快照。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def _round(value):
    return round(float(value), 8) if value is not None else None


def build_snapshot(cd) -> dict:
    return {
        "code": cd.get_code(),
        "frequency": cd.get_frequency(),
        "counts": {
            "src": len(cd.get_src_klines()), "cl": len(cd.get_cl_klines()),
            "fx": len(cd.get_fxs()), "bi": len(cd.get_bis()), "xd": len(cd.get_xds()),
            "zsd": len(cd.get_zsds()), "bi_zs": len(cd.get_bi_zss()), "xd_zs": len(cd.get_xd_zss()),
        },
        "fxs": [[fx.type, fx.k.date.isoformat(), _round(fx.val), bool(fx.done)] for fx in cd.get_fxs()],
        "bis": [[bi.type, bi.start.k.date.isoformat(), bi.end.k.date.isoformat(),
                 _round(bi.high), _round(bi.low), bool(bi.is_done()), sorted(bi.line_mmds("|")), sorted(bi.line_bcs("|"))]
                for bi in cd.get_bis()],
        "xds": [[xd.type, xd.start.k.date.isoformat(), xd.end.k.date.isoformat(),
                 _round(xd.high), _round(xd.low), bool(xd.is_done()), sorted(xd.line_mmds("|")), sorted(xd.line_bcs("|"))]
                for xd in cd.get_xds()],
        "bi_zss": [[_round(zs.zg), _round(zs.zd), _round(zs.gg), _round(zs.dd),
                    int(zs.line_num), int(zs.level), bool(zs.done), bool(zs.real)] for zs in cd.get_bi_zss()],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="生成核心公开业务快照")
    parser.add_argument("csv")
    parser.add_argument("output")
    parser.add_argument("--code", default="TEST")
    parser.add_argument("--frequency", default="d")
    parser.add_argument("--config", default="{}", help="JSON 格式缠论配置")
    args = parser.parse_args()
    from chanlun import cl

    data = pd.read_csv(args.csv)
    data["date"] = pd.to_datetime(data["date"])
    cd = cl.CL(args.code, args.frequency, json.loads(args.config)).process_klines(data)
    Path(args.output).write_text(json.dumps(build_snapshot(cd), ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
