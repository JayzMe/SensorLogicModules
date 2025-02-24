%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% vcom_test.m
%
% This is a demonstration how to use the class *vcom_xep_radar_connector*
%
% Copyright: 2020 Sensor Logic
% Written by: Justin Hadella
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
clear;
clc;
close("all");
% pause(5);
r = vcom_xep_radar_connector('COM7'); % adjust for *your* COM port!
r.Open('X4');

% Setting some variables
r.TryUpdateChip('rx_wait', 0);
r.TryUpdateChip('frame_start', 2);
r.TryUpdateChip('frame_end', 4);
r.TryUpdateChip('ddc_en', 0);

r.TryUpdateChip('tx_region', 3);
r.TryUpdateChip('tx_power', 3);

% r.TryUpdateChip('fs', 23.328e9);
% r.TryUpdateChip('frame_length', 16);
% r.TryUpdateChip('iterations', 8);
% r.TryUpdateChip('prf_div', 16);

% As a side-effect many settings on write will cause the numSamplers
% variable to update
fprintf('bins = %d\n', r.numSamplers);

% Actually every variable from the radar is requested in this manner.
iterations = r.Item('iterations');
fprintf('iterations = %d\n', iterations);
r.Item('num_samples')
r.Item('frame_length')

tic;
for i = 1:100
    r.GetFrameRawDouble;
end
elapsed = toc;
fprintf('measure fps = %f (no plotting)\n', 100 / elapsed);

% Set up time plot signal
frameSize = r.numSamplers;   % Get # bins/samplers in a frame
frame = zeros(1, frameSize); % Preallocate frame
h_fig = figure;
subplot(3,1,1);
ax1 = gca;
h1 = plot(ax1, 1:frameSize, frame);
title(ax1, 'radar time waveform');
xlabel(ax1, 'bin');
ylabel(ax1, 'amplitude');
% ylim([-5, 5]);

Fs = 23.328;
f = (-frameSize/2:frameSize/2-1)*(Fs/frameSize)*2/(100/78);
Y = fft(frame, frameSize);
p2 = subplot(3,1,2);
ax2 = gca;
h2 = plot(ax2, f, abs(Y));
title('FFT of the Signal');
xlabel('Frequency (GHz)');
ylabel('Magnitude');
xlim([0,12]);
grid(ax2);

subplot(3,1,3);
ax3 = gca;
h3 = plot(ax3, f, abs(Y));
title('Phase of the Signal');
xlabel('Frequency (GHz)');
ylabel('angle');
xlim([0,12]);
ylim([-180,180]);
grid(ax3);

% Plot data while window is open
frame_0 = abs(r.GetFrameNormalizedDouble);
for i=1:9
    frame_0 = frame_0 + abs(r.GetFrameNormalizedDouble);
end
frame_0 = frame_0 / 10;
frame_0 = floor(frame_0);
frame_0 = abs(r.GetFrameNormalizedDouble);
% frame_0(1, 100:end) = 255;
half = round(frameSize/2);
t = 0;
file_name = "results/temp.txt";
file = fopen(file_name, "w");
fclose(file);
while isgraphics(h_fig)
    try
        % frame = abs(r.GetFrameRawDouble);
        frame = abs(r.GetFrameNormalizedDouble);
        % frame = frame - frame_0;
        frame = frame - 255;
        file = fopen(file_name, "a+");
        fprintf(file, string(datetime("now")));
        fprintf(file, " ");
        fprintf(file, "%d ", frame);
        fprintf(file, "\n");
        fclose(file);
        % frame(1:80) = 0;
        % frame(150:end) = 0;
        Y = fft(frame, frameSize);
        
        set(h1, 'xdata', 1:frameSize, 'ydata', frame);
        t = t + 1;
        set(h2, 'xdata', f, 'ydata', abs(Y));
        [max_v, i] = max(abs(Y(half:end)));
        temp = sprintf('FFT of the Signal: %.1f Ghz, max: %.1f', abs(f(half+i)), max_v);
        title(p2, temp);
        set(h3, 'xdata', f, 'ydata', rad2deg(angle(Y)));
        drawnow;
    catch ME
        fprintf("ME");
        break;
    end
end

r.Close();
