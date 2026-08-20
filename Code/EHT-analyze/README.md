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

### Example Data

Example image sequences and representative results are available in `Supplementary Data 4.zip` on the latest GitHub release:

https://github.com/pulab/EHT-scope/releases/latest

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

*Note: `EHT_config_corrected.m` is available for physically accurate force calculations (uses post_radius=0.5mm).*

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
- **sgolayfilt.m**: Savitzky-Golay smoothing.
- **detect_maxmin.m**: Peak detection wrapper.
- **find_pv7.m**: Peak detection logic.
- **peakdet2.m**: Peak detection algorithm.
- **calculate_slopes.m**: Slope calculation wrapper.
- **analyze_slopes.m**: Slope calculation logic.

---

**Author:** Kushaan Sharma
**Last Updated:** November 2025
