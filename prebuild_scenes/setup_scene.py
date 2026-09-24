import bpy
import importlib
from pathlib import Path
import sys, os, csv

# Modellib
from  VQ4M_Lib.models import gauge as gau
gau= importlib.reload(gau)

#Pipelinelib
from VQ4M_Lib import camera as camLib
camlib = importlib.reload(camLib)
from VQ4M_Lib import shake as shakeLib
shakelib = importlib.reload(shakeLib)
from VQ4M_Lib import lighting as lightLib
lightlib = importlib.reload(lightLib)
from VQ4M_Lib import rendering as renderLib
renderLib = importlib.reload(renderLib)
from VQ4M_Lib import general as genLib
genlib = importlib.reload(genLib)
from VQ4M_Lib import boundingbox as bb
bb = importlib.reload(bb)
from VQ4M_Lib import background as bg
bg = importlib.reload(bg)
PROJECT_ROOT = Path(__file__).resolve().parents[0].parent

def setup(shake_type, asset_id, cam_location, cam_rotation,object_name,cam_name="",use_video_bg=False):
    cfg = genlib.load_profile(base_dir=str(PROJECT_ROOT)+"/dataset/csvs/configs")   
    scene_length = cfg["scene_length"]        
    shake_settings = cfg["shake_settings"]   
    # === path setup ===
    folder = str(PROJECT_ROOT)+"/dataset/videos/"+str(object_name)+"/"+shake_type+"/img"+asset_id+cam_name
    file_name = f"{object_name}_{shake_type}_img{asset_id}"
    asset_path = str(PROJECT_ROOT)+"/assets/content_"+str(object_name)+"/img"+asset_id
    # === scene setup ===
    scene = bpy.context.scene
    scene.render.fps = 30  
    genLib.clean_scene()
    # === Camera setup ===
    camera,et = camlib.create_camera_from_calibration_json(
        json_path=str(PROJECT_ROOT)+"/dataset/calibration.json",
        name="RealWear_N500",
        location=cam_location,
        rotation_euler_deg=cam_rotation,
        sensor_width_mm=None,          
        set_scene_resolution=True,
        apply_principal_point_shift=True,
        add_simple_lens_node=False)
    
    if use_video_bg:
        bg.create_background_test(size=20, location=(0,0,-40),asset_path=str(PROJECT_ROOT)+f"/assets/content_backgrounds/background_videos/{shake_type}.mp4", parrent=camera)
    else:
        bg.setup_equirect_skybox(str(PROJECT_ROOT)+"/assets/content_backgrounds/thumbnail.jpg")
    # === render setup ===
    renderLib.set_render_settings(f"{folder}/{file_name}.mp4",
                                frame_start = 1,
                                frame_end   = scene_length,
                                fps=30,
                                exposure_time=et)
    
    return asset_path,folder,shake_settings,camera,scene


def setup_bb(asset_path,parent,folder,scene,shaky_cam,show_bb=False):
    ground_truth = []
    with open(asset_path+'/gt.csv', mode='r', newline='') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            ground_truth.append(row["gt"])
            bpy.ops.object.empty_add(type='PLAIN_AXES', location=(float(row["center_x"]),float(row["center_y"]),float(row["center_z"])))
            target = bpy.context.active_object
            target.name = row["name"]
            target.parent = parent 
            if show_bb:
                bb.show_bb(target,width=float(row["width"]), height=float(row["hight"]),offset=(0,0,-0.001))

            bb.project_object_space_box(
                scene,
                shaky_cam,
                parent,
                box_name=row["name"],  
                box_width=float(row["width"]),
                box_height=float(row["hight"]),
                use_empty_frame=True,
                frame_empty=target,
                out_base_dir=bpy.path.abspath(folder)  # defaults to your blend file dir
            )
    ground_truth= " ".join(ground_truth)
    return ground_truth