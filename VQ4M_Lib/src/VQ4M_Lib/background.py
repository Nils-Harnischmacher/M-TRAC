import bpy
import math
import os
from VQ4M_Lib import general
from VQ4M_Lib.models.model_helpers import gen_materials
from pathlib import Path
import random
PROJECT_ROOT = Path(__file__).resolve().parents[5]


def setup_equirect_skybox(
    image_path: str,
    strength: float = 1.0,
    rotation_deg: float = 0.0,
    world_name: str = "SkyboxWorld",
):
    """
    Create/replace a World that uses an equirectangular image as the skybox.
    - image_path: absolute or relative path to your image (.hdr/.exr/.jpg/.png)
    - strength: background intensity
    - rotation_deg: yaw rotation around vertical axis (Z) in degrees
    - world_name: name for the World datablock
    """
    if not os.path.isabs(image_path):
        image_path = bpy.path.abspath(image_path)

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    img = bpy.data.images.load(image_path, check_existing=True)

    ext = os.path.splitext(image_path)[1].lower()
    if ext in {".jpg", ".jpeg", ".png"}:
        try:
            img.colorspace_settings.name = "sRGB"
        except Exception:
            pass
    elif ext in {".hdr", ".exr"}:
        try:
            img.colorspace_settings.name = "Linear"
        except Exception:
            pass

    world = bpy.data.worlds.get(world_name) or bpy.data.worlds.new(world_name)
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()

    n_texcoord = nt.nodes.new("ShaderNodeTexCoord")
    n_map     = nt.nodes.new("ShaderNodeMapping")
    n_env     = nt.nodes.new("ShaderNodeTexEnvironment")
    n_bg      = nt.nodes.new("ShaderNodeBackground")
    n_out     = nt.nodes.new("ShaderNodeOutputWorld")

    n_texcoord.location = (-900, 0)
    n_map.location      = (-700, 0)
    n_env.location      = (-480, 0)
    n_bg.location       = (-250, 0)
    n_out.location      = (0, 0)

    n_env.image = img
    n_env.projection = 'EQUIRECTANGULAR'  # critical!

    n_bg.inputs["Strength"].default_value = strength

    rot = list(n_map.inputs["Rotation"].default_value)
    rot[2] = math.radians(rotation_deg)
    n_map.inputs["Rotation"].default_value = rot

    nt.links.new(n_texcoord.outputs["Generated"], n_map.inputs["Vector"])
    nt.links.new(n_map.outputs["Vector"], n_env.inputs["Vector"])
    nt.links.new(n_env.outputs["Color"], n_bg.inputs["Color"])
    nt.links.new(n_bg.outputs["Background"], n_out.inputs["Surface"])

    bpy.context.scene.world = world


    return world

def create_background(size=100, location=(0, 40, 0),rotation=(math.radians(90),0,0),asset_path=""):
    if asset_path == "":
        asset_folder= str(PROJECT_ROOT)+"/assets/content_background/"
        paths = general.list_files_by_extension(asset_folder,".png")
        img_path = paths[random.randint(0,len(paths)-1)]
    else:
        img_path = asset_path
    bpy.ops.mesh.primitive_plane_add(size=size, location=location, rotation=rotation)
    background = bpy.context.active_object
    background.name = "background"
    
    gen_materials.wrap_image_on_cylinder(
        obj=background,
        image_path= img_path,
        rotation_deg=0,                      # no rotation
        offset_uv=(0.0, 0.0),                # no offset
        force_cylindrical_unwrap=False,      # set True if texture seams look off
        material_name="background_test"
    )


def create_background_test(size=100, location=(0, 40, 0),rotation=(0 ,0,0),asset_path="", parrent=None):
    bpy.ops.mesh.primitive_plane_add(size=1, location=location, rotation=rotation)
    background = bpy.context.active_object
    background.scale=(4*size,3*size,1)
    background.name = "background"
    background.parent=parrent    
    vid=gen_materials.wrap_image_on_cylinder(
        obj=background,
        image_path= asset_path,
        rotation_deg=0,                      # no rotation
        offset_uv=(0.0, 0.0),                # no offset
        force_cylindrical_unwrap=False,      # set True if texture seams look off
        material_name="background_test"
    )
    vid.node_tree.nodes["Image Texture"].image_user.frame_start=1
    vid.node_tree.nodes["Image Texture"].image_user.frame_duration=1000
    vid.node_tree.nodes["Image Texture"].image_user.use_auto_refresh=True
