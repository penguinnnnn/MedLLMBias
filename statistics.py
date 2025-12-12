import argparse
import pandas as pd
import scipy.stats as stats
import statsmodels.api as sm
from statsmodels.formula.api import ols


def run_discrete_analysis(df, predictors, answer_col="answer"):
    print("===== Chi-square tests for discrete answer =====")
    for col in predictors:
        print(f"\n--- Testing association between '{answer_col}' and '{col}' ---")
        try:
            contingency_table = pd.crosstab(df[col], df[answer_col])
            if contingency_table.shape[0] < 2 or contingency_table.shape[1] < 2:
                print("Not enough variation in the data to run chi-square test (need at least 2 categories in each variable).")
                continue

            chi2, p, dof, expected = stats.chi2_contingency(contingency_table)

            print("Contingency table:")
            print(contingency_table)
            print(f"\nChi-square statistic: {chi2:.4f}")
            print(f"Degrees of freedom: {dof}")
            print(f"p-value: {p:.6f}")

            if p < 0.05:
                print("Result: There is a statistically significant association (p < 0.05).")
            else:
                print("Result: No statistically significant association (p >= 0.05).")

        except Exception as e:
            print(f"Error when analyzing variable '{col}': {e}")


def run_continuous_analysis(df, predictors, answer_col="answer"):
    print("===== ANOVA for continuous answer =====")
    for col in predictors:
        print(f"\n--- ANOVA: effect of '{col}' on '{answer_col}' ---")
        try:
            # Drop rows with missing values in the current predictor or answer
            sub_df = df[[answer_col, col]].dropna()
            if sub_df[col].nunique() < 2:
                print("Not enough groups for ANOVA (need at least 2 different values of the predictor).")
                continue

            formula = f"{answer_col} ~ C({col})"
            model = ols(formula, data=sub_df).fit()
            anova_table = sm.stats.anova_lm(model, typ=2)
            print(anova_table)

            p_value = anova_table["PR(>F)"].iloc[0]
            if p_value < 0.05:
                print("Result: The predictor has a statistically significant effect on the answer (p < 0.05).")
            else:
                print("Result: The predictor does not have a statistically significant effect on the answer (p >= 0.05).")

        except Exception as e:
            print(f"Error when analyzing variable '{col}': {e}")


def main():
    parser = argparse.ArgumentParser(description="Analyze the effect of categorical predictors on an answer variable.")

    parser.add_argument("csv_path", help="Path to the input CSV file.")
    parser.add_argument("--answer-type", choices=["discrete", "continuous"], required=True,
                        help="Specify whether the answer variable is discrete or continuous.")
    parser.add_argument("--answer-col", default="answer", help="Name of the answer column. Default is 'answer'.")

    args = parser.parse_args()

    # Load data
    df = pd.read_csv(args.csv_path)

    # Define predictor columns (all columns except the answer column)
    predictors = ['Scenario', 'Name', 'Age', 'Gender', 'SO'] # 'Race'

    print("Predictor columns used in the analysis:")
    print(predictors)

    if args.answer_type == "discrete":
        run_discrete_analysis(df, predictors, answer_col=args.answer_col)
    else:
        run_continuous_analysis(df, predictors, answer_col=args.answer_col)


if __name__ == "__main__":
    main()
