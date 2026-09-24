---
title: Prebuild Scenes (Automated Render Orchestration)
date_created: 2026-04-19
tags:
  - documentation
  - pipeline
  - dataset-generation
  - automation
  - thesis-notes
status: active
parent: "[[DynoText]]"
---

# Prebuild Scenes: Dataset Orchestration

The `prebuild_scenes` master script serves as the high-level operational loop for the DynoText synthetic data pipeline. Instead of manually rendering individual files, this script automates the combinatorial generation of the dataset by iterating through specific medical assets, predefined camera viewpoints, IMU-driven shake profiles, and background configurations.



## 1. Scene Configurations & Viewpoint Mapping

To maintain strict determinism and reproducibility across the dataset, all spatial camera parameters (location and rotation) are hardcoded into a central `SCENE_CONFIGS` dictionary. This ensures that every asset is captured from a standardized set of viewpoints.

The pipeline currently supports five primary medical assets, each with tailored camera configurations:

* **Syringe:** Captures macro details with specific rotational flags (`rot_syring`). Viewpoints: `vertical`, `horizontal`.
* **PulsOX (Pulse Oximeter):** Captures the device at varying depths. Viewpoints: `close_up`, `normal`, `far_away`.
* **Monitor:** Evaluates the screen at multiple off-axis viewing angles (iterating over multiple `asset_id`s). Viewpoints: `center`, `left`, `right`, `up`, `down`.
* **Lifepak:** Defibrillator captured from a hemispherical dome of angles. Viewpoints: `center`, `left`, `right`, `up`, `down`.
* **Gauge:** Analog dial captured from extreme angles to test perspective distortion. Viewpoints: `center`, `left`, `right`, `up`, `down`.

## 2. Dynamic Shake Injection

The script dynamically constructs the list of IMU shake profiles based on the background context:
* `walking`, `running`, `sprinting`, `crouching`, `minimum_shake_walking`, `skipping`.

**Logic Rule:** The static `"noShake"` profile is automatically injected into the generation loop *only* when the scene is rendered without a video background (`use_video_bg = False`). This prevents the generation of redundant, static frames over moving video backgrounds, optimizing render times.

## 3. Standardized Output Hierarchy

A critical function of this script is maintaining a flawless, predictable directory structure for the resulting dataset. All scenes pass their respective configuration dictionaries into standardized helper functions (`render_standard_scene` and `render_syringe_scene`).

The output paths are strictly formatted as:
`{asset}/{movment}/{image_type}/{video_bg_status}/{view_name}`

** Example Output Tree:**
```text
videos/
├── Syringe/  
│   ├── crouching/ 
│   │   └── img1/ 
│	│		├── with_video_bg/ 
│	│		│   ├── close_up/
│	│		│   │   ├── boundingbox/
│	│		│ 	│   │   ├── text_72/
│	│		│	│ 	│   │   ├── bb_tracking.csv
│	│		│	│ 	│   │   └── bb_tracking.json
│	│		│ 	│   │   ├── .../
│	│		│ 	│   │   └── text_spo2/ 
│	│		│   │   └── puls_ox_crouching_img1.mp4 
│	│		│   ├── .../
│	│		│   └── normal/	
│	│		└── without_video_bg/ 
│	│			├── close_up/
│	│			│	├── boundingbox/
│	│			│   │   ├── text_72/
│	│			│ 	│   │   ├── bb_tracking.csv
│	│			│ 	│   │   └── bb_tracking.json
│	│			│   │   ├── .../
│	│			│   │   └── text_spo2/ 
│	│			│   └── puls_ox_crouching_img1.mp4 
│	│			├── .../
│	│			└── normal/	
│	├── .../
│   └── walking/ 
├── .../
└── Gauge/
```    

 
