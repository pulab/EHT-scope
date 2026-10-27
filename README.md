# EHT-scope
**Engineered heart tissue imaging platform with acquisition and analysis software**

The platform is designed to image engineered heart tissues suspended on flexible posts in a 24 well dish.

## Components

* **EHT-scope Hardware Build**: Instructions and schematics to build the imaging platform
* **Code**: Software for acquisition, tracking, and analysis
  * **EHT-acquire**: Code for data acquisition using EHT-scope hardware
  * **EHT-analyze**: MATLAB scripts to analyze post positions and calculate physiological parameters, and a Python script (`mm2vfr.py`) to make videos with a scale bar and timer
* **Example_Videos**: Videos of the example image sequences (.mp4 and .avi)

## Workflow (MATLAB-Based)

1.  **Acquisition**: (`EHT-acquire_v2.3.bsh`): Automated 24-well plate imaging with pacing protocols using EHT-scope hardware
2.  **Motion Tracking** (`EHT_motion_tracker.m`): Template-based post position tracking
3.  **Force Analysis** (`multi_pacing_analysis.m`): Calculate force, contraction/relaxation kinetics, and beat metrics
4.  **Videos** (optional, `mm2vfr.py`): Make videos of the image sequences with a scale bar and running timer

Frame times are read for every frame from the Micro-Manager metadata (`TimeReceivedByCore`), so dropped frames do not affect the timing of the analysis or the videos.

## Key Features
- **No ImageJ dependency** - all tracking and analysis handled entirely in MATLAB
- **Automated batch processing** of multiple wells and pacing frequencies
- **Dynamic self-calibrating diastolic baseline** computation to auto-correct for tracking offsets
- **Physiological parameter extraction** (force, beat rate, kinetics, T50, C50, R50)
- **Customizable** for different tissue geometries and spacing (configured in `EHT_config.m`)

## Getting Started

See `Code/EHT-analyze/README.md` for detailed usage instructions and **critical template-drawing guidelines.**

## Example Data and Results

Example image sequences and representative results are available in GitHub release v2.3:

https://github.com/pulab/EHT-scope/releases/tag/v2.3

Download `Supplementary.Data.4.zip` from the release assets. The archive contains:

- `Analysis_Code`: analysis code included with the supplementary package
- `Representative_Image_Sequences`: example raw image sequences
- `Results`: representative tracking and force-analysis output files
- `Videos`: .mp4 videos of the example image sequences (also in `Example_Videos` in this repository)

To run the example data, extract the zip file, add the extracted `Analysis_Code` folder (or `Code/EHT-analyze` from this repository) to the MATLAB path, and use the extracted `Representative_Image_Sequences` folder as the input data folder.

