---
title: Color Correction (CCM Pipeline)
date_created: 2026-04-19
tags:
  - documentation
  - library
  - colorimetry
  - rendering
  - linear-algebra
  - thesis-notes
status: active
parent: "[[The Libary]]"
---

# Sensor Colorimetry Mimicry via Affine Transformations

The `Colorcorrection` module is designed to bridge the radiometric gap between Blender's mathematically ideal, physically-based rendering (PBR) engine and the specific spectral sensitivity of a target physical camera. 

By applying a Color Correction Matrix (CCM) and an optional offset vector to the rendered image in post-processing, the pipeline synthesizes an affine transformation that maps the synthetic color space onto the empirical color space of the real-world sensor.



## Theoretical Framework & Mathematical Formulation

### 1. The Affine Color Transformation Model
In digital imaging, sensor colorimetry is commonly approximated using a first-order linear transformation (with an optional bias) applied to the trichromatic color values. Let the input pixel color from the rendering engine be represented as a column vector $\mathbf{C}_{in} = [R_{in}, G_{in}, B_{in}]^T$. 

The target output color $\mathbf{C}_{out}$ is calculated via an affine transformation defined by a $3 \times 3$ weight matrix $\mathbf{W}$ (the CCM) and a $3 \times 1$ bias/offset vector $\mathbf{b}$:

$$\mathbf{C}_{out} = \mathbf{W} \mathbf{C}_{in} + \mathbf{b}$$

Expanding this into its scalar components yields the exact system of equations evaluated per-pixel:

$$
\begin{bmatrix} R_{out} \\ G_{out} \\ B_{out} \end{bmatrix} = 
\begin{bmatrix} 
W_{00} & W_{01} & W_{02} \\ 
W_{10} & W_{11} & W_{12} \\ 
W_{20} & W_{21} & W_{22} 
\end{bmatrix} 
\begin{bmatrix} R_{in} \\ G_{in} \\ B_{in} \end{bmatrix} + 
\begin{bmatrix} b_0 \\ b_1 \\ b_2 \end{bmatrix}
$$

### 2. Node-Based Linear Algebra Approximation
Because Blender's Compositor environment does not provide native vector-matrix multiplication nodes, this affine transformation must be topologically unrolled into a scalar node graph. 



The script dynamically constructs a custom node group that mathematically evaluates the expanded polynomials. For example, the red output channel is computed programmatically as:

$$R_{out} = \min(\max((R_{in} \cdot W_{00}) + (G_{in} \cdot W_{01}) + (B_{in} \cdot W_{02}) + b_0, 0), 1)$$

> [!note] Radiometric Clamping
> All mathematical operations in the synthesized node tree are instantiated with `use_clamp = True`. This enforces a non-linear bounding operation, restricting the intermediate and final floating-point color values to the normalized range $[0.0, 1.0]$. This is critical to prevent energy conservation violations (e.g., negative light or blown-out highlights) resulting from aggressive matrix weights.

---

## High-Level API & Pipeline Integration

The module injects the CCM directly into Blender's post-processing render pipeline, intercepting the image between the `R_LAYERS` (Render Layers) output and the final `COMPOSITE` output.

### `load_matrix(json_path)`
Parses the calibration JSON.
* **Input:** Path to a JSON file containing `matrix_3x3_rowmajor` and an optional `offset`.
* **Output:** Extracts the values into NumPy arrays: $\mathbf{W} \in \mathbb{R}^{3 \times 3}$ and $\mathbf{b} \in \mathbb{R}^3$.

### `create_ccm_group(name="CameraCCM")`
The core graph synthesis function.
* **Functionality:** Generates a custom Compositor Node Group containing exactly 1 separator node, 9 multiply nodes, 6 addition nodes, and 1 combine node.
* **Returns:** A tuple containing the initialized `NodeTree` and a dictionary mapping string identifiers to the specific operational nodes (allowing for future weight updates).

### `set_weights(nodes_map, W, b)`
Applies the empirically derived calibration parameters to the node graph.
* **Functionality:** Maps the components of $\mathbf{W}$ and $\mathbf{b}$ directly into the `default_value` parameter of the corresponding multiplication and addition nodes within the `nodes_map`.

### `apply_to_scene(ng, nodes_map)`
Modifies the global scene compositor topology.
* **Functionality:** Ensures the compositor is active, locates the Render Layers and Composite nodes, and splices the instantiated CCM node group (`ng`) into the data flow, simultaneously routing the output to a Viewer node for debugging.