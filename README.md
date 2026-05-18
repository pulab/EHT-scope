# EHT-scope
**Engineered heart tissue imaging platform with acquisition and analysis software**

The platform is designed to image engineered heart tissues suspended on flexible posts in a 24 well dish.

## Components

* **EHT-scope Hardware Build**: Instructions and schematics to build the imaging platform
* **Code**: Software for acquisition, tracking, and analysis
  * **EHT-analyze**: MATLAB scripts to analyze post positions and calculate physiological parameters

## Workflow (MATLAB-Based)

1.  **Acquisition**: Automated 24-well plate imaging with pacing protocols
2.  **Motion Tracking** (`EHT_motion_tracker.m`): Template-based post position tracking
3.  **Force Analysis** (`multi_pacing_analysis.m`): Calculate force, contraction/relaxation kinetics, and beat metrics

## Key Features
- **No ImageJ dependency** - all tracking and analysis handled entirely in MATLAB
- **Automated batch processing** of multiple wells and pacing frequencies
- **Dynamic self-calibrating diastolic baseline** computation to auto-correct for tracking offsets
- **Physiological parameter extraction** (force, beat rate, kinetics, T50, C50, R50)
- **Customizable** for different tissue geometries and spacing (configured in `EHT_config.m`)

## Getting Started

See `Code/EHT-analyze/README.md` for detailed usage instructions and **critical template-drawing guidelines.**

## Example Data and Results

Example image sequences and representative results are available in the latest GitHub release:

https://github.com/pulab/EHT-scope/releases/latest

Download `Supplementary Data 4.zip` from the release assets. The archive contains:

- `Analysis_Code`: analysis code included with the supplementary package
- `Representative_Image_Sequences`: example raw image sequences
- `Results`: representative tracking and force-analysis output files

To run the example data, extract the zip file, add `Code/EHT-analyze` to the MATLAB path, and use the extracted `Representative_Image_Sequences` folder as the input data folder.

