---
title: Installation & Pipeline Usage
date_created: 2026-04-19
tags:
  - documentation
  - setup
  - guide
  - pipeline
  - workflow
status: active
parent: "[[DynoText]]"
---

# Installation & Pipeline Usage Guide

The DynoText / VQ4M pipeline is a hybrid system. The core synthetic data generation runs **inside Blender** using its embedded Python interpreter (`bpy`), while the post-processing, validation, and data-trimming tools run **outside Blender** using your system's standard Python environment.

## 1. Prerequisites & Installation

### A. System Requirements
* **Blender:** Version4.5.5 LTS is recommended 
* **Python:** Version 3.10 or higher.
* **FFmpeg:** Must be installed and added to your system's `PATH` variable (required for the video cropping subprocesses).

### B. Environment Setup: Including External Libraries in Blender

To ensure Blender's internal Python interpreter recognizes the project library, a `.pth` file must be placed in the `site-packages` directory of the Blender installation. This method allows for seamless importing of the library without requiring manual `sys.path` manipulation within individual scripts.
#### 1. Locate the Target Directory
	The `site-packages` directory is located within Blender's internal Python environment. Please identify the path corresponding to your operating system and Blender version. The following examples assume **Blender 4.2**; ensure you adjust the version numbers in the path to match your installation.

##### Windows 
By default, Blender is installed in the Program Files directory.
``` Bash 
C:\Program Files\Blender Foundation\Blender 4.2\4.2\python\lib\site-packages\
```
##### macOS  
Navigate to your Applications folder, right-click `Blender.app`, and select **Show Package Contents**.
```bash
/Applications/Blender.app/Contents/Resources/4.2/python/lib/python3.11/site-packages/
```
##### Linux
The path is relative to the directory where the Blender tarball was extracted or where the binary resides.
```bash
/opt/blender-4.2/4.2/python/lib/python3.11/site-packages/
```
#### 2. Create the .pth File
1.  Create a new text file named `my_project_lib.pth` or use the provided `VQ4M_dev.pth`
2.  Inside this file, enter the **absolute path** to the root directory of your Python library.
    * **Example Content:** `C:\Users\Username\Developer\my_python_library`
3.  Save the file and move it into the `site-packages` directory identified in Step 1.

> [!warning] VQ4M_dev.pth
> You must modify the path in `VQ4M_dev.pth` according to your working directory. 
> ```text
> *PATH TO THE PROJECT*/DynoText/VQ4M_Lib/src
> ```
#### 3. Optional Verification
To confirm that Blender has successfully registered your library, open Blender and execute the following commands in the **Python Console**:

```python
import sys
import my_project_lib  # Replace with your actual library name

# Verify that the path from the .pth file is included in sys.path
for path in sys.path:
    print(path)

# Confirm the library location
print(f"\nLibrary successfully loaded from: {my_project_lib.__file__}")
### B. Python Dependencies (CLI Environment)
For the post-processing tools (`video_crop.py`, `trim_csv.py`, etc.), install the following packages in your local Python environment or Conda virtual environment:
```

### C. Blender Python Dependencies
For the post-processing tools (`video_crop.py`, etc. ) Install the following packages in your Python environment or Conda virtual environment: 
```bash
pip install opencv-python numpy pandas matplotlib moviepy tqdm
```

### D. Installing External Libraries via Terminal

Blender ships with its own isolated Python environment. If you run any scripts inside Blender that require external libraries (like `pandas` or `cv2`), you must install them directly into Blender's Python directory. 

To do this, open your terminal and use the `python` executable located inside your Blender installation path:

#### Windows
```powershell
"C:\Program Files\Blender Foundation\Blender 4.0\4.0\python\bin\python.exe" -m pip install numpy pandas
```

#### macOS

On macOS, the executable is located inside the Blender application bundle. You may need to use `python3.11` or `python3.10`depending on your specific Blender version.
```bash
/Applications/Blender.app/Contents/Resources/4.0/python/bin/python3.11 -m pip install numpy pandas
```
#### Linux

For Linux, the path depends on where you extracted the Blender folder.
```bash
/path/to/blender-4.0-linux-x64/4.0/python/bin/python3.11 -m pip install numpy pandas
```




## 2. Folder structure 
```text
.
├── dataset/
│   ├── calibration.json         # Camera calibration data
│   ├── videos/
│   │   └── [Asset]/             # Syringe, PulsOx, Monitor, etc.
│   │       └── [Movement]/      # Running, sprinting, walking, etc.
│   │           └── [Image_ID]/  # ID of the specific image configuration
│   │               └── [BG_Status]/ # With or without background video
│   │                   └── [View_Angle]/ # View variations (Asset-dependent)
│   │                       ├── *.mp4     # Generated video file
│   │                       └── boundingbox/ # Bounding box tracking (CSV/JSON)
│   ├── csvs/                    # Motion and sensor data
│   └── configs/                 # Configuration file
├── VQ4MLib/                     # Core library source code
│   └── src/VQ4M_Lib/
│       ├── models/              # Code for the 3D models
│       ├── model_helpers/       # Geometry and material utilities
│       └── [core_scripts].py    # Rendering, camera, lighting, etc.
├── assets/
│   ├── textures/                # PBR textures for 3D rendering
│   ├── content_backgrounds/     # Source videos for backgrounds
│   ├── objs/                    # 3D object files (.OBJ)
│   └── content_[device]/        # Device-specific ground truth and images
├── prebuild_scenes/             # Scene setup scripts
├── helper_scripts/              # Utilities for trimming and overlays
├── render_dataset.py            # Main execution script
└── VQ4M_dev.pth                 # Required to include the library in Blender
```   

## 4. How to Render the provided Dataset 

1. Ensure the `VQ4M_Lib` directory is accessible to Blender's `sys.path`. (See section 2)
2. run the following command in `/DynotText/`: 
```bash
blender -b -P render_dataset.py
```


## 5. How to Use the Pipeline (Step-by-Step)

Generating a your own synthetic dataset follows a strict three-phase workflow: **Preparation**, **Generation**, and **Post-Processing**.

### Phase 1: Data Preparation (CLI)

Before opening Blender, prepare your real-world inputs.

1. **Camera Calibration:** Generate your intrinsic camera matrix JSON (e.g., using OpenCV checkerboard calibration) to be ingested by the `Camera recreation` module and place the `calibration.json` in the dataset folder 
    
2. **IMU Preprocessing:** If using real-world iOS CoreMotion data, use the interactive trimmer to remove handling noise at the beginning and end of the recording. Place your final `.csv` files in `/dataset/csvs/`.

``` Bash
python trim_csv.py raw_imu.csv --cols motionUserAccelerationX(G) motionUserAccelerationY(G) motionUserAccelerationZ(G)
```
3. **Video Background Sync:** If you trimmed the IMU data, trim the corresponding video plate to match perfectly using the frame trimmer. Place your final background videos in `/assets/content_backgrounds/background_videos/`.

```Bash
python trim_video_by_frames.py bg_raw.mp4 bg_synced.mp4 150 450
```

(Alternatively, generate synthetic IMU data using `generate_synthetic_imu.py` if no real-world data is available).

> [!warning] Naming
> Corresponding `.csv`  files and background videos have to have the same name and are also called by that name in the script. 



### Phase 2: Dataset Generation (Inside Blender)

1. Open your master Blender file containing your medical assets.
    
2. Ensure the `VQ4M_Lib` directory is accessible to Blender's `sys.path`. (See section 2)
    
3. Open Blender's Scripting workspace and load the `prebuild_scenes.py` script.
    
4. Run the script. The orchestrator will automatically iterate through the assets, background configurations, and shake profiles, rendering the `.mp4` files and `bb_tracking.json` files to the output directory.
Alternatively you can start the render from the terminal by running the following command: 
```bash
blender -b -P render_dataset.py
```
> [!Note] Settings
> If you want to change the look and feel of the shake please change the settings in `/DynoText/dataset/csvs/configs/base.json` 

### Phase 3: Optional Post-Processing & Validation (CLI)

Once Blender finishes rendering the raw dataset, use the post-processing utilities to prepare the data for neural network training.

1. **Crop the Videos:** Use the bounding box data to tightly crop the medical assets out of the full-frame renders.
``` Bash
python video_crop.py --root ./output_dataset --out_dir ./cropped_dataset
```
   
2. **Visual Validation:** Double-check the math. Overlay the JSON bounding boxes onto the rendered videos to ensure perfect alignment.   
```Bash
python video_draw_bb.py --root ./cropped_dataset
```
3. The dataset is now ready to be ingested by your PyTorch or TensorFlow data loaders!

