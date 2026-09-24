---
title: Helper Scripts & Utilities
date_created: 2026-04-19
tags:
  - documentation
  - library
  - utils
  - helpers
status: active
parent: "[[DynoText]]"
---

# Helper Scripts & Utilities

## Video Processing & Cropping (`video_crop.py`)

A standalone post-processing script designed to parse the generated `.mp4` renders and their associated bounding box JSONs. It calculates a stable, quantized crop area over the duration of the video and uses FFmpeg to output tightly cropped clips of the medical assets.
### Core Functions

* **`compute_crop_rect(fm, w, h, scale, pad_px, q_lo, q_hi)`**
  Calculates a constant, unified bounding box across all frames of the video. It uses statistical percentiles (`q_lo=5.0`, `q_hi=95.0`) to aggressively filter out outliers, jitter, and frames where the object gets clipped by the camera border.
* **`make_even_crop(x0, y0, x1, y1, w, h)`**
  A strict safety check that forces the crop width and height to be even numbers. This is a hard requirement for FFmpeg when encoding to the standard `yuv420p` pixel format.
* **`process_video(video_path, json_path, name, out_dir, ...)`**
  The main execution pipeline. It opens the source video using OpenCV (`cv2.VideoCapture`), crops the numpy array frame-by-frame, and pipes the raw bytes directly into an FFmpeg subprocess using the `h264_videotoolbox` hardware encoder for rapid compression.
* **`gen_name(json_path)`**
  A string manipulation helper that parses the pipeline's deeply nested output directory structure (up to 15 levels deep) and condenses it into a flat, standardized filename (e.g., `syr-run-img-wb-cen-box.mp4`).

### Command Line Interface (CLI)
Because this script runs outside of Blender, it can be executed directly via terminal with several configurable arguments:
* `--root`: *(Required)* The base directory containing the rendered `.mp4` and `.json` files.
* `--csv` / `--csv_col`: Allows passing a specific CSV list of filenames to filter the jobs, ensuring only specific subsets of the dataset are processed.
* `--out_dir`: Destination folder for the cropped videos.
* `--crop_scale`: Multiplier for the bounding box size (e.g., `1.2` adds a 20% margin).
* `--crop_pad`: Absolute pixel padding added to the crop.
* `--visible_only`: If flagged, the crop calculation strictly ignores frames where the `visible` boolean was logged as False during generation.


## Video Annotation Overlay (`video_draw_bb.py`)

A post-processing debugging and validation utility. This script parses the generated `.mp4` renders and their associated bounding box JSONs, visually rendering the ground-truth 2D polygons directly onto the video frames. This is essential for verifying the mathematical accuracy of the projection matrices used during dataset generation.



### Core Functions

* **`draw_poly(frame, poly, color, thickness, alpha, label, scale)`**
  Utilizes OpenCV to draw the bounding polygons onto the numpy image arrays. It supports scaling the box, adding a text label, and rendering a semi-transparent fill using `cv2.fillPoly` and `cv2.addWeighted` for high-visibility visual debugging.
* **`process_video(video_path, json_path, name)`**
  The main execution loop. It opens the source video, iterates through the frames, looks up the corresponding bounding box from the JSON frame map, and applies the `draw_poly` overlay. The annotated raw frames (`bgr24`) are then piped directly into an FFmpeg subprocess using the `h264_videotoolbox` hardware encoder for rapid export.
* **`load_json_as_frame_map(path, default_name)`**
  Parses the comprehensive bounding box JSON and extracts just the `tl`, `tr`, `br`, `bl` corner coordinates into a lightweight, frame-indexed dictionary.
* **`find_files` & `gen_name`**
  Directory traversal and string manipulation helpers that parse the deep nested output structure to generate a condensed, standardized filename (e.g., `syr-run-img-wb-cen-box.mp4`), identical to the cropping utility.

### Command Line Interface (CLI)
This script is executed directly via the terminal:
* `--root`: *(Required)* The base directory containing the rendered `.mp4` and `.json` files. The script will recursively search this directory for valid render outputs and process them in batches.

## Multi-Object Video Annotation Overlay (`video_draw_multi_bb.py`)

A localized, single-video debugging tool designed to overlay multiple tracking JSONs onto a single render. While the bulk-processing script handles entire dataset directories, this script is used to validate scenes containing multiple tracked assets simultaneously, utilizing a predefined color palette to visually differentiate each object's ground-truth bounding box.



### Core Functions

* **Color Palette Mapping:**
  Maintains a list of distinct, high-contrast BGR colors (`PALETTE`). As the script iterates through the provided JSON files, it assigns a unique color to each tracking target to prevent visual confusion.
* **`draw_poly(frame, poly, color, thickness, alpha, label, scale)`**
  Draws the scaled, semi-transparent polygons and text labels using OpenCV, matching the logic of the bulk-processing script.
* **Execution Loop (`main`)**
  Unlike the bulk script which pipes raw bytes to an FFmpeg subprocess, this script relies on OpenCV's native `cv2.VideoWriter` (using the `avc1` codec) for straightforward, local file generation. It loops through each frame, applying the respective polygon from every loaded JSON tracker before writing the frame to disk.

### Command Line Interface (CLI)
Designed for targeted execution on a single video file, with highly customizable visual parameters:
* `--video`: *(Required)* Path to the source video.
* `--json`: *(Required)* One or more paths to the `bb_tracking.json` files (using `nargs="+"` to accept multiple inputs).
* `--out`: *(Required)* Output path for the annotated video.
* `--start-frame`: Adjusts for 1-based (Blender) vs 0-based index alignment (default: `1`).
* `--alpha` / `--thickness`: Visual overrides for the bounding box fill opacity and line weight.
* `--draw-invisible`: Forces the script to draw the polygon even if the dataset logged the object as occluded or off-screen (`visible==False`).

## Synthetic IMU Data Generation (`generate_synthetic_imu.py`)

A data-synthesis utility that mathematically simulates iOS CoreMotion data for human locomotion (e.g., running, walking). Instead of relying on physical device recordings, this script uses harmonic oscillators and statistical noise to generate infinite, deterministic CSV tracks that are natively compatible with the `imu_preprocess.py` (Camera Shake) module.



### Theoretical Formulation

Human bipedal locomotion is fundamentally periodic. The script models this by decomposing movement into two primary base frequencies:
1.  **Step Frequency ($f_{step}$):** The frequency of individual footfalls (e.g., 2.5 Hz).
2.  **Stride Frequency ($f_{stride}$):** The frequency of a complete gait cycle (left + right foot), which is exactly half the step frequency ($f_{stride} = \frac{f_{step}}{2}$).

These frequencies are converted into angular velocities ($\omega = 2\pi f$) to drive a series of harmonic equations for attitude, rotation rate, and user acceleration. 

To simulate the physical imperfections of real-world sensors and human movement, Gaussian white noise $\mathcal{N}(\mu, \sigma^2)$ is injected into every signal.

**Example: Attitude Synthesis**
The pitch (forward/backward tilt) is dominated by individual steps, while roll (side-to-side sway) and yaw are dominated by the full stride cycle:

$$Pitch(t) = A_{pitch} \sin(\omega_{step} t) + \mathcal{N}(0, 0.01)$$
$$Roll(t) = A_{roll} \sin(\omega_{stride} t) + \mathcal{N}(0, 0.01)$$
$$Yaw(t) = A_{yaw} \cos(\omega_{stride} t) + \mathcal{N}(0, 0.01)$$

**Example: Acceleration Synthesis**
Vertical acceleration (Y-axis in device space) is the most complex, modeled as a superposition of the primary step frequency (phase-shifted to represent the impact) and its first harmonic (representing the secondary bounce), plus higher variance noise:

$$a_y(t) = 0.7 \sin\left(\omega_{step} t - \frac{\pi}{2}\right) + 0.3 \sin(2 \omega_{step} t) + \mathcal{N}(0, 0.15)$$

### Core Functionality

* **`generate_running_imu_data(duration_sec, sample_rate_hz, step_freq_hz, base_uptime_sec)`**
  Computes the time-series arrays using NumPy and packages them into a Pandas DataFrame. 
  * **`base_uptime_sec`:** Simulates the iOS `motionTimestamp_sinceReboot(s)` format, ensuring compatibility with our CoreMotion CSV parser.
  * Outputs precisely formatted column headers: `motionYaw(rad)`, `motionRotationRateX(rad/s)`, `motionUserAccelerationY(G)`, etc.
* **Execution (`main`)**
  Generates the synthetic DataFrame and exports it as `synth_shake.csv`, ready to be ingested by the Blender pipeline.


## Interactive CSV Trimming (`trim_csv.py`)

A Command Line Interface (CLI) utility designed to interactively clean raw time-series CSV data (such as recorded iOS CoreMotion IMU tracks). It uses `pandas` and `matplotlib` to render a live, interactive plot of three selected data columns, allowing the user to visually scrub the start and end points of the recording to remove unwanted noise (e.g., handling the device before/after a walk).



### Core Functions

* **`plot_view(df, sample_col, cols, title_suffix)`**
  Clears and re-renders the live Matplotlib figure (`plt.ion()`). It plots the exact three telemetry columns specified by the user against the sample index, updating in real-time as the user tests different trim boundaries.
* **`ask_sample_point(df, sample_col, cols, mode_label)`**
  An interactive terminal loop that prompts the user for a specific integer sample index. Once entered, it immediately updates the `plot_view` to show a preview of the newly sliced data, requiring a `[y/N]` confirmation before locking in the start or end frame.
* **Execution Loop (`main`)**
  Handles the file I/O operations. It automatically generates a `SampleIndex` column if one does not exist, guides the user through the start/end selection process, validates that the indices are logically ordered, and exports the tightly cropped subset as a new `_trimmed.csv`.

### Command Line Interface (CLI)

The script is heavily reliant on terminal arguments to define which data to visualize:
* `csv`: *(Required)* Positional argument for the input CSV file path.
* `--cols`: *(Required)* Exactly three column headers to plot (e.g., `--cols motionUserAccelerationX(G) motionUserAccelerationY(G) motionUserAccelerationZ(G)`).
* `--sample-col`: Explicitly define which column to use as the X-axis time/sample index. If omitted, the script auto-generates a 0-indexed column.
* `--out`: Custom output path. Defaults to `<original_name>_trimmed.csv`.
* `--delimiter`: Override for the `pandas` CSV delimiter auto-detection.

## Video Frame Trimming (`trim_video_by_frames.py`)

A precise, frame-based video slicing utility built on `moviepy`. While most standard video tools trim based on timecodes (seconds/minutes), this script allows you to trim using exact integer frame indices. This is strictly necessary when syncing real-world background video plates to the exact boundaries of your trimmed IMU CSV data.



### Core Functions

* **`trim_video_by_frames(input_path, output_path, start_frame, end_frame)`**
  Loads the video clip and performs the mathematical conversion from 0-based frame indices to absolute time in seconds ($t_{start} = frame_{start} / fps$). 
  * It includes automatic clamping, warning the user and defaulting to the final available frame if the requested `end_frame` exceeds the video's actual duration.
  * The subclip is extracted and re-encoded using the highly compatible `libx264` video codec and `aac` audio codec.

### Command Line Interface (CLI)

Designed for rapid execution via terminal using strictly positional arguments:
* `input`: *(Required)* Path to the source video file.
* `output`: *(Required)* Destination path for the sliced video.
* `start_frame`: *(Required)* The 0-based integer index of the first frame to keep.
* `end_frame`: *(Required)* The 0-based integer index of the final frame to keep (inclusive).

**Example Usage:**
`python trim_video.py background_raw.mp4 background_synced.mp4 150 450`