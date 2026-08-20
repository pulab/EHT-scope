% Units for each parameter are given in the comments below. The analysis
% output units (force in mN, time in s, rates in Hz) are only correct if
% these conventions are followed: distances in mm and Young's modulus in
% MPa yield force in millinewtons (mN).

config.pixel_size = 67;             % pixels/mm (camera calibration: pixels per millimeter)

config.post_radius = 1.0;           % mm (post radius)
config.diastolic_distance = 8.0;    % mm (resting distance between posts)
config.tissue_height = 12.0;        % mm (tissue height on post)

config.youngs_modulus = 1.7;        % MPa (PDMS Young's modulus)

config.template_width = 50;         % pixels
config.template_height = 50;        % pixels
config.min_template_width = 10;     % pixels
config.max_template_width = 150;    % pixels
config.min_template_height = 10;    % pixels
config.max_template_height = 150;   % pixels
config.show_annotation_guidance = true;  % true/false (no units)

config.score_threshold = 0.4;       % dimensionless (normalized cross-correlation score, 0-1)

config.min_distance = 30;           % pixels

config.peak_threshold = 1.0; % dimensionless (multiple of the force signal's standard deviation); increased to 1.0 to match legacy Analyze_logs_EHT.m

config.outlier_sensitivity = 10; % dimensionless (Thompson tau sensitivity); reverted to 10 to match legacy Analyze_logs_EHT.m

config.sg_poly_order = 4;           % dimensionless (Savitzky-Golay polynomial order)
    config.sg_window_size = 11;     % frames (Savitzky-Golay window length, must be odd)
