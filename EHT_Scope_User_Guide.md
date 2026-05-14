# EHT-Scope User Guide (Quick Start)
**Standardized Analysis Workflow for EHT Videos**

---

## 1. Before You Start
Make sure your data is organized correctly on your computer:
*   **Raw Videos**: Place your video folders inside the `TestingData` folder.
*   **Folder Names**: Ensure folders are named like this: `Acquire-EHT_WellName_PacingRate` (Example: `Acquire-EHT_A1_60`).

---

## 2. Step 1: Tracking the Tissue (Motion Tracking)
This step tells the software where the two posts are in your video.

1.  Open the script `run_pipeline_COMPLETE_LIVE.m` in MATLAB.
2.  Press **Run**.
3.  **Select Posts**: A window will open showing a picture of your tissue. 
    *   Click and drag a box around the **left circular post**. 
    *   Click and drag a box around the **right circular post**.
    *   *Note: Try to be as centered as possible.*
4.  The software will now automatically track the posts for all videos in that well.

---

## 3. Step 2: Getting the Results (Force Analysis)
Once tracking is finished, the software will automatically calculate the forces.

*   **Result Files**: Your final numbers are saved in the `Results` folder as `.txt` files.
*   **Figures**: The software also saves a picture of the force trace (the "heartbeat" graph) for every well so you can check if the data looks clean.

---

## 4. Standard Settings (Check These First)
If you need to change settings, open the file `EHT_config_corrected.m`. Only touch these numbers:
*   **Pixel Size**: Should be **67** (This converts pixels to millimeters).
*   **Diastolic Distance**: Should be **8.0** (The baseline distance between posts).

---

## 5. Troubleshooting for Beginners
*   **"Matrix is close to singular"**: Ignore this message; it is a common MATLAB warning that does not affect your final numbers.
*   **"Templates saved"**: This means the software has remembered where your posts are for that well. You only need to draw the boxes once per experimental plate.
*   **"Error: Unrecognized Well ID"**: Check your folder names! They must have the underscores (`_`) in the right places.
