#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Usage example:
python analyze_answer_en.py --csv data.csv --answer_col answer --output_dir charts --numeric_bins 5 --max_categories 20

Features:
- Reads a CSV and analyzes how the 'answer' column (one of four options) relates to every other column.
- For each non-answer column:
  * If categorical/bool: directly plots grouped bar chart (feature value × answer).
  * If numeric: bin into quantiles (default 5 bins), then plot.
- Also exports each contingency table as CSV.
- Automatically removes the **first character** from every 'answer' entry.
"""

import argparse
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def is_categorical_dtype(s: pd.Series) -> bool:
    return s.dtype == "object" or pd.api.types.is_categorical_dtype(s) or pd.api.types.is_bool_dtype(s)


def safe_value_counts(s: pd.Series) -> pd.Series:
    return s.fillna("Missing").astype(str).value_counts(dropna=False)


def clip_to_top_n_categories(s: pd.Series, top_n: int) -> pd.Series:
    if top_n is None or top_n <= 0:
        return s
    vc = safe_value_counts(s)
    if len(vc) <= top_n:
        return s.fillna("Missing").astype(str)
    keep = set(vc.head(top_n).index.astype(str))
    s2 = s.fillna("Missing").astype(str).apply(lambda x: x if x in keep else "Other")
    return s2


def bin_numeric_series(s: pd.Series, q: int) -> pd.Series:
    if s.dropna().nunique() <= 1:
        return s.astype(object).fillna("Missing")
    try:
        binned = pd.qcut(s, q=q, duplicates="drop")
        return binned.astype(str).fillna("Missing")
    except Exception:
        try:
            binned = pd.cut(s, bins=q)
            return binned.astype(str).fillna("Missing")
        except Exception:
            return s.astype(object).fillna("Missing")


def plot_grouped_bars(ct: pd.DataFrame, feature_name: str, answer_col: str, out_png: str):
    ct = ct.sort_index()
    n_groups = ct.shape[0]
    n_series = ct.shape[1]

    fig = plt.figure(figsize=(max(6, min(18, 0.6 * n_groups + 4)), 6))
    ax = fig.add_subplot(111)

    x = np.arange(n_groups)
    width = 0.8 / max(1, n_series)

    for i, col in enumerate(ct.columns):
        ax.bar(x + i * width, ct[col].values, width, label=str(col))

    ax.set_title(f"{feature_name} × {answer_col} distribution", pad=10)
    ax.set_xlabel(feature_name)
    ax.set_ylabel("Count")
    ax.set_xticks(x + width * (n_series - 1) / 2)
    ax.set_xticklabels([str(idx) for idx in ct.index], rotation=30, ha="right")
    ax.legend(title=answer_col, ncol=min(4, n_groups), frameon=False)

    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze the relationship between 'answer' column and all other columns, "
                    "producing grouped bar charts and contingency tables.",
    )
    parser.add_argument("--csv", required=True, help="Input CSV file path")
    parser.add_argument("--answer_col", default="answer", help="Name of the answer column (default: answer)")
    parser.add_argument("--output_dir", default="charts", help="Output folder for charts/tables (default: charts)")
    parser.add_argument("--numeric_bins", type=int, default=5, help="Number of quantile bins for numeric features")
    parser.add_argument("--max_categories", type=int, default=20, help="Max distinct values to keep for categorical features")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    try:
        df = pd.read_csv(args.csv)
    except Exception as e:
        print(f"Failed to read CSV: {e}", file=sys.stderr)
        sys.exit(1)

    if args.answer_col not in df.columns:
        print(f"Answer column not found: {args.answer_col}", file=sys.stderr)
        sys.exit(1)

    answer_col = args.answer_col
    df[answer_col] = df[answer_col].astype(str).fillna("Missing")

    # Remove first character from each answer
    df[answer_col] = df[answer_col].apply(lambda x: x[1:] if isinstance(x, str) and len(x) > 0 else x)

    # Counts the frequency of each answer
    ans_counts = df[answer_col].value_counts(dropna=False).sort_index()
    ans_counts.to_csv(os.path.join(args.output_dir, "_overall_answer_counts.csv"), encoding="utf-8-sig")

    for col in df.columns:
        if col == answer_col:
            continue

        s = df[col]
        # If categorical or boolean
        if is_categorical_dtype(s):
            s_proc = clip_to_top_n_categories(s, args.max_categories)
            s_proc = s_proc.fillna("Missing").astype(str)
            feature_label = col
        # bin if numerical
        elif pd.api.types.is_numeric_dtype(s):
            s_proc = bin_numeric_series(s, args.numeric_bins)
            feature_label = f"{col} (binned)"
        else:
            s_proc = clip_to_top_n_categories(s.astype(str), args.max_categories)
            feature_label = col

        ct = pd.crosstab(s_proc, df[answer_col], dropna=False)
        ct_path = os.path.join(args.output_dir, f"{col}__x__{answer_col}_crosstab.csv")
        ct.to_csv(ct_path, encoding="utf-8-sig")

        png_path = os.path.join(args.output_dir, f"{col}__x__{answer_col}.png")
        try:
            plot_grouped_bars(ct, feature_label, answer_col, png_path)
        except Exception as e:
            err_path = os.path.join(args.output_dir, f"{col}__plot_error.txt")
            with open(err_path, "w", encoding="utf-8") as f:
                f.write(str(e))

    print(f"Done! Charts and tables are saved in: {os.path.abspath(args.output_dir)}")


if __name__ == "__main__":
    main()
