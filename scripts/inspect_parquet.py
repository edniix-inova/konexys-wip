#!/usr/bin/env python3
"""Lightweight utility to explore Parquet files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Open a Parquet file and print summary statistics.",
    )
    parser.add_argument(
        "parquet_path",
        type=Path,
        help="Path to the Parquet file to inspect.",
    )
    parser.add_argument(
        "--columns",
        nargs="+",
        help="Optional subset of columns to read (default: all columns).",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=5,
        help="Number of rows to show from the top of the file.",
    )
    parser.add_argument(
        "--describe",
        action="store_true",
        help="Show pandas describe output for numeric columns.",
    )
    return parser.parse_args()


def format_percent(value: float) -> str:
    return f"{value:.2f}%" if value is not None else "n/a"


def main() -> int:
    args = parse_args()
    path = args.parquet_path

    if not path.exists():
        print(f"ERROR: file does not exist: {path}", file=sys.stderr)
        return 1
    if path.is_dir():
        print(f"ERROR: expected file but got directory: {path}", file=sys.stderr)
        return 1

    read_kwargs = {}
    if args.columns:
        read_kwargs["columns"] = args.columns

    df = pd.read_parquet(path, **read_kwargs)
    row_count = len(df)
    col_count = len(df.columns)

    print("Parquet summary")
    print("--------------")
    print(f"File: {path}")
    print(f"Rows: {row_count}")
    print(f"Columns: {col_count}")
    if args.columns:
        print(f"Read columns: {', '.join(args.columns)}")

    if row_count == 0:
        print("(file contains no rows)")
        return 0

    dtype_table = df.dtypes.astype(str).to_frame("dtype")

    null_counts = df.isna().sum()
    dtype_table["nulls"] = null_counts
    dtype_table["null_percent"] = (
        (null_counts / row_count) * 100
    ).round(2)
    dtype_table["null_percent"] = dtype_table["null_percent"].map(format_percent)

    dtype_table["unique"] = df.nunique(dropna=False)

    print("\nColumn overview:")
    print(dtype_table.to_string())

    print("\nTop rows:")
    print(df.head(args.sample).to_string(index=False))

    if args.describe:
        print("\nDescribe (numeric):")
        print(df.describe().to_string())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
