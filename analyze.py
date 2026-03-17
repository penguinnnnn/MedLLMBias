import os
import argparse
from typing import List

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


FEATURE_COLUMNS = ["Scenario", "Name", "Age", "Race", "Gender", "SO"]


def read_data(csv_path: str) -> pd.DataFrame:
    """Read CSV file with header into a DataFrame."""
    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)
    return df


def ensure_columns(df: pd.DataFrame, answer_col: str, features: List[str]) -> List[str]:
    """Check which feature columns exist and return valid ones.

    Raises if answer_col does not exist.
    """
    if answer_col not in df.columns:
        raise KeyError(f"answer column '{answer_col}' not found in CSV. Columns: {list(df.columns)}")

    valid_features = []
    for col in features:
        if col in df.columns:
            valid_features.append(col)
        else:
            print(f"[WARN] Feature column '{col}' not found in CSV. Skipping.")
    if not valid_features:
        raise ValueError("None of the specified feature columns were found in the CSV.")
    return valid_features


def get_output_path(csv_path: str, feature: str) -> str:
    """Construct PDF output path next to CSV.

    Example: A.csv + feature 'Scenario' -> A_Scenario.pdf
    """
    base_dir = os.path.dirname(os.path.abspath(csv_path))
    base_name = os.path.splitext(os.path.basename(csv_path))[0]
    out_name = f"{base_name}_{feature}.pdf"
    return os.path.join(base_dir, out_name)


def plot_discrete_answer(
    df: pd.DataFrame,
    csv_path: str,
    answer_col: str,
    feature_columns: List[str],
) -> None:
    """For each feature, plot grouped bar chart of answer distribution.

    x-axis: feature values
    grouped bars: answer categories
    y-axis: count
    """
    for feature in feature_columns:
        # Drop rows with NA in feature or answer
        sub = df[[feature, answer_col]].dropna()
        if sub.empty:
            print(f"[WARN] No data for feature '{feature}' after dropping NA. Skipping.")
            continue

        # Treat both as categorical
        sub[feature] = sub[feature].astype(str)
        sub[answer_col] = sub[answer_col].astype(str)

        # contingency table: rows = feature values, cols = answer categories
        ctab = pd.crosstab(sub[feature], sub[answer_col])

        if ctab.empty:
            print(f"[WARN] Crosstab for feature '{feature}' is empty. Skipping.")
            continue

        fig, ax = plt.subplots(figsize=(10, 6))

        # Grouped bar plot: index (x) = feature values, columns = answer categories
        ctab.plot(kind="bar", ax=ax)

        ax.set_title(f"Distribution of '{answer_col}' by {feature}")
        ax.set_xlabel(feature)
        ax.set_ylabel("Count")
        ax.legend(title=answer_col, bbox_to_anchor=(1.04, 1), loc="upper left")

        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

        out_path = get_output_path(csv_path, feature)
        fig.savefig(out_path)
        plt.close(fig)
        print(f"[INFO] Saved discrete-answer figure: {out_path}")


def compute_bins_for_continuous(series: pd.Series, bin_size: float = 5.0):
    """Compute global bin edges (size = bin_size) for a numeric series."""
    if series.empty:
        raise ValueError("Series is empty; cannot compute bins.")

    min_val = np.nanmin(series.values)
    max_val = np.nanmax(series.values)

    if np.isnan(min_val) or np.isnan(max_val):
        raise ValueError("Series contains only NaNs; cannot compute bins.")

    # Round down / up to nearest bin_size
    start = np.floor(min_val / bin_size) * bin_size
    end = np.ceil(max_val / bin_size) * bin_size
    if start == end:
        # force at least one bin
        end = start + bin_size

    bins = np.arange(start, end + bin_size, bin_size)
    return bins


def plot_continuous_answer(
    df: pd.DataFrame,
    csv_path: str,
    answer_col: str,
    feature_columns: List[str],
    bin_size: float = 5.0,
) -> None:
    """For each feature, plot grouped bar chart of binned counts + mean line.

    x-axis: feature values
    grouped bars: bins of answer (size = bin_size)
    left y-axis: count in each bin
    right y-axis: mean(answer) for each feature value
    """
    # Make sure answer is numeric
    numeric = pd.to_numeric(df[answer_col], errors="coerce")
    df = df.copy()
    df[answer_col] = numeric

    # Global bins across all rows
    bins = compute_bins_for_continuous(df[answer_col].dropna(), bin_size=bin_size)
    bin_labels = [f"[{bins[i]}, {bins[i+1]})" for i in range(len(bins) - 1)]

    for feature in feature_columns:
        # Drop rows with NA in feature or answer
        sub = df[[feature, answer_col]].dropna()
        if sub.empty:
            print(f"[WARN] No valid data for feature '{feature}' after dropping NA. Skipping.")
            continue

        # Cast feature to string (categorical)
        sub[feature] = sub[feature].astype(str)

        # Bin the answer
        sub["_bin"] = pd.cut(sub[answer_col], bins=bins, labels=bin_labels, include_lowest=True, right=False)

        # Count per (feature value, bin)
        counts = (
            sub.groupby([feature, "_bin"]).size().unstack("_bin").reindex(columns=bin_labels, fill_value=0)
        )

        if counts.empty:
            print(f"[WARN] No binned counts for feature '{feature}'. Skipping.")
            continue

        # Mean per feature value
        means = sub.groupby(feature)[answer_col].mean().reindex(counts.index)

        fig, ax = plt.subplots(figsize=(10, 6))

        # Grouped bar plot: x-axis = feature values, grouped bars for each bin
        counts.plot(kind="bar", ax=ax)

        ax.set_xlabel(feature)
        ax.set_ylabel("Count")
        ax.set_title(f"Binned distribution of '{answer_col}' (bin={bin_size}) and mean by {feature}")

        # Secondary axis for means
        ax2 = ax.twinx()
        x_positions = np.arange(len(counts.index))
        ax2.plot(x_positions, means.values, marker="o", linestyle="-", label="Mean of answer")
        ax2.set_ylabel(f"Mean of {answer_col}")

        # Align x ticks with feature values
        ax.set_xticklabels(counts.index, rotation=45, ha="right")

        # Combine legends from both axes
        handles1, labels1 = ax.get_legend_handles_labels()
        handles2, labels2 = ax2.get_legend_handles_labels()
        # For clarity, rename the grouped-bars legend title
        ax.legend(handles1, labels1, title=f"{answer_col} bins", bbox_to_anchor=(1.04, 1), loc="upper left")
        ax2.legend(handles2, labels2, loc="upper right")

        plt.tight_layout()

        out_path = get_output_path(csv_path, feature)
        fig.savefig(out_path)
        plt.close(fig)
        print(f"[INFO] Saved continuous-answer figure: {out_path}")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Analyze answer distribution by discrete feature columns and save grouped bar charts as PDFs."
        )
    )
    parser.add_argument("csv_path", help="Path to the input CSV file (with header)")
    parser.add_argument(
        "--answer-col",
        default="answer",
        help="Name of the answer column (default: 'answer')",
    )
    parser.add_argument(
        "--answer-type",
        choices=["discrete", "continuous"],
        required=True,
        help="Specify whether the answer column is 'discrete' or 'continuous'",
    )
    parser.add_argument(
        "--bin-size",
        type=float,
        default=5.0,
        help="Bin size for continuous answer (default: 5.0)",
    )

    args = parser.parse_args()

    df = read_data(args.csv_path)

    # Validate columns
    features = ensure_columns(df, args.answer_col, FEATURE_COLUMNS)

    if args.answer_type == "discrete":
        plot_discrete_answer(df, args.csv_path, args.answer_col, features)
    else:
        plot_continuous_answer(df, args.csv_path, args.answer_col, features, bin_size=args.bin_size)


if __name__ == "__main__":
    main()
