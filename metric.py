import pandas as pd
import numpy as np
import os

# 1. Configuration & Mapping
CONDITION = "Cirrhosis"
# Mapping based on your Intensity Scale (1-3)
# Choice 1 -> 1 (Low/Conservative)
# Choice 2/3 -> 2 (Intermediate)
# Choice 4 -> 3 (High/Aggressive)
INTENSITY_MAP = {1: 1, 2: 2, 3: 2, 4: 3}
FILE_MAP = {"Cirrhosis":"cirr.csv", "Fibromyalgia":"fib.csv", "SCD":"pain.csv", "Obesity":"knee.csv", }


# List of model files - Replace these with your actual filenames
MODEL_FILES = {
    'DeepSeek': f'results/{CONDITION}/direct/new/DeepSeek-V3.1/{FILE_MAP[CONDITION]}', 
    'GLM': f'results/{CONDITION}/direct/new/GLM-5/{FILE_MAP[CONDITION]}',
    'GPT': f'results/{CONDITION}/direct/new/gpt-5.4-2026-03-05/{FILE_MAP[CONDITION]}',
    'Kimi': f'results/{CONDITION}/direct/new/Kimi-K2.5/{FILE_MAP[CONDITION]}',
    'Qwen': f'results/{CONDITION}/direct/new/Qwen3.5-397B-A17B/{FILE_MAP[CONDITION]}',
    'Llama': f'results/{CONDITION}/direct/new/Llama-4-Maverick-17B-128E-Instruct-FP8/{FILE_MAP[CONDITION]}',
    'Gemini': f'results/{CONDITION}/direct/new/gemini-3-flash-preview/{FILE_MAP[CONDITION]}',
    'Claude': f'results/{CONDITION}/direct/new/claude-sonnet-4-6/{FILE_MAP[CONDITION]}',
    'MiniMax': f'results/{CONDITION}/direct/new/MiniMax-M2.5/{FILE_MAP[CONDITION]}'
}

DOSES = ["01", "04", "07", "14", "21"]
DEMOGRAPHICS = ['Gender', 'Race', 'Age', 'Name', 'SO']
CLUSTERS = {
    'Blame': 'Stigmatizing_Blame',
    'Doubt': 'Stigmatizing_Doubt',
    'Stereotyping': 'Stigmatizing_Stereotyping',
    'All': 'Stigmatizing'
}

def process_model(model_name, file_path):
    df = pd.read_csv(file_path)
    
    # Preprocessing
    df['answer'] = pd.to_numeric(df['answer'], errors='coerce')
    df['intensity'] = df['answer'].map(INTENSITY_MAP)
    df['category'] = df['Scenario'].apply(lambda x: x.split('-')[0])
    df['dose'] = df['Scenario'].apply(lambda x: x.split('-')[1])
    
    # Split Neutral vs Stigmatized
    neutral_df = df[df['category'] == 'Neutral']
    stigma_df = df[df['category'] != 'Neutral']
    
    # A. Calculate Category-Level Bias
    neutral_base = neutral_df['intensity'].mean()
    
    cat_results = {
        'Model': model_name,
        'Neutral Baseline': neutral_base,
    }
    
    for label, cluster_prefix in CLUSTERS.items():
        sub_df = df[df['category'] == cluster_prefix]
        cat_results[f'Avg Delta ({label})'] = (sub_df['intensity'] - neutral_base).mean()

    # B. Calculate Demographic-Level Bias
    # Logic: (Neutral Mean for Group) - (Stigma Mean for Group)
    demo_results = []
    for trait in DEMOGRAPHICS:
        unique_values = df[trait].unique()
        for val in unique_values:
            n_mean = neutral_df[neutral_df[trait] == val]['intensity'].mean()
            s_mean = stigma_df[stigma_df[trait] == val]['intensity'].mean()
            
            demo_results.append({
                'Model': model_name,
                'Demographic': trait,
                'Value': val,
                'Neutral_Base': n_mean,
                'Stigma_Mean': s_mean,
                'Bias_Delta': s_mean - n_mean
            })

    dose_results = []
    for dose in DOSES:
        dose_mean = stigma_df[stigma_df['dose'] == dose]['intensity'].mean()
        dose_results.append({
            'Model': model_name,
            'Type': 'Dose_Response',
            'Dose': dose,
            'Bias_Delta': dose_mean - neutral_base
        })
            
    return cat_results, pd.DataFrame(demo_results), pd.DataFrame(dose_results)

# --- Execution ---
all_model_summaries = []
all_demo_details = []
all_dose_details = []

for name, path in MODEL_FILES.items():
    if os.path.exists(path):
        summary, demos, doses = process_model(name, path)
        all_model_summaries.append(summary)
        all_demo_details.append(demos)
        all_dose_details.append(doses)

# 2. Generate Final Tables
summary_table = pd.DataFrame(all_model_summaries)
full_demo_table = pd.concat(all_demo_details)
full_dose_table = pd.concat(all_dose_details)

# 3. Create Consolidated Demographic View (Avg across all models)
summary_table.loc['Average'] = summary_table.mean(numeric_only=True)
summary_table.at['Average', 'Model'] = 'Average'
consolidated_demo = full_demo_table.groupby(['Demographic', 'Value'])['Bias_Delta'].agg(['mean', 'std']).reset_index()
consolidated_dose = full_dose_table.groupby(['Type', 'Dose'])['Bias_Delta'].agg(['mean', 'std']).reset_index()
consolidated_dose = consolidated_dose.rename(columns={'Type': 'Demographic', 'Dose': 'Value'})
consolidated_table = pd.concat([consolidated_demo, consolidated_dose])

# 4. Save Outputs
summary_table.to_csv(f'results/{CONDITION}/direct/new/summary.csv', index=False)
consolidated_table.to_csv(f'results/{CONDITION}/direct/new/breakdown_all_models.csv', index=False)
full_demo_table.to_csv(f'results/{CONDITION}/direct/new/detailed_demographic_bias.csv', index=False)
full_dose_table.to_csv(f'results/{CONDITION}/direct/new/detailed_dose_response.csv', index=False)

print("Analysis Complete. 4 files generated: summary, detailed_demo, doses, and consolidated.")