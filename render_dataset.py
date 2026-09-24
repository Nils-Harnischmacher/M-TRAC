import bpy
import sys
import os
import importlib

# --- PATH SETUP ---
script_dir = os.path.dirname(bpy.data.filepath)
if script_dir not in sys.path:
    sys.path.append(script_dir)

# --- IMPORTS & RELOADS ---
import prebuild_scenes.scene_gauge as scene_gauge
import prebuild_scenes.scene_Lifepak as scene_Lifepak
import prebuild_scenes.scene_mointor as scene_monitor  
import prebuild_scenes.scene_pulsOX as scene_pulsOX
import prebuild_scenes.scene_syringe as scene_syringe

modules = [scene_gauge, scene_Lifepak, scene_monitor, scene_pulsOX, scene_syringe]
for mod in modules:
    importlib.reload(mod)

# --- SCENE CONFIGURATIONS ---
SCENE_CONFIGS = {
    "syringe": [
        {"name": "vertical",   "loc": (2, 0.2, 0.02),  "rot": (90, 0, 90), "rot_syring": False},
        {"name": "horizontal", "loc": (2, 0.02, 0.02), "rot": (90, 0, 90), "rot_syring": True}
    ],
    "pulsOX": [
        {"name": "close_up", "loc": (0, -2, 2), "rot": (45, 0, 0)},
        {"name": "normal",   "loc": (0, -5, 5), "rot": (45, 0, 0)},
        {"name": "far_away", "loc": (0, -7, 7), "rot": (45, 0, 0)}
    ],
    "monitor": [
        {"name": "center", "loc": (0, -5, 1),  "rot": (90, 0, 0)},
        {"name": "left",   "loc": (-5, -5, 1), "rot": (90, 0, -45)},
        {"name": "right",  "loc": (5, -5, 1),  "rot": (90, 0, 45)},
        {"name": "up",     "loc": (0, -5, 5),  "rot": (45, 0, 0)},
        {"name": "down",   "loc": (0, -5, -5), "rot": (135, 0, 0)}
    ],
    "Lifepak": [
        {"name": "center", "loc": (0, 1, 0),  "rot": (-90, 180, 0)},
        {"name": "left",   "loc": (1, 1, 0),  "rot": (-90, 180, -45)},
        {"name": "right",  "loc": (-1, 1, 0), "rot": (-90, 180, 45)},
        {"name": "up",     "loc": (0, 1, 1),  "rot": (-135, 180, 0)},
        {"name": "down",   "loc": (0, 1, -1), "rot": (-45, 180, 0)}
    ],
    "gauge": [
        {"name": "center", "loc": (0, -1.5, 25),   "rot": (0, 0, 0)},
        {"name": "left",   "loc": (-25, -1.5, 25), "rot": (0, -45, 0)},
        {"name": "right",  "loc": (25, -1.5, 25),  "rot": (0, 45, 0)},
        {"name": "up",     "loc": (0, 25, 25),     "rot": (-45, 0, 0)},
        {"name": "down",   "loc": (0, -25, 25),    "rot": (45, 0, 0)}
    ]
}

# --- HELPER FUNCTIONS ---
def render_standard_scene(module, scene_name, shake, use_bg, folder, views, asset_id='1'):
    print(f"_______________Rendering {scene_name} scene with shake type: {shake}")
    for view in views:
        cam_name = f"{folder}/{view['name']}"  # Guaranteed identical folder structure
        print(f"_______________Camera location: {view['loc']} Camera rotation: {view['rot']}")
        module.render_monitor_scene(shake, asset_id, view['loc'], view['rot'], use_video_bg=use_bg, cam_name=cam_name)

def render_syringe_scene(module, shake, use_bg, folder, views):
    print(f"_______________Rendering syringe scene with shake type: {shake}")
    for view in views:
        cam_name = f"{folder}/{view['name']}"  # Guaranteed identical folder structure
        print(f"_______________Rendering syringe scene {view['name']} with shake type: {shake}")
        module.render_monitor_scene(shake, '1', view['loc'], view['rot'], rot_syring=view['rot_syring'], use_video_bg=use_bg, cam_name=cam_name)

# --- MAIN RENDER LOOP ---
video_bgs = [True]

for use_video_bg in video_bgs:
    vid_folder = "/with_video_bg" if use_video_bg else "/without_video_bg"
    print(f"_______________Use video background:_______________ {use_video_bg}")
    
    # Configure shake types dynamically based on background
    shake_types = ["walking", "running", "sprinting", "crouching", "minimum_shake_walking", "skipping"]
    if not use_video_bg:
        shake_types.insert(0, "noShake")

    for shake in shake_types:
        # 1. Syringe
        render_syringe_scene(scene_syringe, shake, use_video_bg, vid_folder, SCENE_CONFIGS["syringe"])
        
        # 2. PulsOX
        render_standard_scene(scene_pulsOX, "pulsOX", shake, use_video_bg, vid_folder, SCENE_CONFIGS["pulsOX"])
        
        # 3. Monitor (Iterates through multiple asset IDs)
        for asset_id in ['1', '2']:
            print(f"Using monitor asset id: {asset_id}")
            render_standard_scene(scene_monitor, "monitor", shake, use_video_bg, vid_folder, SCENE_CONFIGS["monitor"], asset_id)
            
        # 4. Lifepak
        render_standard_scene(scene_Lifepak, "Lifepak", shake, use_video_bg, vid_folder, SCENE_CONFIGS["Lifepak"])
        
        # 5. Gauge
        render_standard_scene(scene_gauge, "gauge", shake, use_video_bg, vid_folder, SCENE_CONFIGS["gauge"])