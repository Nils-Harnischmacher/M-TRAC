---
title: Shake (IMU Preprocessing)
date_created: 2026-04-19
tags:
  - documentation
  - library
  - imu
  - physics
  - kinematics
  - thesis-notes
status: active
parent: "[[The Libary]]"
---

# Camera Shake: Kinematic Reconstruction from IMU Data

The `imu_preprocess.py` module reconstructs realistic 6-Degree-of-Freedom (6-DoF) camera trajectories from raw Inertial Measurement Unit (IMU) data (e.g., iOS CoreMotion). This process involves transforming local device accelerations into a global reference frame and performing double numerical integration. 

To counteract the unbounded drift inherent in integrating noisy accelerometer data, this module implements a deterministic, non-linear spring-damper system (the "rubberband" algorithm) that acts as a low-frequency high-pass filter, physically anchoring the trajectory.

## Theoretical Framework & Mathematical Formulation

### 1. Coordinate Frame Transformation
Raw accelerometer readings $\mathbf{a}_{raw}$ are captured in the device's local coordinate system. To map these to the 3D application space (Blender), an initial correction matrix $\mathbf{C} \in \mathbb{R}^{3 \times 3}$ is applied to orthogonalize the axes:

$$\mathbf{a}_{dev} = \mathbf{C} \mathbf{a}_{raw}$$

The orientation of the device at time $t$ is given as a quaternion $\mathbf{q}_t$. To establish a zero-centered origin frame, the rotation is measured relative to the initial frame $\mathbf{q}_0$:

$$\mathbf{q}_{center}(t) = \mathbf{q}_0^{-1} \otimes \mathbf{q}_t$$

The acceleration vector is then rotated into the world coordinate frame using the rotation matrix equivalent of the centered quaternion, denoted as $\mathbf{R}(\mathbf{q}_{center})$:

$$\mathbf{a}_{world}(t) = \mathbf{R}(\mathbf{q}_{center}(t)) \mathbf{a}_{dev}(t)$$

An optional fixed spatial offset $\mathbf{q}_{fix}$ can be applied to align the final camera orientation $\mathbf{q}_{cam}$ to the scene constraints:

$$\mathbf{q}_{cam}(t) = \mathbf{q}_{fix} \otimes \mathbf{q}_{center}(t)$$

### 2. The Drift Problem and Anti-Drift Restoring Forces
Standard kinematic reconstruction relies on integrating acceleration $\mathbf{a}$ to find velocity $\mathbf{v}$ and position $\mathbf{p}$:

$$\mathbf{v}(t) = \int_{0}^{t} \mathbf{a}_{world}(\tau) d\tau, \quad \mathbf{p}(t) = \int_{0}^{t} \mathbf{v}(\tau) d\tau$$

Due to sensor noise and low-frequency bias, standard double integration results in quadratic spatial drift over time ($e_{pos} \propto t^2$). To mitigate this, a simulated physical restoring force is introduced, acting as an artificial anchor.

The total acceleration $\mathbf{a}_{tot}$ evaluated at time $t$ is a superposition of the observed acceleration, a restoring spring acceleration $\mathbf{a}_{spring}$, and a viscous damping acceleration $\mathbf{a}_{damp}$:

$$\mathbf{a}_{tot}(t) = \mathbf{a}_{world}(t) + \mathbf{a}_{spring}(\mathbf{p}) + \mathbf{a}_{damp}(\mathbf{v})$$

**Viscous Damping:**
To prevent oscillation, a damping force proportional to the velocity is applied, parameterized by a damping coefficient $c_{damp}$:
$$\mathbf{a}_{damp} = -c_{damp} \mathbf{v}(t)$$

**Non-Linear Exponential Spring:**
A restoring force pulls the camera back toward the origin $\mathbf{p} = \mathbf{0}$. To allow for small, natural micro-jitters without immediate resistance, a deadband radius $\delta$ is established. If $\|\mathbf{p}\| > \delta$, an exponential spring force is applied:

$$\mathbf{a}_{spring} = - \left( k_{spring} e^{\alpha_{exp} \|\mathbf{p}\|} \right) \frac{\mathbf{p}}{\|\mathbf{p}\|}$$

Where:
* $k_{spring}$ is the base Hookean stiffness coefficient.
* $\alpha_{exp}$ dictates the exponential growth of the restoring force, creating a "soft wall" boundary that increasingly penalizes large deviations from the origin.
* If $\|\mathbf{p}\| \leq \delta$, then $\mathbf{a}_{spring} = \mathbf{0}$.

### 3. Numerical Integration (Trapezoidal Method)
Given the discrete nature of the IMU samples at intervals $\Delta t = t_k - t_{k-1}$, continuous integration is approximated numerically. To minimize discretization errors inherent in the forward Euler method, the system utilizes the Trapezoidal rule for velocity updates:

$$\mathbf{v}_k = \mathbf{v}_{k-1} + \frac{1}{2} \left( \mathbf{a}_{tot, k} + \mathbf{a}_{tot, k-1} \right) \Delta t$$

The position is then updated via standard forward integration using the newly computed velocity:

$$\mathbf{p}_k = \mathbf{p}_{k-1} + \mathbf{v}_k \Delta t$$

---

## High-Level API

### `add_camera_shake()`
The primary entry point for other scripts to apply motion to a Blender camera.

> [!warning] Camera Initialization
> You must place the camera in the scene and set its initial location/rotation before calling this function. The script uses the camera's current transformation as the anchor point ($\mathbf{p}_0$).

**Parameters:**
* `type` (str): The type of shake (e.g., "walking", "running").
* `camera` (bpy.types.Object): The Blender camera object.
* `csv_path` (str): Absolute or relative path to the motion CSV.
* `settings` (dict, optional): A dictionary overriding default physics settings (`trapezoid`, `rubberband`, `k_spring`, `c_damp`, `deadband`, `alpha_exp`).

---

## Internal Processing Functions

### `imu_to_trajectory()`
The core physics engine. It iterates through the IMU frames and calculates the new position and velocity based on the theoretical framework outlined above.

### `apply_trajectory_to_object()`
Takes the simulated trajectory list and bakes it into the Blender timeline. 
* Clears existing animation data.
* Sets keyframe interpolation to `LINEAR`.
* Translates the simulated points relative to the camera's `base_location` (anchor).

### `load_ios_coremotion_csv()`
Parses the specific column formats generated by the iOS CoreMotion app. Extracts timestamps, Euler angles (converted to quaternions), and acceleration vectors, immediately converting G-forces to $m/s^2$.