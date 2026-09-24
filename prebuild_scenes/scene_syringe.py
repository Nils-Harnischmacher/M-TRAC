
import bpy
import importlib
from pathlib import Path
# Modellib 
from  VQ4M_Lib.models import syringe as syr
syr= importlib.reload(syr)
# Pipelinelib 
from VQ4M_Lib import shake as shakeLib
shakelib = importlib.reload(shakeLib)
from VQ4M_Lib import lighting as lightLib 
lightlib = importlib.reload(lightLib)
from VQ4M_Lib import rendering as renderLib 
renderLib = importlib.reload(renderLib)
import prebuild_scenes.setup_scene as setup_s



PROJECT_ROOT = Path(__file__).resolve().parents[0].parent

def render_monitor_scene(shake_type, asset_id, cam_location, cam_rotation,cam_name="" ,use_video_bg=False,rot_syring=False):
    # === set up ===
    asset_path,folder,shake_settings,camera,scene = setup_s.setup(shake_type, asset_id, cam_location, cam_rotation,"syringe",cam_name,use_video_bg)
    # === moddel loading ===
    label = syr.make_syringe(asset_path+'/img.png',rot_syring)
    # === Ligthing ===
    lightlib.upsert_light(name="sun", type='SUN', location=(40, 20, 1),energy=5.0,target_obj=label)
    # === Animation ===
    if shake_type != "noShake":
        shaky_cam=shakelib.add_camera_shake(shake_type, camera=camera, csv_path=str(PROJECT_ROOT)+"/dataset/csvs/"+shake_type+".csv",settings=shake_settings)
    else:
        shaky_cam=camera
    bpy.context.scene.camera = shaky_cam
    # === boundingboxs setup ===
    ground_truth = setup_s.setup_bb(asset_path,label,folder,scene,shaky_cam)
    # === rendering ===
    renderLib.render()
