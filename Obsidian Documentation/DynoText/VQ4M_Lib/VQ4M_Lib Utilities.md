---
title: VQ4M_Lib Utilities
date_created: 2026-04-19
tags:
  - documentation
  - library
  - utils
  - helpers
status: active
parent: "[[The Libary]]"
---

# VQ4M_Lib Utilities

This section outlines the standard utility functions used across the `VQ4M_Lib` pipeline for scene management, file handling, and basic asset loading.

## Model Loading

* **`load_obj(obj_path, target_location, target_rotation, uniform_scale, mat)`**
  Imports an `.obj` file into the scene, immediately applying a uniform scale, spatial transforms, and a designated material. 
  * *Note: Assumes the imported OBJ is the first/only object instantiated by the import operation.*

## Scene Management (`general.py`)

* **`clean_scene()`**
  Safely resets the Blender environment. It deletes all objects and collections, then aggressively loops through the data API (meshes, materials, images, etc.) to purge unlinked, orphaned data blocks, ensuring a pristine state for the next render task.
* **`create_parent(name, location, rotation)`**
  Spawns a 'PLAIN_AXES' Empty object at the specified coordinates, useful for establishing kinematic parenting hierarchies.
* **`ensure_camera(location, rotation)`**
  Checks the scene for an active camera. If one exists, it sets it as the active scene camera; if not, it spawns a new one at the provided coordinates.

## File & Configuration Handling (`general.py`)

* **`list_files_by_extension(root_dir, extension, absolute, include_root)`**
  A recursive directory walker. Returns a sorted list of file paths that match the requested extension(s) (e.g., `["png", "jpg"]`). Can return absolute paths or paths relative to the root.
* **`load_profile(base_dir)`**
  Loads standard configuration parameters from `configs/base.json`. It strictly validates required fields (like `scene_length`) and merges settings (like `shake_settings`) into a usable configuration dictionary.
* **JSON Validation Helpers (`_read_json`, `_require_int`, `_require_seq_len`, `_reject_unknown`)**
  Internal validation functions used by `load_profile` to ensure data types, enforce minimum values, check sequence lengths, and reject unexpected keys in the JSON config.