---
title: Bounding Box (2D Projection & Ground Truth Generation)
date_created: 2026-04-19
tags:
  - documentation
  - library
  - bounding-box
  - computer-vision
  - linear-algebra
  - thesis-notes
status: active
pare: "[[The Libary]]"
---

# Analytical 2D Bounding Box Projection

The `Boundingbox` module is responsible for generating the ground-truth annotations required for training object detection models. Rather than relying on pixel-based segmentation or computer vision techniques to find the object in the final image, this module uses forward kinematics and projective geometry. 

It mathematically projects a defined geometric plane (representing the object's spatial boundary) from 3D world space onto the 2D camera sensor plane, generating an exact Axis-Aligned Bounding Box (AABB) in pixel coordinates.



## Theoretical Framework & Mathematical Formulation

### 1. Local Bounding Plane Definition
Instead of calculating a full 3D volumetric cuboid, the script defines an Oriented Bounding Plane (a 2D rectangle) that is rigidly attached to the target object's local coordinate system. 

Given the user-defined `box_width` ($w$) and `box_height` ($h$), the four corners of this plane are defined in local object space as homogeneous coordinates $v_{local}$:

$$v_{local} = \begin{bmatrix} \pm \frac{w}{2} \\ \pm \frac{h}{2} \\ 0 \\ 1 \end{bmatrix}$$

### 2. Forward Kinematics (Local to World Transformation)
To determine where these corners exist in the global scene, they are multiplied by the object's $4 \times 4$ transformation matrix $\mathbf{M}_{world}$, which encodes the object's translation, rotation, and scale.

$$v_{world} = \mathbf{M}_{world} \cdot v_{local}$$


*Note: The script also allows binding the bounding box to an `Empty` object via the `use_empty_frame` flag. This allows the bounding box to track an invisible kinematic parent rather than the mesh itself, which is highly beneficial for articulating assemblies or complex grouping hierarchies.*

### 3. Camera Space Projection and Perspective Division
Once the coordinates are in world space, they must be projected onto the camera's image plane. The module utilizes Blender's `world_to_camera_view` utility, which internally applies the camera's extrinsic matrix $\mathbf{M}_{cam}^{-1}$ (to move the points into camera space) and intrinsic projection matrix $\mathbf{K}$. 



After perspective division (dividing by the depth $z$), the function yields Normalized Device Coordinates (NDC) $(u, v)$, where a point perfectly inside the camera frame falls within the range $[0.0, 1.0]$. The variable $w_{depth}$ represents the orthogonal distance from the camera sensor.

### 4. NDC to Absolute Pixel Coordinates
Standard image matrices (e.g., OpenCV, PIL) place the coordinate origin $(0, 0)$ at the top-left of the image. Because Blender's NDC system places the origin at the bottom-left, the $v$ axis must be inverted during the final translation to absolute pixel coordinates $(p_x, p_y)$. 

Given a rendered resolution width $R_x$ and height $R_y$:

$$p_x = u \cdot R_x$$
$$p_y = (1.0 - v) \cdot R_y$$

### 5. Axis-Aligned Bounding Box (AABB) Extraction
To generate the final annotation format required by standard object detection architectures (e.g., YOLO, Faster R-CNN), the projected polygon is circumscribed by finding the absolute extrema of the projected pixel coordinates:

$$x_{min} = \min(p_{x,1}, p_{x,2}, p_{x,3}, p_{x,4})$$
$$x_{max} = \max(p_{x,1}, p_{x,2}, p_{x,3}, p_{x,4})$$

The identical minimum and maximum evaluations are performed for the $y$ axis to define the final 2D box.

---

## High-Level API

### `project_object_space_box()`
Iterates over the active frame range, performs the matrix projections, and logs the bounding box coordinates.

**Parameters:**
* `scene` (bpy.types.Scene): The active Blender scene.
* `camera` (bpy.types.Object): The active rendering camera.
* `obj` (bpy.types.Object): The target object to be tracked.
* `box_name` (str): Identifier used for creating the output directory.
* `box_width` / `box_height` (float): Spatial dimensions of the bounding plane in meters.
* `use_empty_frame` (bool): Toggles whether the box inherits the transformation matrix from `frame_empty` instead of `obj`.
* `frame_empty` (bpy.types.Object | None): An optional anchor object.
* `local_center` (Vector): Optional positional offset from the object's origin.
* `out_base_dir` (str | None): Destination path for the generated dataset logs.

**Output:**
* Generates a comprehensive `bb_tracking.json` containing exhaustive scene metadata (camera intrinsics/extrinsics, 3D world corners, etc.).
* Generates a lightweight `bb_tracking.csv` containing only the frame number, 2D AABB extrema ($x_{min}$, $y_{min}$, $x_{max}$, $y_{max}$), and a boolean visibility flag.

---

## Visual Debugging Utility

### `show_bb(target, height, width, offset)`
A developer utility designed to visually validate the mathematical boundary logic inside the Blender viewport.
* Dynamically generates a 3D mesh plane matching the exact dimensions of the analytical bounding box.
* Parents the mesh to the target object to inherit its kinematics.
* Assigns a highly transparent red (`RGBA: 1.0, 0.0, 0.0, 0.4`) Principled BSDF material.
* Hardcodes `hide_render = True` to ensure the debugging geometry does not accidentally contaminate the final synthesized dataset.