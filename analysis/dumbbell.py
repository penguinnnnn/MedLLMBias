import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.backends.backend_pdf

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

CONDITIONS = ['SCD', 'Obesity', 'Cirrhosis', 'Fibromyalgia']
SCENARIOS = ['Stigmatizing-21', 'Stigmatizing-14', 'Stigmatizing-07', 'Neutral-01']
SCENARIO_LABELS = ['Stigmatizing (21)', 'Stigmatizing (14)', 'Stigmatizing (7)', 'Neutral']
SCENARIO_COLORS = ['#4b0082', '#6a3d8a', '#9b72b0', '#c9b1d9']  # dark to light purple
SCENARIO_MARKERS = ['^', 'v', 's', 'o']  # triangle, inverted triangle, square, circle
SCORE_MAP = {1: 0, 2: 50, 3: 50, 4: 100}

plt.rcParams.update({'font.size': 14})


def load_csv(path):
    df = pd.read_csv(path)
    df = df.iloc[:, :7]
    df.columns = ['Scenario', 'Name', 'Age', 'Race', 'Gender', 'SO', 'answer']
    return df


def get_scores(condition, csv_name, is_continuous):
    """Return {model_name: {scenario: avg_score}} for the 4 target scenarios."""
    out_dir = f'results/{condition}/direct'
    scores = {}
    for model_name, model_dir in MODEL_FILES.items():
        path = f'{out_dir}/{model_dir}/{csv_name}'
        if not os.path.exists(path):
            print(f'WARNING: {path} not found, skipping')
            continue
        df = load_csv(path)
        df = df[df['Scenario'].isin(SCENARIOS)]
        if is_continuous:
            avg = df.groupby('Scenario')['answer'].mean()
        else:
            df = df.copy()
            df['score'] = df['answer'].map(SCORE_MAP)
            avg = df.groupby('Scenario')['score'].mean()
        scores[model_name] = avg.to_dict()
    return scores


def draw_dumbbell(axes, scores_by_condition, conditions, x_ranges, x_label):
    """Draw a 4-panel dumbbell plot."""
    model_names = list(MODEL_FILES.keys())
    y_pos = np.arange(len(model_names))

    for idx, condition in enumerate(conditions):
        ax = axes[idx]
        scores = scores_by_condition[condition]

        for i, model in enumerate(model_names):
            if model not in scores:
                continue
            vals = [scores[model].get(s, np.nan) for s in SCENARIOS]
            valid = [v for v in vals if not np.isnan(v)]
            if not valid:
                continue

            # Draw connecting line
            ax.plot([min(valid), max(valid)], [i, i],
                    color='grey', linewidth=1.5, zorder=1)

            # Draw points
            for j, s in enumerate(SCENARIOS):
                v = scores[model].get(s, np.nan)
                if not np.isnan(v):
                    ax.scatter(v, i, color=SCENARIO_COLORS[j], s=120,
                               marker=SCENARIO_MARKERS[j],
                               zorder=2, edgecolors='none')

        ax.set_yticks(y_pos)
        ax.set_yticklabels(model_names)
        ax.set_ylim(len(model_names) - 0.5, -0.5)  # padding top & bottom

        # Add x padding so dots don't overlap the axis lines
        xlo, xhi = x_ranges[idx]
        x_pad = (xhi - xlo) * 0.03
        ax.set_xlim(xlo - x_pad, xhi + x_pad)

        # Draw grey vertical lines at the actual range boundaries
        for xv in [xlo, xhi]:
            ax.axvline(xv, color='grey', linewidth=0.8, alpha=0.3)

        ax.set_xlabel(x_label, fontsize=14)
        ax.set_title(condition, fontsize=16)
        ax.grid(axis='x', linestyle='-', color='grey', alpha=0.3)

        # Remove top and right spines
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    return axes


def main():
    # --- Categorical dumbbell ---
    cat_scores = {}
    for condition in CONDITIONS:
        cond_csv = CONDITION_FILE_MAP[condition]
        cat_scores[condition] = get_scores(condition, cond_csv, is_continuous=False)

    fig_cat, axes_cat = plt.subplots(1, 4, figsize=(16, 5), sharey=True)
    cat_ranges = [(40, 100), (0, 100), (0, 100), (0, 100)]
    draw_dumbbell(axes_cat, cat_scores, CONDITIONS, x_ranges=cat_ranges,
                  x_label='Treatment Score')

    # Legend
    legend_handles = [
        plt.Line2D([0], [0], marker=m, color='w', markerfacecolor=c,
                   markersize=10, label=l)
        for l, c, m in zip(SCENARIO_LABELS, SCENARIO_COLORS, SCENARIO_MARKERS)
    ]
    fig_cat.legend(handles=legend_handles, loc='lower center',
                   ncol=4, bbox_to_anchor=(0.5, -0.05), frameon=False)
    fig_cat.tight_layout()

    # --- Pass dumbbell ---
    pass_scores = {}
    for condition in CONDITIONS:
        pass_scores[condition] = get_scores(condition, 'pass.csv', is_continuous=True)

    fig_pass, axes_pass = plt.subplots(1, 4, figsize=(16, 5), sharey=True)
    pass_ranges = [(10, 40)] * 4
    draw_dumbbell(axes_pass, pass_scores, CONDITIONS, x_ranges=pass_ranges,
                  x_label='PASS Score')
    fig_pass.legend(handles=legend_handles, loc='lower center',
                    ncol=4, bbox_to_anchor=(0.5, -0.05), frameon=False)
    fig_pass.tight_layout()

    # --- Save to separate PDFs ---
    os.makedirs('results', exist_ok=True)
    fig_cat.savefig('results/dumbbell_categorical.pdf', bbox_inches='tight')
    fig_pass.savefig('results/dumbbell_pass.pdf', bbox_inches='tight')
    plt.close('all')
    print('Saved: results/dumbbell_categorical.pdf')
    print('Saved: results/dumbbell_pass.pdf')


if __name__ == '__main__':
    main()
