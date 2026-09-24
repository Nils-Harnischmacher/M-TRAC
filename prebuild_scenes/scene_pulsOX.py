
import bpy
import math
import importlib
from pathlib import Path
# Modellib 
from  VQ4M_Lib.models import pulsox as pox
pox= importlib.reload(pox)
from VQ4M_Lib import load_obj as obj
obj= importlib.reload(obj)
from VQ4M_Lib.models.model_helpers import gen_materials 
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
    asset_path,folder,shake_settings,camera,scene = setup_s.setup(shake_type, asset_id, cam_location, cam_rotation,"puls_ox",cam_name,use_video_bg)
    # === moddel loading ===
    obj.load_obj(
        obj_path = str(PROJECT_ROOT)+"/assets/objs/Hand.OBJ",
        target_location = (8.3,-0.225,-4.7),   
        target_rotation = (math.radians(142.487),math.radians(-3.95123),math.radians(-98.7319)),
        uniform_scale = 0.4,                 
        mat=gen_materials.hand_mat()
    )
    screen=pox.create_pulsOX(100, 60, 45,50,35,(0,0,0),asset_path+'/img.png')
    # === Ligthing ===
    lightlib.upsert_light(name="sun", type='SUN', location=(0,-2,10),energy=2.0,target_obj=screen)
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

