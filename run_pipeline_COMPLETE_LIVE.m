% run_pipeline_COMPLETE_LIVE.m
% Complete End-to-End Validation for all 27 folders in TestingData
% Uses Hybrid Analysis (Win 5) and FORCES REANNOTATION

BASE         = 'C:\Users\kusha\Downloads\11.11.25 EHT\EHT-scope-main';
CODE_DIR     = fullfile(BASE, 'Code', 'EHT-analyze');
template_path = fullfile(BASE, 'Templates');
data_path    = fullfile(BASE, 'TestingData');
result_path  = fullfile(BASE, 'Final_Hybrid_Validation');
config_file  = fullfile(CODE_DIR, 'EHT_config_corrected.m');

if ~exist(result_path, 'dir'); mkdir(result_path); end
addpath(CODE_DIR); addpath(BASE);

fprintf('=== EHT Pipeline: COMPLETE HYBRID VALIDATION (LIVE) ===\n');

%% ---- STEP 1: Motion Tracking (All Wells) ----
fprintf('\n=== STEP 1: Motion Tracking ===\n');
fprintf('NOTE: force_reannotation = true. You will be prompted for all wells.\n');

% force_reannotation = true
EHT_motion_tracker(template_path, data_path, result_path, true, config_file, true, {});

fprintf('Tracking complete.\n\n');

%% ---- STEP 2: Hybrid Analysis (All Wells) ----
fprintf('=== STEP 2: Hybrid Analysis ===\n');

% Find the latest TSV result
result_files = dir(fullfile(result_path, 'Results_*.tsv'));
[~, idx] = max([result_files.datenum]);
results_file = fullfile(result_path, result_files(idx).name);
fprintf('Using tracking file: %s\n\n', results_file);

data = readtable(results_file, 'Delimiter', char(9), 'FileType', 'text');
wells = unique(data.Well_ID);
rates = [0, 60, 120];

for i = 1:length(wells)
    for j = 1:length(rates)
        well       = wells{i};
        pacing_bpm = rates(j);
        pacing_hz  = pacing_bpm / 60;

        subset = data(strcmp(data.Well_ID, well) & data.Pacing_Rate_BPM == pacing_bpm, :);
        if height(subset) < 50, continue; end

        fprintf('[Analyzing] %s @ %d BPM...\n', well, pacing_bpm);
        temp_file = fullfile(result_path, sprintf('%s_%dBPM_final_test.txt', well, pacing_bpm));
        writetable(subset, temp_file, 'Delimiter', char(9));

        try
            % Hybrid Analysis (Smoothed Peaks / Raw Timing / Win 5)
            analyze_EHT_with_figure(temp_file, 67.0, pacing_hz, config_file, i*10+j);
        catch ME
            fprintf('  -> ERROR: %s\n', ME.message);
        end
    end
end

fprintf('\n=== Complete Validation Run Finished ===\n');
fprintf('Results saved in: %s\n', result_path);
