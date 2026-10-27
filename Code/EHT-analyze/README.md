# EHT-analyze: MATLAB Analysis Suite

MATLAB code for EHT (Engineered Heart Tissue) post motion tracking and force analysis.

---

## Quick Start

### 1. Motion Tracking

Track post positions from image sequences using `EHT_motion_tracker.m`.

```matlab
template_path = 'C:/Templates/';     % Where to save/load templates
data_path = 'C:/RawData/';           % Folder with video folders
result_path = 'C:/Results/';         % Where to save results
perform_annotation = true;           % Set to false if templates already exist

EHT_motion_tracker(template_path, data_path, result_path, perform_annotation, ...
                   'Code/EHT-analyze/EHT_config.m', true, {});
```

**Input folders must be named:** `Acquire-EHT_WellID_PacingRate`
- Example: `Acquire-EHT_C3_0`, `Acquire-EHT_C3_60`, `Acquire-EHT_C3_120`

**Templates:**
- The tracker looks for video-specific templates first (`Pos0/templates/`).
- If not found, it looks for well-based templates in `template_path`.
- If `perform_annotation` is true, it will ask you to draw boxes around posts for each well.

> [!WARNING]
> **Template Drawing Protocol:**
> When drawing templates, crop the box *as tightly as possible* around the upper or lower tip of the bare post. Do not include large blocks of background tissue. `normxcorr2` tracks the average motion of the entire drawn block. If background tissue is included, it will falsely dampen the force waveform amplitude, which will artificially shift the C50, R50, and UV timing metrics.



### 2. Force Analysis

Calculate force and beat metrics using `multi_pacing_analysis.m`.

```matlab
% Run this after motion tracking
multi_pacing_analysis
```

This script automatically:
1.  Prompts for the full path to the `Results` folder.
2.  Loads the selected `Results_*.txt` tracking file.
3.  Analyzes each well at each pacing rate.
4.  Generates figures and result text files.

**Output:**
- `[Well]_[Rate]BPM_temp_result.txt` - Force metrics (each column header includes its units, e.g. `dias_forces_mN`, `t50_s`, `beating_rates_Hz`)
- `[Well]_[Rate]BPM_temp_fig.fig` - Force vs Time plot

Output units (force in mN, time in s, rates in Hz) assume the input parameter units documented in the comments of `EHT_config.m` (distances in mm, Young's modulus in MPa).

### 3. Making Videos (optional)

`mm2vfr.py` turns a recording into an .mp4 video with a 1 mm scale bar, a timer and the well name. Each frame is shown at the time it was recorded, so skipped frames don't make the video jump ahead.

**One-time setup**
1. Install Python 3 from https://www.python.org/downloads/. On the first screen of the installer, tick "Add python.exe to PATH".
2. Open Command Prompt and type:
   ```
   python -m pip install numpy tifffile pillow av
   ```

**Making videos**
1. In File Explorer, open the folder that has `mm2vfr.py`. Click the address bar, type `cmd` and press Enter. A Command Prompt opens in that folder.
2. Type `python mm2vfr.py` and a space, drag the folder with your recordings into the window, then type ` -o videos` and press Enter. For example:
   ```
   python mm2vfr.py "D:\Data\Representative_Image_Sequences" -o videos
   ```
3. The videos are saved in a new folder called `videos`, one for each recording (for example `Acquire-EHT_C1_60.mp4`).

You can give it a single recording or a folder with many recordings. On a Mac, use Terminal and type `python3` instead of `python`.

**Options** (add them to the end of the command)
- `--avi` saves an .avi instead of an .mp4.
- `--px-per-mm 67` sets the scale bar. Change it if your camera calibration is not 67 pixels per mm (`pixel_size` in `EHT_config.m`).
- `--report-only` prints how many frames were skipped in each recording without making videos.

### Example Data

Example image sequences, representative results and videos are available in `Supplementary.Data.4.zip` on GitHub release v2.3:

https://github.com/pulab/EHT-scope/releases/tag/v2.3

After extracting the zip file, use `Representative_Image_Sequences` as the motion-tracking input folder. The included `Results` folder contains representative output files.

---

## Configuration

Configuration is handled by `EHT_config.m`.

| Parameter | Value | Description |
|-----------|-------|-------------|
| pixel_size | 67 | Pixels per mm (Camera calibration) |
| post_radius | 1.0 | Post radius in mm (Legacy value) |
| diastolic_distance | 8.0 | Resting distance between posts in mm |
| tissue_height | 12.0 | Tissue height in mm |
| youngs_modulus | 1.7 | PDMS Young's modulus (MPa) |
| sg_poly_order | 4 | Savitzky-Golay polynomial order |
| sg_window_s | 0.35 | Savitzky-Golay window length in seconds (about 11 frames at 30 fps) |

Frame times come from `TimeReceivedByCore` in each acquisition's `metadata.txt` (`ElapsedTime-ms` if it is missing), so dropped frames do not change the timing.

---

## File List

### Core Scripts
- **EHT_motion_tracker.m**: Main tracking function.
- **multi_pacing_analysis.m**: Main analysis wrapper.
- **analyze_EHT_with_figure.m**: Core analysis logic.

### Helpers
- **load_EHT_config.m**: Loads configuration.
- **parse_folder_name.m**: Extracts metadata from folder names.
- **post_force2.m**: Calculates force from deflection.
- **sgolay_time.m**: Savitzky-Golay smoothing over a fixed time window (handles dropped frames).
- **detect_maxmin.m**: Peak detection wrapper.
- **find_pv7.m**: Peak detection logic.
- **peakdet2.m**: Peak detection algorithm.
- **calculate_slopes.m**: Slope calculation wrapper.
- **analyze_slopes.m**: Slope calculation logic.

### Videos (Python)
- **mm2vfr.py**: Makes videos with a scale bar and timer from the image sequences (see Making Videos above).

---

**Author:** Kushaan Sharma
**Last Updated:** October 2026
