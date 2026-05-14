% test_interactive_ui.m
% This script is designed specifically to test the updated interactive bounding box UI.

clc; clear; close all;

% Define paths relative to the Code/EHT-analyze directory
template_path = '../../Templates';
data_path = '../../TestingData';
result_path = '../../TestingData_Results';
config_file = 'EHT_config_corrected.m';

fprintf('Launching UI Test...\n');
fprintf('Please check your taskbar for the MATLAB Figure window if it doesn''t pop up automatically.\n');

% We set perform_annotation = true (4th arg) and force_reannotation = true (6th arg)
% Ensure it triggers the UI even if templates already exist.
EHT_motion_tracker(template_path, data_path, result_path, true, config_file, true);