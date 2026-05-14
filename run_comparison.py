import pandas as pd
import numpy as np

csv_path = r'TestingData_Results\Combined_Results.csv'
excel_path = r'4April26_Comparison.xlsx'

print('Loading newly generated results...')
df_current = pd.read_csv(csv_path)

print('Loading ground truth...')
df_old = pd.read_excel(excel_path, sheet_name='OLD values')
df_new = pd.read_excel(excel_path, sheet_name='New values')

metrics = [
    'beating_rates', 'dias_forces', 'syst_forces', 'dev_forces',
    't50', 'c50', 'r50', 't2peak', 'r90', 'uv', 'dv'
]

def extract_tissue_pacing(fn):
    import os
    base = os.path.basename(fn)
    parts = base.split('_')
    tissue = parts[0]
    pacing = parts[1].replace('BPM', '')
    return f'{tissue}_{pacing}'

df_current['match_id'] = df_current['tissue_name'].apply(extract_tissue_pacing)
df_old['match_id'] = df_old['tissue_name']
df_new['match_id'] = df_new['tissue_name']

merged_old = pd.merge(df_current, df_old, on='match_id', suffixes=('_curr', '_old'))
merged_new = pd.merge(df_current, df_new, on='match_id', suffixes=('_curr', '_val'))

with open('Comparison_Against_4April26.md', 'w', encoding='utf-8') as f:
    f.write('# Verification Report: Current Pipeline vs. 4April26 Ground Truth\n\n')
    f.write('This report summarizes the maximum absolute errors (MAE) and maximum percentage differences across all 27 tissues and pacing conditions.\n\n')
    
    f.write('## 1. Current Pipeline vs. 4April26 "New values" (Expected Ground Truth)\n\n')
    f.write('| Metric | Max Abs Diff | Max % Diff | Mean Abs Diff | Match Status |\n')
    f.write('| :--- | :--- | :--- | :--- | :--- |\n')
    
    for m in metrics:
        col_c = f'{m}_curr'
        if m == 'beating_rates':
             col_v = m + '_val'
        else:
             col_v = m + '_val'
             
        diff = np.abs(merged_new[col_c] - merged_new[col_v])
        pct_diff = diff / np.abs(merged_new[col_v]) * 100
        
        max_diff = diff.max()
        max_pct = pct_diff.max()
        mean_diff = diff.mean()
        
        status = 'Exact' if max_diff < 1e-4 else 'Diverged'
        f.write(f'| **{m}** | {max_diff:.6f} | {max_pct:.4f}% | {mean_diff:.6f} | {status} |\n')

    f.write('\n## 2. Current Pipeline vs. 4April26 "OLD values" (Legacy Baseline)\n\n')
    f.write('| Metric | Max Abs Diff | Mean Abs Diff | Direction |\n')
    f.write('| :--- | :--- | :--- | :--- |\n')
    
    for m in metrics:
        col_c = f'{m}_curr'
        col_v = m + '_old'
             
        diff = np.abs(merged_old[col_c] - merged_old[col_v])
        max_diff = diff.max()
        mean_diff = diff.mean()
        
        f.write(f'| **{m}** | {max_diff:.6f} | {mean_diff:.6f} | Diverged |\n')

print('Report generation complete')
