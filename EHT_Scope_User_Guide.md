# EHT-Scope User Guide (Quick Start)
**Standardized Analysis Workflow for EHT Videos**

---

## 1. Before You Start
Make sure your data is organized correctly on your computer:
*   **Raw Videos**: Place your video folders inside the `TestingData` folder.
*   **Folder Names**: Ensure folders are named like this: `Acquire-EHT_WellName_PacingRate` (Example: `Acquire-EHT_A1_60`).

---

## 2. Step 1: Tracking the Tissue (Motion Tracking)
To identify the posts in your video, run the following command in the MATLAB Command Window. 

**Note**: You must be in the main project folder.

```matlab
% 1. Add the code folder to your MATLAB path
addpath('Code/EHT-analyze');

% 2. Run the tracking command (This example tracks ALL folders in TestingData)
EHT_motion_tracker('Templates', 'TestingData', 'Results', true, 'Code/EHT-analyze/EHT_config.m', true, {});
```
*   **Post Selection**: A window will open for each new well. Click and drag boxes around the **left post** and **right post**.
*   **Automatic Matching**: The software will automatically apply your boxes to all pacing rates (0, 60, 120) for that well.

---

## 3. Step 2: Getting the Results (Force Analysis)
Once tracking is finished, run the analysis command:

```matlab
% Example for analyzing Well A1 at 1 Hz (60 BPM)
analyze_EHT_with_figure('Results/Results_TIMESTAMP.tsv', 67, 1.0, 'Code/EHT-analyze/EHT_config.m', 1);
```
*   **Individual Results**: Saved in the `Results` folder as `.txt` files for each tissue.
*   **Combined Results**: A master file named **`Master_Results_Combined.csv`** is automatically updated in the `Results` folder every time you run an analysis. This contains all your data in one big spreadsheet.

---

## 4. Standard Settings
To change baseline settings, edit the file `Code/EHT-analyze/EHT_config.m`:
*   **Pixel Size**: Should be **67** (Pixels per mm).
*   **Diastolic Distance**: Should be **8.0** mm.
