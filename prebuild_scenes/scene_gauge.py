import bpy
import importlib
from pathlib import Path
# Modellib
from  VQ4M_Lib.models import gauge as gau
gau= importlib.reload(gau)
# Pipelinelib 
from VQ4M_Lib import shake as shakeLib
shakelib = importlib.reload(shakeLib)
from VQ4M_Lib import lighting as lightLib 
lightlib = importlib.reload(lightLib)
from VQ4M_Lib import rendering as renderLib 
renderLib = importlib.reload(renderLib)
from VQ4M_Lib import boundingbox as bb
bb = importlib.reload(bb)
# Setup Script
import prebuild_scenes.setup_scene as setup_s


PROJECT_ROOT = Path(__file__).resolve().parents[0].parent


def render_monitor_scene(shake_type, asset_id, cam_location, cam_rotation,cam_name="",use_video_bg=False):
    # === set up ===
    asset_path,folder,shake_settings,camera,scene = setup_s.setup(shake_type, asset_id, cam_location, cam_rotation,"gauge",cam_name,use_video_bg)
    # === moddel loading ===
    gau_parent,targets,parents=gau.create_full_gauge(
        anim=False,
        start_val=2,
        end_val=7,
        min_val=1,
        max_val=10,
        start_angle=0,
        sweep_angle=360,
        location=(0,0,0.1),
        rotation = (0,0,0)
    )
    # === Ligthing ===
    lightlib.upsert_light(name="sun", type='SUN', location=(0,0  , 10), energy=2.0, target_obj=gau_parent)
    # === Animation ===
    if shake_type != "noShake":
        shaky_cam=shakelib.add_camera_shake(shake_type, camera=camera, csv_path=str(PROJECT_ROOT)+"/dataset/csvs/"+shake_type+".csv",settings=shake_settings)
    else:
        shaky_cam=camera
    bpy.context.scene.camera = shaky_cam
    # === boundingboxs setup ===
    ground_truth = []
    for idx, parent in enumerate(parents):
        bb.project_object_space_box(
            scene,
            shaky_cam,
            gau_parent,
            box_name=parent.name,
            box_width=0.8,
            box_height=0.8,
            use_empty_frame=True,
            frame_empty=targets[idx],
            out_base_dir=bpy.path.abspath(folder)  # defaults to your blend file dir
        )
    ground_truth= " ".join(ground_truth)
    # === rendering ===
    renderLib.render()
