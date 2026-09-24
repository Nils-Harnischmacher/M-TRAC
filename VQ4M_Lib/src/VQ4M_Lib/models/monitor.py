import math
import bpy 
import sys, os
from VQ4M_Lib.models.model_helpers import gen_materials 

from VQ4M_Lib import general
from pathlib import Path
import random
PROJECT_ROOT = Path(__file__).resolve().parents[1]#[4]
def create_text(text,
                location=(0, -0.12, 1.4),
                rotation=(math.radians(90), 0, 0),
                scale=(0.3, 0.3, 0.3),
                name="ScreenText"):

    # Create FONT curve datablock and object
    font_curve = bpy.data.curves.new(name=name, type='FONT')
    font_curve.body = text

    text_obj = bpy.data.objects.new(name, font_curve)
    text_obj.location = location
    text_obj.rotation_euler = rotation
    text_obj.scale = scale

    # Link to current collection
    bpy.context.collection.objects.link(text_obj)
    gen_materials.assign_single_material(text_obj,gen_materials.monitor_body((0,0,0,1)))


    bpy.context.view_layer.objects.active = text_obj
    text_obj.select_set(True)
    return text_obj

def create_monitor():
    #gen.clean_scene()
    # --- Create screen (a flat cube) ---
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 1.2))
    screen = bpy.context.active_object
    screen.name = "MonitorScreen"
    screen.scale = (2.075, 0.1, 1.2)
    bevMon = screen.modifiers.new(name="RoundedCorners", type='BEVEL')
    bevMon.width = 0.02
    bevMon.segments = 64
    bevMon.profile = 0.7                  # 0.5=perfect circular; >0.5 a bit squarer
    bevMon.limit_method = 'NONE'          # affect all edges/verts
    bevMon.affect = 'EDGES'
    bevMon.harden_normals = True
    # --- Create stand (a small cylinder) ---
    bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=1, location=(0, 0.1, 0.2))
    stand = bpy.context.active_object
    stand.name = "MonitorStand"

    # --- Create base (a flattened cube) ---
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -0.1, -0.3))
    base = bpy.context.active_object
    base.name = "MonitorBase"
    base.scale = (1.2, 0.8, 0.05)
    bevbase = base.modifiers.new(name="RoundedCorners", type='BEVEL')
    bevbase.width = 0.06
    bevbase.segments = 64
    bevbase.profile = 0.7                  # 0.5=perfect circular; >0.5 a bit squarer
    bevbase.limit_method = 'NONE'          # affect all edges/verts
    bevbase.affect = 'EDGES'
    bevbase.harden_normals = True


    gen_materials.assign_single_material(screen,gen_materials.monitor_body((0,0,0,1)))
    gen_materials.assign_single_material(stand,gen_materials.monitor_body((0.45,0.45,0.45,1),metallic=0.691,roughness=0.314,name='mon_stand'))
    gen_materials.assign_single_material(base,gen_materials.monitor_body((0.45,0.45,0.45,1),metallic=0.691,roughness=0.314,name='mon_base'))



    return screen, stand, base


def create_monitor_single_text(text):
    screen,stand,base = create_monitor()
    create_text(text)
    return screen, stand, base


def create_monitor_multi_text(text1,text2,text3):
    screen,stand,base = create_monitor()
    create_text(text1)
    create_text(text2,location=(-1.8,-0.11,2))
    create_text(text3,location=(-1.5,-0.11,0.5))
    return screen, stand, base


def create_monitor_img(asset_path = ""):
    screen,stand,base = create_monitor()
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, -0.101, 1.2), rotation=(math.radians(90), 0, 0))
    content = bpy.context.active_object
    content.scale = (2, 1.125, 1)
    content.name = "MonitorContent"   
    gen_materials.add_image(content,gen_materials.mon_screen_img(asset_path))
    return content