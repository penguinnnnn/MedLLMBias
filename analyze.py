#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys
import re
from typing import Optional, Sequence

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ---------------------------- Helpers ----------------------------
def is_categorical_dtype(s: pd.Series) -> bool:
    """Treat object, category, bool, or integer dtypes as categorical for plotting."""
    return (
        s.dtype == "object"
        or pd.api.types.is_categorical_dtype(s)
        or pd.api.types.is_bool_dtype(s)
        or pd.api.types.is_integer_dtype(s)
    )


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
    """Bin a numeric series. If only one unique non-null value, return as categorical strings."""
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


def is_numeric_column_name(name: str) -> bool:
    """Return True if the column name is purely digits like '123' or '007'."""
    if name is None:
        return False
    return bool(re.fullmatch(r"\s*\d+\s*", str(name)))


def should_skip_column(name: str, answer_col: str) -> bool:
    if name == answer_col:
        return True
    if str(name) == "Test":
        return True
    if is_numeric_column_name(str(name)):
        return True
    return False


# ---------------------------- Plotting ----------------------------
def plot_grouped_bars(
    ct: pd.DataFrame,
    feature_name: str,
    answer_col: str,
    out_png: str,
    mean_values: Optional[Sequence[float]] = None,
    mean_label: Optional[str] = None,
):
    """Plot grouped bars for counts; optionally overlay mean markers/line on a second y-axis.

    ct.index: feature categories (x). ct.columns: answer buckets/levels (series).
    mean_values: list/array aligned with ct.index order.
    """
    ct = ct.sort_index()
    n_groups = ct.shape[0]
    n_series = ct.shape[1]

    fig = plt.figure(figsize=(max(10, min(18, 0.6 * n_groups + 12)), 6))
    ax = fig.add_subplot(111)

    x = np.arange(n_groups)
    width = 0.8 / max(1, n_series)

    # Bars: counts
    bars = []
    for i, col in enumerate(ct.columns):
        bars.append(
            ax.bar(x + i * width, ct[col].values, width, label=str(col))
        )

    ax.set_title(f"{feature_name} × {answer_col} distribution", pad=10)
    ax.set_xlabel(feature_name)
    ax.set_ylabel("Count")
    ax.set_xticks(x + width * (n_series - 1) / 2)
    ax.set_xticklabels([str(idx) for idx in ct.index], rotation=30, ha="right")

    handles, labels = ax.get_legend_handles_labels()

    # Overlay mean of answer across feature categories, if provided
    if mean_values is not None:
        ax2 = ax.twinx()
        # Center markers in the middle of each group
        x_centers = x + width * (n_series - 1) / 2
        mean_line, = ax2.plot(x_centers, mean_values, marker="o", linestyle="-", label=mean_label or "Mean")
        ax2.set_ylabel(mean_label or f"Mean of {answer_col}")
        # Merge legends: bars + mean line
        handles = handles + [mean_line]
        labels = labels + [mean_label or f"Mean of {answer_col}"]

    ax.legend(handles, labels, title=answer_col, ncol=min(2, n_groups), frameon=False, loc='center left', bbox_to_anchor=(1.05, 0.5))

    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)


# ---------------------------- Main ----------------------------

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Analyze the relationship between an 'answer' column and all other columns, "
            "producing grouped bar charts and contingency tables."
        ),
    )
    parser.add_argument("--csv", required=True, help="Input CSV file path")
    parser.add_argument("--answer_col", default="answer", help="Name of the answer column (default: answer)")
    parser.add_argument("--output_dir", default="charts", help="Output folder for charts/tables (default: charts)")
    parser.add_argument("--numeric_bins", type=int, default=5, help="Number of quantile bins for float numeric feature columns")
    parser.add_argument("--answer_bins", type=int, default=5, help="If answer is float, number of quantile bins for the answer distribution")
    parser.add_argument("--max_categories", type=int, default=20, help="Max distinct values to keep for categorical features")
    parser.add_argument("--scenario_analysis", type=bool, default=False, help="Analyse all other traits based on Scenario")
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

    # Keep 'answer' as-is (no stripping). We'll keep an original numeric copy if float.
    # If not float, still convert to string for consistent crosstabs later when needed.
    # But we need two parallel representations: (a) possibly binned answer labels for counts, (b) numeric for means.
    answer_strings = ["ketorolac 60 mg IM",  "morphine 4 mg IV", "hydromorphone 1 mg IV", "hydromorphone 4 mg IV"]
    answer_series = df[answer_col].apply(lambda x: x[1:] if isinstance(x, str) and len(x) > 0 else answer_strings[x-1])


    # Determine if answer is float dtype and get numeric version for means
    is_answer_float = pd.api.types.is_float_dtype(answer_series)
    answer_numeric = None
    if is_answer_float:
        answer_numeric = answer_series.astype(float)
        # Create binned labels for answer to use in crosstabs
        answer_binned = bin_numeric_series(answer_numeric, args.answer_bins)
        df["__answer_for_ct__"] = answer_binned
        answer_label_for_legend = f"{answer_col} bins"
        mean_label = f"Mean of {answer_col}"
    else:
        # Use the original as string labels
        df["__answer_for_ct__"] = answer_series.astype(str).fillna("Missing")
        answer_label_for_legend = answer_col
        mean_label = None

    # Overall answer counts
    overall_counts = df["__answer_for_ct__"].value_counts(dropna=False).sort_index()
    overall_counts.to_csv(os.path.join(args.output_dir, "_overall_answer_counts.csv"), encoding="utf-8-sig")

    for col in df.columns:
        if should_skip_column(col, answer_col):
            continue

        s = df[col]

        # Prepare feature series (categorical index for crosstab), per v2 rules
        if is_categorical_dtype(s):
            s_proc = clip_to_top_n_categories(s, args.max_categories).fillna("Missing").astype(str)
            feature_label = str(col)
        elif pd.api.types.is_numeric_dtype(s):
            if pd.api.types.is_integer_dtype(s):
                s_proc = clip_to_top_n_categories(s, args.max_categories).fillna("Missing").astype(str)
                feature_label = str(col)
            else:
                s_proc = bin_numeric_series(s, args.numeric_bins)
                feature_label = f"{col} (binned)"
        else:
            s_proc = clip_to_top_n_categories(s.astype(str), args.max_categories)
            feature_label = str(col)

        if args.scenario_analysis:
            scenario_col = "Scenario"
            df_temp = pd.DataFrame({
                'Feature': s_proc,
                'Scenario_Answer': df[scenario_col].astype(str).fillna('Missing') + " - " + df["__answer_for_ct__"],
            })
            
            # The columns of ct are now 'Scenario1 - AnswerBin1', 'Scenario1 - AnswerBin2', 'Scenario2 - AnswerBin1', etc.
            feature_label_ct = feature_label
            answer_label_for_legend_ct = f"{scenario_col} x {answer_label_for_legend}"

        # Crosstab: feature categories vs (binned or original) answer labels
        ct = pd.crosstab(df_temp['Feature'], df_temp['Scenario_Answer'], dropna=False) if args.scenario_analysis else pd.crosstab(s_proc, df["__answer_for_ct__"], dropna=False)
        ct_path = os.path.join(args.output_dir, f"{col}__x__{answer_col}_crosstab.csv")
        ct.to_csv(ct_path, encoding="utf-8-sig")

        means_per_cat = None
        if args.scenario_analysis:
            mean_label_scenario = None
            if is_answer_float:
                # Group by the Feature and the Scenario, then calculate the mean of the numeric answer
                mean_df = (
                    df.groupby([s_proc.name, scenario_col], dropna=False)[answer_col]
                    .mean()
                    .unstack(fill_value=np.nan) # Unstack to get Scenario values as columns
                    .reindex(ct.index) # Align the index order with the crosstab
                )
                # Convert the DataFrame of means to a list of lists/array for plotting.
                # This requires modification to plot_grouped_bars (see step 3).
                means_per_cat = mean_df.values.T # Transpose to align with new plot logic
                mean_label_scenario = f"Mean of {answer_col} by {scenario_col}"
        else:
            # Compute mean answer per feature category (only if answer was float)
            if is_answer_float:
                # Align means with the category order used in ct.index
                means_per_cat = []
                for cat in ct.index:
                    mask = s_proc == str(cat)
                    # Note: s_proc was cast to str; compare as str
                    if mask.any():
                        means_per_cat.append(float(np.nanmean(answer_numeric[mask])))
                    else:
                        means_per_cat.append(np.nan)

        # Plot
        png_path = os.path.join(args.output_dir, f"{col}__x__{scenario_col}.png") if args.scenario_analysis else os.path.join(args.output_dir, f"{col}__x__{answer_col}.png")
        try:
            plot_grouped_bars(
                ct,
                feature_label,
                answer_label_for_legend,
                png_path,
                mean_values=means_per_cat,
                mean_label= mean_label_scenario if args.scenario_analysis else (mean_label if is_answer_float else None),
            )
        except Exception as e:
            err_path = os.path.join(args.output_dir, f"{col}__plot_error.txt")
            with open(err_path, "w", encoding="utf-8") as f:
                f.write(str(e))

    print(f"Done! Charts and tables are saved in: {os.path.abspath(args.output_dir)}")


if __name__ == "__main__":
    main()
