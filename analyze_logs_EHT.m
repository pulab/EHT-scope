function analyze_logs_EHT(file_name, pixel,pacing_freqs)
% EHT analysis by Joshua Mayourian 2/1/22

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Defining analysis parameters
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

post_radius = 1; % radius = 1mm
thresh = 1; % no need to change
sens = 10; % no need to change
diastolicdist = 8; % distance between posts = 8mm
p_order = 4; % no need to change
w_size = 11; % no need to change
tissue_heights = 12; % tissue height = 12mm

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Here is where the analysis starts
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%%%%%% Read file %%%%%%
log = readtable(file_name);
log = log(:,3:end);
log = table2array(log);
log(:,1) = log(:,1)./1000;

% Force Calculation %
measurement_times = log(:,1) - min(log(:,1));
post_distances = sqrt((log(:,4)-log(:,2)).^2+(log(:,3)-log(:,5)).^2)./pixel; % define post distance as difference between L and R posts
total_deflections = diastolicdist - post_distances;
post_deflections = total_deflections / 2;
raw_force = post_force2(post_deflections, tissue_heights, tissue_heights, post_radius); % calculate force
smooth_data = sgolayfilt(raw_force,p_order,w_size); % smooths force data
[smooth_data, measurement_times, indout] = removeoutliers2(smooth_data,measurement_times,sens);
raw_force = raw_force(indout); % Raw force after outliers

%%% Beating freq calcs %%%
sampling_freq = 1 / mean(diff(measurement_times));
zm_force = smooth_data - mean(smooth_data);
L = length(measurement_times);
NFFT = 2^nextpow2(L);
fc = fft(zm_force, NFFT)/L; % frequency components
fc = 2*abs(fc(1:NFFT/2+1)); % make components absolute, only use absolute
f = sampling_freq/2 * linspace(0, 1, NFFT/2+1);
[max_fc, max_i] = max(fc);
beating_freqs = f(max_i);

%%% Developed Force Calculation %%%
[max_t, maxima, min_t, minima] = find_pv7(measurement_times, smooth_data,thresh);
[max_ind, maxjunk, min_ind, minjunk] = find_pv7(1:length(smooth_data-1), smooth_data,thresh);
clearvars maxjunk minjunk
peak_v = zeros(size(smooth_data));
val_v = zeros(size(smooth_data));
cur_pk = 1;
cur_vl = 1;

for n=1:length(smooth_data)
    if ~isempty(maxima)
        peak_v(n) = maxima(cur_pk);
        val_v(n) = minima(cur_vl);
        if (cur_pk < length(maxima) && measurement_times(n) >= max_t(cur_pk+1));
            cur_pk = cur_pk + 1;
        end
        if (cur_vl < length(minima) && measurement_times(n) >= min_t(cur_vl+1));
            cur_vl = cur_vl + 1;
        end
    end
end

if (~isempty(maxima))
    max_deflections = max(maxima);
    dev_forces = mean(peak_v-val_v);
    dev_forc_std = std(peak_v-val_v);
    dias_forces = mean(val_v);
    dias_forc_st = std(val_v);
    syst_forces = mean(peak_v);
    syst_forces_st = std(peak_v);
    force(:,1) = measurement_times;
    force(:,2) = smooth_data;
    periods = diff(max_t);
    beatrate = 1./periods;
    beating_rates = mean(beatrate);
    beating_rates_std = std(beatrate);
    t2prev = periods(1:end-1);
    t2next = periods(2:end);
end
