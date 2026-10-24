"""回测前 K线数据质量门禁。"""

import argparse

import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv")
    args = parser.parse_args()
    df = pd.read_csv(args.csv)
    required = {"date", "open", "close", "high", "low", "volume"}
    missing = required - set(df.columns)
    assert not missing, f"缺少字段: {sorted(missing)}"
    df["date"] = pd.to_datetime(df["date"], errors="raise")
    assert df["date"].is_monotonic_increasing, "日期必须升序"
    assert not df["date"].duplicated().any(), "日期存在重复"
    numeric = ["open", "close", "high", "low", "volume"]
    assert not df[numeric].isna().any().any(), "价格或成交量存在空值"
    assert (df["high"] >= df[["open", "close", "low"]].max(axis=1)).all(), "最高价非法"
    assert (df["low"] <= df[["open", "close", "high"]].min(axis=1)).all(), "最低价非法"
    print(f"数据通过: {len(df)} 行, {df.date.min()} -> {df.date.max()}")


if __name__ == "__main__":
    main()
