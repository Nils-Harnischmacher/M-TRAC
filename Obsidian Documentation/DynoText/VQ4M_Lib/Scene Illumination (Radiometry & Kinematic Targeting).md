---
title: Scene Illumination (Radiometry & Kinematic Targeting)
date_created: 2026-04-19
tags:
  - documentation
  - library
  - lighting
  - radiometry
  - linear-algebra
  - thesis-notes
status: active
parent: "[[The Libary]]"
---

# Scene Illumination & Deterministic Targeting

The `Lighting` module is responsible for algorithmically constructing the radiometric environment of the synthetic dataset. To ensure domain randomization and physical accuracy, lighting cannot be placed arbitrarily; it must be procedurally generated, explicitly targeted, and parametrically driven by real-world radiometric units (Watts, Kelvin) and geometric constraints (cone angles, surface areas).

## Theoretical Framework & Mathematical Formulation

### 1. Radiometry and Color Temperature
In a physically-based rendering (PBR) pipeline, light sources are not defined by arbitrary RGB values, but by spectral emission curves. The script utilizes a Shader Node tree to map a defined thermodynamic temperature $T$ (in Kelvin) to a visible color spectrum using Planck's law of black-body radiation. 



The total radiant flux $\Phi_e$ emitted by the source is parameterized in Watts (**W**). Blender's rendering engine automatically computes the inverse-square falloff of this energy over distance $r$:

$$E = \frac{\Phi_e}{4 \pi r^2}$$

Where $E$ is the irradiance (energy per unit area) hitting the target object.

### 2. Kinematic Targeting (Orthonormal Basis Construction)
A critical feature of the automated lighting pipeline is the `_look_at_rotation()` function. Rather than relying on Blender's constraint solver (which incurs dependency graph overhead), the script can analytically compute the exact Euler rotation required to orient a light's local axis (e.g., the optical axis $-Z$) toward a spatial coordinate $\mathbf{p}_{target}$.



Given the light's origin $\mathbf{p}_{origin}$, the normalized forward direction vector $\mathbf{f}$ is defined as:

$$\mathbf{f} = \frac{\mathbf{p}_{target} - \mathbf{p}_{origin}}{\|\mathbf{p}_{target} - \mathbf{p}_{origin}\|}$$

To construct a valid 3D rotation matrix, we require an orthonormal basis. An arbitrary world up-vector $\mathbf{u}_{world}$ is selected (defaulting to the global $Z$-axis $(0,0,1)^T$, unless $\mathbf{f}$ is nearly parallel to $Z$, in which case $(0,1,0)^T$ is used to prevent gimbal lock).

The orthogonal right vector $\mathbf{r}$ is found via the cross product:

$$\mathbf{r} = \frac{\mathbf{f} \times \mathbf{u}_{world}}{\|\mathbf{f} \times \mathbf{u}_{world}\|}$$

The true orthogonal up vector $\mathbf{u}$ is then mathematically guaranteed by:

$$\mathbf{u} = \frac{\mathbf{r} \times \mathbf{f}}{\|\mathbf{r} \times \mathbf{f}\|}$$

By mapping these derived vectors $(\mathbf{r}, \mathbf{u}, \mathbf{f})$ to the light's designated local axes, a $3 \times 3$ rotation matrix $\mathbf{R}$ is constructed and converted to Euler angles to establish the absolute world rotation.

### 3. Light Typologies & Geometric Optics
The module supports four distinct optical emission profiles, each parameterizing how the radiometric energy propagates through the simulated volume:



* **POINT:** Isotropic emission from an infinitely small coordinate. Parameterized by `shadow_soft_size` (virtual radius) to control the penumbra (softness) of cast shadows.
* **SPOT:** Conical emission. Parameterized by a solid angle `spot_size_deg` $\theta$ and a `spot_blend` factor $\beta$ which defines the smooth Hermite interpolation between the inner unattenuated cone and the outer boundary.
* **SUN:** Directional lighting simulating a source at infinite distance. Energy does not undergo inverse-square falloff. Parameterized by `sun_angle_deg`, representing the apparent angular diameter (e.g., **0.53°** for Earth's sun) to dictate shadow softness.
* **AREA:** Planar emission from a geometric surface (Square, Rectangle, Disk, Ellipse). Provides the most physically accurate soft shadows, computing irradiance via surface integration over `area_size`.

---

## High-Level API

### `upsert_light()`
A highly robust, idempotent function that either instantiates a new light or updates an existing datablock to match the exact physical parameters requested. 

**Core Radiometric Parameters:**
* `name` (str): Identifier for the light object.
* `type` (str): `'POINT'`, `'SUN'`, `'SPOT'`, or `'AREA'`.
* `energy` (float): Radiant flux in Watts.
* `color` (tuple): Linear RGB multiplier (default: (1.0, 1.0, 1.0)).
* `temperature` (float | None): If provided (and `use_nodes=True`), overrides RGB with Blackbody radiation temperature in Kelvin.

**Targeting Parameters:**
* `target_obj` (bpy.types.Object): If provided with `make_constraint=True`, adds a dynamic `'TRACK_TO'` constraint.
* `target_location` (tuple): If provided, analytically computes the rotation matrix via `_look_at_rotation()`.
* `align_axis` (str): The local axis pointing at the target (default: `'-Z'`).
* `up_axis` (str): The local axis pointing upwards (default: `'+Y'`).

**Typology-Specific Parameters:**
* `spot_size_deg` / `spot_blend` (float): Cone angle and penumbra falloff.
* `sun_angle_deg` (float): Apparent angular diameter for directional shadow softness.
* `area_shape` / `area_size`: Geometry and dimensions of planar emitters.
* `shadow_soft_size` (float): Virtual radius for Point/Spot shadows.