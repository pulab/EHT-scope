# EHT-Scope User Guide (Quick Start)
**Standardized Analysis Workflow for EHT Videos**

---

## 1. Before You Start
Make sure your data is organized correctly on your computer:
*   **Raw Videos**: Place your video folders inside the `TestingData` folder.
*   **Folder Names**: Ensure folders are named like this: `Acquire-EHT_WellName_PacingRate` (Example: `Acquire-EHT_A1_60`).

---

## 2. Step 1: Tracking the Tissue (Motion Tracking)
To identify the posts in your video, run the following command in the MATLAB Command Window:

```matlab
% Example for tracking Well A1
EHT_motion_tracker('Templates', 'TestingData', 'Results', true, 'EHT_config.m', true, {'Acquire-EHT_A1_0'});
```
*   **Post Selection**: A window will open. Click and drag boxes around the **left post** and **right post**.
*   **Subsequent Videos**: You only need to draw the boxes once per well.

---

## 3. Step 2: Getting the Results (Force Analysis)
Once tracking is finished, run the analysis command:

```matlab
% Example for analyzing Well A1 at 1 Hz
analyze_EHT_with_figure('Results/Results_File_Name.tsv', 67, 1.0, 'EHT_config.m', 1);
```
*   **Output**: Final metrics are saved in the `Results` folder as `.txt` files.

---

## 4. Standard Settings
To change baseline settings, edit the file `Code/EHT-analyze/EHT_config.m`:
*   **Pixel Size**: Should be **67** (Pixels per mm).
*   **Diastolic Distance**: Should be **8.0** mm.
