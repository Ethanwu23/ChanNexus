"""缠论核心的命令行计算入口。

入口支持两种互斥用法：读取外部 CSV 行情并输出完整计算快照，或通过
``--self-test`` 运行内置模拟行情检查。CSV 至少应包含 ``date``、``open``、
``close``、``high``、``low`` 和 ``volume`` 字段；计算结果以 UTF-8 JSON
写入标准输出，便于终端查看或交给其他程序继续处理。

本模块只负责任务参数解析和结果序列化，K 线规范化、缠论结构生成及信号计算
统一由 ``ChanEngine`` 完成。
"""

import argparse
import json

import pandas as pd

from chanlun_core import ChanEngine
from chanlun_core.selftest import run_self_test


def main() -> None:
    """解析命令行参数，执行自检或 CSV 行情计算并输出 JSON。"""
    parser = argparse.ArgumentParser(description="独立缠论计算器")
    parser.add_argument("csv", nargs="?", help="包含 date/open/close/high/low/volume 的 CSV")
    parser.add_argument("--code", default="UNKNOWN")
    parser.add_argument("--frequency", default="d")
    parser.add_argument("--self-test", action="store_true", help="运行内置模拟行情自测")
    args = parser.parse_args()

    # 自检模式不依赖外部行情文件，用于快速确认核心计算链路可以运行。
    if args.self_test:
        print(json.dumps(run_self_test(), ensure_ascii=False, indent=2))
        return
    if not args.csv:
        parser.error("必须提供 csv，或使用 --self-test")

    # CSV 模式将全部参数交给计算引擎，并输出可序列化的稳定快照。
    engine = ChanEngine(args.code, args.frequency).process_klines(pd.read_csv(args.csv))
    print(json.dumps(engine.snapshot(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
