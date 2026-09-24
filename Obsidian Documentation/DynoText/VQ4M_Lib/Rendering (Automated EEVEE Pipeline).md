---
title: Rendering (Automated EEVEE Pipeline)
date_created: 2026-04-19
tags:
  - documentation
  - library
  - rendering
  - eevee
  - motion-blur
  - thesis-notes
status: active
parent: "[[The Libary]]"
---

# Automated Rendering & Motion Blur Synthesis Pipeline

The `Rendering` module is responsible for standardizing the image synthesis pipeline across the dataset. It interfaces with Blender's real-time rasterization engine (EEVEE) to configure spatial and temporal sampling, shadows, and video encoding parameters. 

Crucially, this module guarantees backwards compatibility across major Blender API revisions while deterministically mapping physical camera exposure parameters into the virtual environment.

## Theoretical Framework & Mathematical Formulation

### 1. Temporal Motion Blur Kinematics
To generate photorealistic datasets that accurately train computer vision models, the virtual camera must replicate the motion blur characteristics of the target physical sensor. 

In a physical camera, motion blur is a function of the absolute exposure time $t_{exp}$ (in seconds). However, Blender's rendering engine parameterizes motion blur via a unitless shutter variable $S$, which represents the exposure duration relative to the total time occupied by a single frame.

Given a sequence running at $f_{fps}$ frames per second, the time span of a single frame is:

$$\Delta t_{frame} = \frac{1}{f_{fps}}$$

The normalized shutter parameter $S$ is mathematically derived by calculating the ratio of the physical exposure time to the frame duration:

$$S = \frac{t_{exp}}{\Delta t_{frame}} = t_{exp} \cdot f_{fps}$$



The script configures the `motion_blur_position` to `'CENTER'`, meaning the synthetic shutter opens and closes symmetrically around the exact temporal center of the current frame, integrating the object's trajectory over the interval $\left[-\frac{S}{2}, \frac{S}{2}\right]$. The continuous trajectory is discretely sampled using $N_{steps}$ (`blur_steps`), typically set to 32 to ensure smooth sub-frame interpolation.

### 2. Temporal Anti-Aliasing (TAA) and Shadow Quality
Rasterization engines inherently suffer from spatial aliasing at polygon edges. EEVEE relies on Temporal Anti-Aliasing (TAA) to accumulate samples across multiple frames, smoothing out these artifacts. The script hardcodes a high fidelity $N_{samples} = 64$ to enforce high geometric edge clarity. Soft shadows and high shadow bleed bias ($100$) are also strictly enforced to ensure realistic ambient occlusion and depth perception in the resulting images.

### 3. Video Encoding and Compression (FFmpeg)
When generating continuous sequences, the script interfaces directly with Blender's `FFMPEG` wrapper. It enforces the H.264 codec using an MPEG-4 container. 



To balance file size with high temporal fidelity (minimizing compression artifacts that could negatively impact downstream neural networks), the sequence is encoded with a Group of Pictures (GOP) size of 12 and a maximum of 2 consecutive B-frames. Audio encoding is strictly disabled (`NONE`) to optimize output size.

---

## High-Level API

### `set_render_settings()`
The primary configuration function that establishes the deterministic render state for the active scene.

**Parameters:**
* `output_path` (str): Absolute or relative filepath for the rendered output.
* `file_format` (str): Image or video format (default: `'FFMPEG'`).
* `codec` (str): Video codec selection (default: `'H264'`).
* `frame_start` (int): The initial frame of the sequence (default: 200).
* `frame_end` (int): The final frame of the sequence (default: 280).
* `overwrite_res` (bool): Toggles the application of the custom `resolution` tuple.
* `resolution` (tuple): Spatial output dimensions $(w, h)$ in pixels (default: (1280, 720)).
* `fps` (int): Simulation and playback frame rate (default: 24).
* `exposure_time` (float): Absolute physical shutter duration in seconds (default: 1/90).
* `blur_steps` (int): Sub-frame interpolation samples for motion blur calculation (default: 32).

### `render()`
Triggers the global Blender animation render operation (`bpy.ops.render.render(animation=True)`) and logs completion to the console.

---

## Internal Processing & Abstraction

### `_force_eevee_engine()` and `_eevee_settings()`
Blender 4.0 introduced a significant engine overhaul, transitioning from `BLENDER_EEVEE` to `BLENDER_EEVEE_NEXT`. These helper functions serve as an abstraction layer, probing the `bpy.context.scene` via `try-except` blocks and `getattr` to dynamically assign the correct renderer and fetch its specific settings struct, preventing API breakage across software updates.