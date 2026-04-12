import sys
import os
import pandas as pd
import numpy as np
from scipy import stats

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


def load_csv(path):
    """Load CSV and keep only the first 7 columns."""
    df = pd.read_csv(path)
    df = df.iloc[:, :7]
    df.columns = ['Scenario', 'Name', 'Age', 'Race', 'Gender', 'SO', 'answer']
    return df


def anova_eta_squared(df):
    """One-way ANOVA + eta-squared for each grouping column vs continuous answer."""
    results = []
    for col in GROUPING_COLS:
        groups = [g['answer'].values for _, g in df.groupby(col)]
        if len(groups) < 2:
            results.append({
                'Variable': col,
                'F': np.nan, 'p': np.nan, 'eta_squared': np.nan,
                'n_groups': len(groups),
            })
            continue

        f_stat, p_val = stats.f_oneway(*groups)

        # Eta-squared: SS_between / SS_total
        grand_mean = df['answer'].mean()
        ss_total = np.sum((df['answer'] - grand_mean) ** 2)
        ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2
                         for g in (grp['answer'] for _, grp in df.groupby(col)))
        eta_sq = ss_between / ss_total if ss_total > 0 else np.nan

        results.append({
            'Variable': col,
            'F': round(f_stat, 4),
            'p': round(p_val, 6),
            'eta_squared': round(eta_sq, 4),
            'n_groups': len(groups),
        })
    return pd.DataFrame(results)


def chi_square_cramers_v(df):
    """Chi-square test + Cramer's V for each grouping column vs categorical answer."""
    results = []
    for col in GROUPING_COLS:
        ct = pd.crosstab(df[col], df['answer'])
        chi2, p_val, dof, _ = stats.chi2_contingency(ct)

        # Cramer's V
        n = ct.values.sum()
        k = min(ct.shape) - 1
        cramers_v = np.sqrt(chi2 / (n * k)) if (n * k) > 0 else np.nan

        results.append({
            'Variable': col,
            'chi2': round(chi2, 4),
            'p': round(p_val, 6),
            'dof': dof,
            'cramers_v': round(cramers_v, 4),
            'n_groups': ct.shape[0],
        })
    return pd.DataFrame(results)


def main():
    if len(sys.argv) < 2:
        print("Usage: python stats.py <CONDITION>")
        print("  CONDITION: SCD, Obesity, Cirrhosis, Fibromyalgia")
        sys.exit(1)

    condition = sys.argv[1]
    if condition not in CONDITION_FILE_MAP:
        print(f"Unknown condition: {condition}")
        print(f"  Choose from: {', '.join(CONDITION_FILE_MAP.keys())}")
        sys.exit(1)

    cond_csv = CONDITION_FILE_MAP[condition]
    out_dir = f'results/{condition}/direct'

    for file_type, csv_name, is_continuous in [
        (condition, cond_csv, False),
        ('pass', 'pass.csv', True),
    ]:
        all_results = []

        for model_name, model_dir in MODEL_FILES.items():
            path = f'{out_dir}/{model_dir}/{csv_name}'
            if not os.path.exists(path):
                print(f'WARNING: {path} not found, skipping')
                continue

            df = load_csv(path)

            if is_continuous:
                res = anova_eta_squared(df)
            else:
                res = chi_square_cramers_v(df)

            res.insert(0, 'Model', model_name)
            all_results.append(res)

            # Print per-model results
            test_name = 'ANOVA' if is_continuous else 'Chi-square'
            print(f'\n{model_name} / {csv_name} ({test_name}):')
            print(res.to_string(index=False))

        if all_results:
            combined = pd.concat(all_results, ignore_index=True)

            # Average across models per variable
            numeric_cols = combined.select_dtypes(include='number').columns.tolist()
            avg = combined.groupby('Variable')[numeric_cols].mean().round(4).reset_index()
            avg.insert(0, 'Model', 'AVG')
            combined = pd.concat([combined, avg], ignore_index=True)

            stats_path = f'{out_dir}/{file_type}_stats.csv'
            combined.to_csv(stats_path, index=False)
            print(f'\nAverage across models:')
            print(avg.to_string(index=False))
            print(f'\nStats saved: {stats_path}')


if __name__ == '__main__':
    main()
