---
title: Camera Recreation (Intrinsic Calibration)
date_created: 2026-04-19
tags:
  - documentation
  - library
  - camera
  - calibration
  - intrinsics
  - thesis-notes
status: active
parent: "[[The Libary]]"
---

# Virtual Camera Reconstruction from Intrinsic Parameters

The camera recreation module is responsible for bridging the gap between a physical imaging device (e.g., RealWear N500) and its virtual counterpart in Blender. By parsing a JSON file containing calibration data—typically derived from checkerboard calibration algorithms in OpenCV—this script mathematically maps the idealized Pinhole Camera Model to Blender's simulated physical sensor.

## Theoretical Framework & Mathematical Formulation

### 1. The Intrinsic Camera Matrix
In standard computer vision literature, the transformation from 3D camera coordinates to 2D image pixel coordinates is defined by the intrinsic camera matrix $\mathbf{K}$:

$$\mathbf{K} = \begin{bmatrix} f_x & 0 & c_x \\ 0 & f_y & c_y \\ 0 & 0 & 1 \end{bmatrix}$$



Where:
* $f_x, f_y$ represent the focal length expressed in pixel units.
* $c_x, c_y$ represent the principal point (optical center) in pixel coordinates.

### 2. Focal Length Domain Conversion
Blender's rendering engine requires the focal length to be expressed in metric units ($f_{mm}$), simulating a physical lens, rather than the pixel-based focal length ($f_x$) provided by OpenCV. To perform this translation, the physical width of the camera sensor ($w_{sensor}$) and the image resolution width in pixels ($w_{px}$) must be known.

The metric focal length is derived using the ratio of physical sensor width to image pixel width:

$$f_{mm} = f_x \frac{w_{sensor}}{w_{px}}$$

*Note: If the physical sensor width is unavailable in the calibration data, the script defaults to a standard 6.30 mm sensor.*

### 3. Principal Point Offset (Sensor Shift)
Ideally, the principal point $(c_x, c_y)$ lies exactly at the geometric center of the image. However, manufacturing imperfections cause the true optical axis to intersect the sensor off-center. 

Blender corrects this via "Sensor Shift" parameters. Unlike OpenCV, which uses absolute pixel coordinates from the top-left origin, Blender uses normalized, relative offset values ($\Delta x, \Delta y$) calculated from the geometric center. 

The mathematical mapping from OpenCV pixel coordinates to Blender shift coordinates is:

$$\Delta x = \frac{c_x - \frac{w_{px}}{2}}{w_{px}}$$

$$\Delta y = -\frac{c_y - \frac{h_{px}}{2}}{h_{px}}$$

*Note: The negative sign applied to $\Delta y$ accounts for the inverted Y-axis direction between standard 2D image coordinates (top-to-bottom) and Blender's sensor shift coordinates (bottom-to-top).*

### 4. Radial Lens Distortion

Physical lenses introduce non-linear geometric distortion, most commonly radial distortion (barrel or pincushion). The first-order radial distortion coefficient $k_1$ models this displacement. To replicate this effect in the virtual pipeline, the script injects a compositor node structure. 

Because Blender's `CompositorNodeLensdist` does not strictly map 1:1 with the Brown-Conrady distortion model used by OpenCV, an empirical heuristic multiplier is applied to approximate the visual effect:

$$k_{blender} \approx k_1 \times 0.7$$

---

## High-Level API

### `create_camera_from_calibration_json()`
Instantiates a perfectly calibrated 3D camera object matching the physical device.

**Parameters:**
* `json_path` (str): Absolute or relative path to the calibration JSON file.
* `name` (str): Identifier for the generated Blender object (default: "RealWear_N500").
* `location` (tuple): Initial 3D translation $(x, y, z)$.
* `rotation_euler_deg` (tuple): Initial rotation in degrees $(roll, pitch, yaw)$.
* `sensor_width_mm` (float | None): Explicit override for physical sensor width.
* `set_scene_resolution` (bool): If True, automatically scales the Blender scene render dimensions to match the $w_{px}$ and $h_{px}$ from the JSON.
* `apply_principal_point_shift` (bool): Toggles the calculation and application of $\Delta x$ and $\Delta y$.
* `add_simple_lens_node` (bool): If True, dynamically generates a compositor node tree to apply the $k_1$ radial distortion heuristic.

**Returns:**
* `cam_obj`: The instantiated `bpy.types.Object` representing the matched camera.
* `et`: The extracted exposure time (float) from the physical camera metadata, useful for downstream motion blur calculations.

---

## Internal Object Data Properties
For downstream reference, the script embeds the raw intrinsic variables directly into the Blender object's custom properties:
* `cam_obj["fx_px"]`
* `cam_obj["fy_px"]`
* `cam_obj["cx_px"]`
* `cam_obj["cy_px"]`
* `cam_obj["k1"]`