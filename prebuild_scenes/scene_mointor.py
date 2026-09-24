import bpy
import importlib
from pathlib import Path
import random
# Modellib 
from  VQ4M_Lib.models import monitor as mon
mon= importlib.reload(mon)
# Pipelinelib 
from VQ4M_Lib import shake as shakeLib
shakelib = importlib.reload(shakeLib)
from VQ4M_Lib import lighting as lightLib 
lightlib = importlib.reload(lightLib)
from VQ4M_Lib import rendering as renderLib 
renderLib = importlib.reload(renderLib)
# Setup Script
import prebuild_scenes.setup_scene as setup_s



PROJECT_ROOT = Path(__file__).resolve().parents[0].parent



def render_monitor_scene(shake_type, asset_id, cam_location, cam_rotation,cam_name="",use_video_bg=False):
    # === set up ===
    random_int = random.randint(-1 , 1)
    cam_location = (cam_location[0]+random_int,cam_location[1],cam_location[2]) 
    asset_path,folder,shake_settings,camera,scene = setup_s.setup(shake_type, asset_id, cam_location, cam_rotation,"monitor",cam_name,use_video_bg)
    # === moddel loading ===
    screen =  mon.create_monitor_img(asset_path+'/img.png')
    # === Ligthing ===
    lightlib.upsert_light(name="sun", type='SUN', location=(0, -10, 10), energy=2.0, target_obj=screen)
    # === Animation ===
    if shake_type != "noShake":
        shaky_cam=shakelib.add_camera_shake(shake_type, camera=camera, csv_path=str(PROJECT_ROOT)+"/dataset/csvs/"+shake_type+".csv",settings=shake_settings)
    else:
        shaky_cam=camera
    bpy.context.scene.camera = shaky_cam
    # === boundingboxs setup ===
    ground_truth = setup_s.setup_bb(asset_path,screen,folder,scene,shaky_cam)
    # === rendering ===
    renderLib.render()

