function smoothed = sgolay_time(t, data, order, window_s)
% Savitzky-Golay style smoothing for unevenly spaced samples. Each point is
% replaced by the value at t(i) of a polynomial fitted to the samples within
% window_s/2 of t(i), so the window is a fixed time span rather than a fixed
% number of frames. With evenly spaced samples this matches classic
% Savitzky-Golay smoothing away from the ends of the recording.
% Where frames are missing the window holds fewer samples; the polynomial
% order is then lowered so the fit still has more samples than coefficients.

t = t(:);
data = data(:);
halfwin = window_s / 2;
n = length(data);
smoothed = zeros(size(data));

for i = 1:n
    idx = find(abs(t - t(i)) <= halfwin);
    n_times = length(unique(t(idx)));
    p = max(0, min(order, n_times - 2));
    x = (t(idx) - t(i)) / halfwin;

    A = zeros(length(idx), p + 1);
    for j = 0:p
        A(:, j + 1) = x.^j;
    end
    coeffs = A \ data(idx);
    smoothed(i) = coeffs(1);
end

end
