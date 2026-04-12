import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

CONDITION_FILE_MAP = {
    'SCD': 'pain.csv',
    'Obesity': 'knee.csv',
    'Cirrhosis': 'cirr.csv',
    'Fibromyalgia': 'fib.csv',
}

MODEL_FILES = {
    'DeepSeek': 'DeepSeek-V3.1',
    'GLM': 'GLM-5',
    'GPT': 'gpt-5.4-2026-03-05',
    'Kimi': 'Kimi-K2.5',
    'Qwen': 'Qwen3.5-397B-A17B',
    'LLaMA': 'Llama-4-Maverick-17B-128E-Instruct-FP8',
    'Gemini': 'gemini-3-flash-preview',
    'Claude': 'claude-sonnet-4-6',
    'MiniMax': 'MiniMax-M2.5',
}

GROUPING_COLS = ['Scenario', 'Name', 'Age', 'Race', 'Gender', 'SO']
FIXED_COLORS = ['red', 'blue', 'orange', 'purple']
SCORE_MAP = {1: 0, 2: 50, 3: 50, 4: 100}


def load_csv(path):
    """Load CSV and keep only the first 7 columns."""
    df = pd.read_csv(path)
    df = df.iloc[:, :7]
    df.columns = ['Scenario', 'Name', 'Age', 'Race', 'Gender', 'SO', 'answer']
    return df


def plot_distribution(df, col, is_continuous, ax):
    """Plot grouped bar chart for one grouping column."""
    if is_continuous:
        bins = [10, 20, 30, 40, 50]
        bin_labels = ['10-20', '20-30', '30-40', '40-50']
        df = df.copy()
        df['answer_bin'] = pd.cut(df['answer'], bins=bins, labels=bin_labels,
                                  right=True, include_lowest=True)
        counts = df.groupby([col, 'answer_bin'], observed=False).size().unstack(fill_value=0)
        counts = counts.reindex(columns=bin_labels, fill_value=0)
        group_labels = bin_labels
        legend_title = 'Answer Bin'
        title_suffix = '(continuous, binned)'
    else:
        answer_vals = [1, 2, 3, 4]
        counts = df.groupby([col, 'answer'], observed=False).size().unstack(fill_value=0)
        counts = counts.reindex(columns=answer_vals, fill_value=0)
        group_labels = [str(v) for v in answer_vals]
        legend_title = 'Answer'
        title_suffix = '(categorical)'

    counts = counts.loc[sorted(counts.index, key=str)]
    x = np.arange(len(counts.index))
    width = 0.8 / len(group_labels)

    for i, label in enumerate(counts.columns):
        ax.bar(x + i * width, counts[label], width,
               label=str(label), color=FIXED_COLORS[i])

    ax.set_xticks(x + width * (len(group_labels) - 1) / 2)
    ax.set_xticklabels(counts.index, rotation=45, ha='right')
    ax.set_xlabel(col)
    ax.set_ylabel('Count')
    ax.set_title(f'Answer distribution by {col} {title_suffix}')
    ax.legend(title=legend_title)


def compute_averages(df, is_continuous):
    """Return {col: {value: avg}} for each grouping column."""
    if is_continuous:
        series = df['answer']
    else:
        series = df['answer'].map(SCORE_MAP)

    result = {}
    for col in GROUPING_COLS:
        result[col] = series.groupby(df[col]).mean().round(2).to_dict()
    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python visualize.py <CONDITION>")
        print("  CONDITION: SCD, Obesity, Cirrhosis, Fibromyalgia")
        sys.exit(1)

    condition = sys.argv[1]
    if condition not in CONDITION_FILE_MAP:
        print(f"Unknown condition: {condition}")
        print(f"  Choose from: {', '.join(CONDITION_FILE_MAP.keys())}")
        sys.exit(1)

    cond_csv = CONDITION_FILE_MAP[condition]
    out_dir = f'results/{condition}/direct'
    os.makedirs(out_dir, exist_ok=True)

    model_names = list(MODEL_FILES.keys())

    # Process both file types: condition-specific (categorical) and pass (continuous)
    for file_type, csv_name, is_continuous in [
        (condition, cond_csv, False),
        ('pass', 'pass.csv', True),
    ]:
        # --- Collect averages from all models into one summary ---
        # Build a set of all (Column, Value) pairs across models for consistent rows
        all_averages = {}  # model_name -> {col: {value: avg}}

        for model_name, model_dir in MODEL_FILES.items():
            path = f'{out_dir}/{model_dir}/{csv_name}'
            if not os.path.exists(path):
                print(f'WARNING: {path} not found, skipping')
                continue

            df = load_csv(path)
            all_averages[model_name] = compute_averages(df, is_continuous)

            # --- Per-model visualization ---
            for col in GROUPING_COLS:
                fig, ax = plt.subplots(figsize=(12, 6))
                plot_distribution(df, col, is_continuous, ax)
                ax.set_title(f'{model_name}: Answer distribution by {col}')
                plt.tight_layout()
                model_src_dir = f'{out_dir}/{model_dir}'
                fig.savefig(f'{model_src_dir}/{file_type}_{col}.png', dpi=150)
                plt.close(fig)

            print(f'  Charts saved for {model_name} / {csv_name}')

        # --- Build summary CSV with model names as columns ---
        # Gather all (Column, Value) pairs
        all_keys = set()
        for model_avgs in all_averages.values():
            for col, val_dict in model_avgs.items():
                for val in val_dict:
                    all_keys.add((col, val))

        rows = []
        for col, val in sorted(all_keys, key=lambda x: (x[0], str(x[1]))):
            row = {'Column': col, 'Value': val}
            for model_name in model_names:
                if model_name in all_averages and col in all_averages[model_name]:
                    row[model_name] = all_averages[model_name][col].get(val, '')
                else:
                    row[model_name] = ''
            rows.append(row)

        summary_df = pd.DataFrame(rows, columns=['Column', 'Value'] + model_names)
        summary_path = f'{out_dir}/{file_type}_summary.csv'
        summary_df.to_csv(summary_path, index=False)
        print(f'Summary saved: {summary_path}')


if __name__ == '__main__':
    main()
