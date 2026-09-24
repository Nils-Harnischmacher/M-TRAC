import math
import bpy
from pathlib import Path
from mathutils import Vector
from VQ4M_Lib.models.model_helpers import gen_materials 

def load_obj(obj_path,
    target_location = (0.83,-0.0225,-0.47),   
    target_rotation = (math.radians(142.487),math.radians(-3.95123),math.radians(-98.7319)),
    uniform_scale = 0.04,                
    mat=gen_materials.hand_mat(),
    ):
    fp = Path(obj_path)
    if not fp.exists():
        raise FileNotFoundError(f"OBJ nicht gefunden: {fp}")

    res = bpy.ops.wm.obj_import(filepath=str(fp), forward_axis='NEGATIVE_Z', up_axis='Y')
    hand = bpy.data.objects[list(bpy.data.objects.keys())[0]]

    hand.scale = (uniform_scale, uniform_scale, uniform_scale)
    hand.location = Vector(target_location)
    hand.rotation_euler = target_rotation
    gen_materials.assign_single_material(hand,mat)