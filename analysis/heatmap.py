import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def main():
    df = pd.read_csv('model-disease-p.csv', index_col=0)

    # Compute averages for labels
    col_avgs = df.mean(axis=0)  # per model
    row_avgs = df.mean(axis=1)  # per disease

    fig, ax = plt.subplots(figsize=(10, 4))

    # Purple gradient: white (0) to deep purple (-100)
    im = ax.imshow(df.values, cmap='Purples_r', vmin=-17, vmax=0, aspect='auto')

    # Axes
    ax.set_xticks(np.arange(len(df.columns)))
    x_labels = [f'{col} ({col_avgs[col]:.1f})' for col in df.columns]
    ax.set_xticklabels(x_labels, rotation=90, fontsize=15, ha='center')
    ax.xaxis.set_ticks_position('bottom')

    ax.set_yticks(np.arange(len(df.index)))
    y_labels = [f'{idx} ({row_avgs[idx]:.1f})' for idx in df.index]
    ax.set_yticklabels(y_labels, fontsize=15)

    # Annotate cells with values
    for i in range(len(df.index)):
        for j in range(len(df.columns)):
            val = df.iloc[i, j]
            color = 'white' if val < -55 else 'black'
            ax.text(j, i, f'{val:.1f}', ha='center', va='center',
                    fontsize=13, color=color)

    # Remove spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.tick_params(left=False, bottom=False)

    # Colorbar
    cbar = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
    cbar.ax.tick_params(labelsize=13)

    plt.tight_layout()
    fig.savefig('results/heatmap.pdf', bbox_inches='tight')
    plt.close()
    print('Saved: results/heatmap.pdf')


if __name__ == '__main__':
    main()
