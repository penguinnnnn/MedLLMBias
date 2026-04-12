import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

VARIABLES = ['Language', 'Name', 'Age', 'Gender', 'Race', 'SO']
CONDITIONS = ['SCD', 'Obesity', 'Cirrhosis', 'Fibromyalgia']


def main():
    df = pd.read_csv('effect-size-t.csv', index_col=0)
    df = df.reindex(VARIABLES)

    fig, axes = plt.subplots(1, 4, figsize=(16, 3.5))
    y_pos = np.arange(len(VARIABLES))

    for idx, condition in enumerate(CONDITIONS):
        ax = axes[idx]
        values = df[condition].values

        for i, val in enumerate(values):
            if pd.isna(val):
                continue
            ax.plot([0, val], [i, i], color='#6a3d8a', linewidth=2, zorder=1)
            ax.scatter(val, i, color='#6a3d8a', s=100, zorder=2, edgecolors='none')

        ax.set_yticks(y_pos)
        if idx == 0:
            ax.set_yticklabels(VARIABLES, fontsize=14)
        else:
            ax.set_yticklabels([''] * len(VARIABLES))

        ax.set_ylim(len(VARIABLES) - 0.5, -0.5)
        ax.axvline(0, color='grey', linewidth=0.8)
        ax.set_title(condition, fontsize=15)
        ax.set_xlabel("Cramer's V", fontsize=14) # r'$\eta^2$' "Cramer's V"
        ax.grid(axis='x', linestyle='-', color='grey', alpha=0.2)
        ax.tick_params(axis='x', labelsize=12)
        ax.tick_params(axis='y', length=0)

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    fig.tight_layout()
    fig.savefig('results/lollipop.pdf', bbox_inches='tight')
    plt.close()
    print('Saved: results/lollipop.pdf')


if __name__ == '__main__':
    main()
