import math
import bpy 
from VQ4M_Lib.models.model_helpers import gen_materials 
from VQ4M_Lib import general

from pathlib import Path
import random
PROJECT_ROOT = Path(__file__).resolve().parents[4]


def create_rounded_cube(
    size=2.0,          # edge length of the cube
    radius=0.2,        # bevel "rounding" amount
    segments=4,        # how smooth the rounding is
    scale=(1, 1, 1),  # scale of the cube
    only_corners=False,# True -> round only the 8 corners; False -> round edges too
    location=(0,0,0)
):
    # Safety: clamp radius so it can't exceed half the cube size
    max_radius = max(0.0, (size * 0.5) - 1e-5)
    radius = min(radius, max_radius)

    # Make a clean active object
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.mesh.primitive_cube_add(size=size, location=location)
    obj = bpy.context.active_object
    obj.name = "RoundedCube"
    obj.scale = scale
    # Bevel modifier for rounded edges/corners
    bev = obj.modifiers.new(name="RoundedCorners", type='BEVEL')
    bev.width = radius
    bev.segments = segments
    bev.profile = 0.7                  # 0.5=perfect circular; >0.5 a bit squarer
    bev.limit_method = 'NONE'          # affect all edges/verts
    bev.affect = 'VERTICES' if only_corners else 'EDGES'
    bev.harden_normals = True
    #bev.clamp_overlap = True

    # Nice shading
    bpy.ops.object.shade_smooth()
    #obj.data.use_auto_smooth = True

    # Apply the modifier (optional—leave unapplied if you want it editable)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=bev.name)

    return obj



def make_cylinder(radius=1.0, height=2.0, vertices=64, location=(0,0,0),rotation=(0,0,0), name="Cylinder"):
    """
    Creates a solid cylinder in Blender with its base at the given location.
    Extends upward along +Z.
    """
    
    # Create cylinder (centered)
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, 
        radius=radius, 
        depth=height, 
        location=location,
        rotation = rotation 
    )
    cyl = bpy.context.active_object
    cyl.name = name
    return cyl



def creat_pat_monitor(asset_path=""):
    back=create_rounded_cube(size=5.0, radius=0.25, segments=5, scale=(0.99,0.3,0.7),only_corners=False, location=(0,1,2))
    screen=create_rounded_cube(size=5.0, radius=0.25, segments=5, scale=(1,0.1,0.8),only_corners=False, location=(0,0.2,2))
    patMonMat=gen_materials.create_and_apply_material(screen,name="PatMonWhite",base_color="#fdf9e5",metallic=0.0,roughness=0.8)
    back.data.materials.append(patMonMat)
    bpy.ops.mesh.primitive_plane_add(size=5, location=(0, -0.06, 2), rotation=(math.radians(90), 0, 0))
    content = bpy.context.active_object
    content.scale = (0.8,0.6,1)
    content.name = "MonitorContent"  
    if asset_path == "":
        asset_folder= str(PROJECT_ROOT)+"/assets/content_patient_monitor/"
        paths = general.list_files_by_extension(asset_folder,".png")
        img_path = paths[random.randint(0,len(paths)-1)]
    else:
        img_path = asset_path
       
    gen_materials.wrap_image_on_cylinder(
        obj=content,
        image_path= img_path,
        rotation_deg=0,                      # no rotation
        offset_uv=(0.0, 0.0),                # no offset
        force_cylindrical_unwrap=False,      # set True if texture seams look off
        material_name="patiet_mon_selfmade"
    )

    sw=make_cylinder(radius=.2, height=.2,vertices=64,location=(2.2,-0.05,0.25), rotation=(math.radians(90), 0, 0),name="scroolwheel")
    swMat=gen_materials.create_and_apply_material(sw,name="scrollwheelMat",base_color="#5f5f5f",metallic=0.0,roughness=0.8)

    pb=make_cylinder(radius=.15, height=.1,vertices=64,location=(-2.1,-0.05,0.25), rotation=(math.radians(90), 0, 0),name="Powerbutton")
    led1=make_cylinder(radius=.05, height=.1,vertices=64,location=(-1.8,-0.005,0.3), rotation=(math.radians(90), 0, 0),name="LED1")
    led2=make_cylinder(radius=.05, height=.1,vertices=64,location=(-1.8,-0.005,0.15), rotation=(math.radians(90), 0, 0),name="LED2")
    powerButtonMat=gen_materials.create_and_apply_material(pb,name="Powerbutton",base_color="#FF5500FF",metallic=0.0,roughness=0.0)
    Led1Mat=gen_materials.create_and_apply_material(led1,name="led1",base_color="#baff6a",metallic=0.0,roughness=1,emission_color="#27FF00FF",emission_strength=2.5)
    Led2Mat=gen_materials.create_and_apply_material(led2,name="led2",base_color="#fdff6a",metallic=0.0,roughness=1,emission_color="#FFFD00FF",emission_strength=2.5)

    b1=create_rounded_cube(size=.15, radius=0.25, segments=5 ,only_corners=False, location=(0.5,-0.05,0.25))
    b2=create_rounded_cube(size=.15, radius=0.25, segments=5 ,only_corners=False, location=(1,-0.05,0.25))
    b3=create_rounded_cube(size=.15, radius=0.25, segments=5 ,only_corners=False, location=(1.5,-0.05,0.25))

    b4=create_rounded_cube(size=.15, radius=0.25, segments=5 ,only_corners=False, location=(0.75,-0.05,0.25))
    b5=create_rounded_cube(size=.15, radius=0.25, segments=5 ,only_corners=False, location=(1.25,-0.05,0.25))
    b6=create_rounded_cube(size=.15, radius=0.25, segments=5 ,only_corners=False, location=(1.75,-0.05,0.25))
    buttonMat=gen_materials.create_and_apply_material(b1,name="buttonMat",base_color="#6aa6ff",metallic=0.0,roughness=1)
    b2.data.materials.append(buttonMat)
    b3.data.materials.append(buttonMat)
    b4.data.materials.append(buttonMat)
    b5.data.materials.append(buttonMat)
    b6.data.materials.append(buttonMat)

    
    
    
    
    
    
    return content