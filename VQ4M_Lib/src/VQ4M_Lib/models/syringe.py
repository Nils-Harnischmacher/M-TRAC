import math
import bpy 
import sys, os
from VQ4M_Lib.models.model_helpers.helpers import mm, relink, round_corners, ensure_weighted_bevel, set_edge_weights, generate_cylinder_geometry, create_mesh_object, combine
from VQ4M_Lib.models.model_helpers.geometry_helpers import make_button_round, make_button_pill, make_quad_pyramid_y, set_active, make_quarter_donut_trapezoid
from VQ4M_Lib.models.model_helpers import gen_materials 
from VQ4M_Lib import general
from pathlib import Path
import random
PROJECT_ROOT = Path(__file__).resolve().parents[4]

def mm(val): return val *  0.01  # mm -> m

def make_tube(outer_radius=1.0, inner_radius=0.5, height=2.0, vertices=64, location=(0,0,0), name="Tube"):
    """
    Creates a hollow cylinder (tube) with its base at the given location.
    Extends upward along +Z.
    """
    
    # Outer cylinder
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, 
        radius=outer_radius, 
        depth=height, 
        location=location
    )
    outer_cyl = bpy.context.active_object
    
    # Move geometry so base is at Z = 0
    bpy.ops.object.editmode_toggle()
    bpy.ops.transform.translate(value=(0, 0, height / 2))
    bpy.ops.object.editmode_toggle()
    
    # Inner cylinder
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, 
        radius=inner_radius, 
        depth=height + 0.01, 
        location=location
    )
    inner_cyl = bpy.context.active_object
    
    # Move geometry for base alignment
    bpy.ops.object.editmode_toggle()
    bpy.ops.transform.translate(value=(0, 0, (height + 0.01) / 2))
    bpy.ops.object.editmode_toggle()
    
    # Boolean difference
    bpy.context.view_layer.objects.active = outer_cyl
    mod_bool = outer_cyl.modifiers.new(name="TubeCutout", type='BOOLEAN')
    mod_bool.operation = 'DIFFERENCE'
    mod_bool.object = inner_cyl
    bpy.ops.object.modifier_apply(modifier=mod_bool.name)
    
    # Cleanup
    bpy.data.objects.remove(inner_cyl, do_unlink=True)
    outer_cyl.name = name
    return outer_cyl


def make_cone(base_r: float,
              top_r: float,
              height: float,
              base_center=(0.0, 0.0, 0.0),
              vertices: int = 32,
              name: str = "Cone"):
    """
    Erstellt in Blender einen (ggf. abgeschnittenen) Kegel.
    
    Parameter
    ---------
    base_r : float
        Radius der Basis (unten).
    top_r : float
        Radius der Spitze/Deckfläche (oben). 0.0 => echter Kegel.
    height : float
        Höhe des Kegels entlang +Z.
    base_center : tuple[float,float,float]
        Weltkoordinaten der Basismitte (x, y, z).
    vertices : int
        Anzahl der Umfangssegmente (Detailgrad).
    name : str
        Objektname im Outliner.
    """

    # Grundlegende Prüfungen
    if height <= 0:
        raise ValueError("height muss > 0 sein.")
    if base_r < 0 or top_r < 0:
        raise ValueError("base_r und top_r müssen >= 0 sein.")
    if vertices < 3:
        raise ValueError("vertices muss >= 3 sein.")

    # Wir platzieren das Objekt so, dass die BASISMItte bei base_center liegt.
    # Blender erzeugt den Kegel mit Ursprung in der Mitte seiner Höhe.
    # Daher setzen wir die Objekt-Location auf base_center.z + height/2.
    loc_x, loc_y, base_z = base_center
    obj_location = (loc_x, loc_y, base_z + height * 0.5)

    # Kegel/Kegelstumpf erzeugen
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices,
        radius1=base_r,
        radius2=top_r,
        depth=height,
        enter_editmode=False,
        align='WORLD',
        location=obj_location,
        rotation=(0.0, 0.0, 0.0)
    )

    obj = bpy.context.active_object
    obj.name = name

    return obj

def make_cylinder(radius=1.0, height=2.0, vertices=64, location=(0,0,0), name="Cylinder"):
    """
    Creates a solid cylinder in Blender with its base at the given location.
    Extends upward along +Z.
    """
    
    # Create cylinder (centered)
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, 
        radius=radius, 
        depth=height, 
        location=location
    )
    cyl = bpy.context.active_object
    
    # Move geometry so base is at Z = 0 relative to object origin
    bpy.ops.object.editmode_toggle()
    bpy.ops.transform.translate(value=(0, 0, height / 2))
    bpy.ops.object.editmode_toggle()
    
    cyl.name = name
    return cyl

def round_over(obj,width=mm(30)):
    me = obj.data
    M  = obj.matrix_world
    mid_edges = []  # (midY, edge_index)
    for i, e in enumerate(me.edges):
        v1, v2 = e.vertices
        p1 = M @ me.vertices[v1].co
        p2 = M @ me.vertices[v2].co
        mid_world = M @ ((p1 + p2) * 0.5)
        mid_edges.append((mid_world, i))
    max_midZ= max(x.z for x, _ in mid_edges)
    min_midZ= min(x.z for x, _ in mid_edges)

    edges_indices = [i for y, i in mid_edges if (abs(y.z - min_midZ) < 1e-8 or abs(y.z - max_midZ) < 1e-8)]
    ensure_weighted_bevel(obj, width, segments=200, profile=0.5, name="corner_roundover",use_clamp_overlap=False)
    set_edge_weights(obj,edges_indices)  
    return edges_indices


def make_plunger(radius,hight,thumb_r,location):
    x,y,z=location
    bpy.ops.mesh.primitive_cube_add(size=1,location=(x,y,z+hight/2))
    plungerX_1 = bpy.context.active_object
    plungerX_1.name = "plungerX_1"
    plungerX_1.scale = (radius, mm(0.5), hight)
    bpy.ops.mesh.primitive_cube_add(size=1,location=(x,y,z+hight/2))
    plunger = bpy.context.active_object
    plunger.name = "plunger"
    plunger.scale = (mm(0.5),radius, hight)
    combine(plungerX_1,plunger)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    thumb=make_cylinder(thumb_r,mm(2),location=(x,y,z+hight-mm(1)))
    round_over(thumb,mm(1))
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    combine(plunger,thumb)
    plug = make_cylinder(radius,mm(5),location=(x,y,z))
    round_over(plug,mm(1))


    return thumb,plug,

def make_med_chamber(outer_r,inner_r,tip_r,height,tip_hight,location):
    x,y,z = location
    flansch_hight=mm(1)
    tube=make_tube(outer_r, inner_r, height, vertices=80, location=(x,y,z+tip_hight+flansch_hight), name="medication_chamber")
    flansch_base= make_cone(outer_r,tip_r,flansch_hight,vertices=80,base_center=(x,y,z+tip_hight))
    flansch_base.rotation_euler.x=math.radians(180)
    flansch=make_tube(tip_r, tip_r-mm(0.5), tip_hight, vertices=80, location=(x,y,z), name="flansch")
    combine(flansch,flansch_base)
    combine(flansch_base,tube)
    return tube

def make_Luer_slip(outer_r_base,outer_r_tip,hight,location):
    x,y,z = location
    base_ring=make_tube(outer_r_base+mm(1), outer_r_base, mm(0.5), vertices=80, location=(x,y,z))
    flansch_base= make_cone(outer_r_base,outer_r_tip,hight/2,vertices=80,base_center=(x,y,z-hight/2))
    flansch_base.rotation_euler.x=math.radians(180)
    reduction = make_cone(outer_r_tip,outer_r_tip/2,hight/4,vertices=80,base_center=(x,y,z-hight/2-hight/4))
    reduction.rotation_euler.x=math.radians(180)
    tube=make_tube(outer_r_tip/2, outer_r_tip/3, hight/4, vertices=80, location=(x,y,z-hight/2-hight/4-hight/4), name="medication_chamber")
    bpy.ops.mesh.primitive_cube_add(size=1,location=(x,y,z-hight/2-hight/4))
    X_1 = bpy.context.active_object
    X_1.name = "X_1"
    X_1.scale = (outer_r_tip*2, mm(0.2), hight/2)
    bpy.ops.mesh.primitive_cube_add(size=1,location=(x,y,z-hight/2-hight/4))
    X_2 = bpy.context.active_object
    X_2.name = "X_2"
    X_2.scale = ( mm(0.2), outer_r_tip*2,hight/2)
    combine(base_ring,flansch_base)
    combine(flansch_base,reduction)
    combine(reduction,tube)
    combine(X_1,X_2)
    combine(X_2,tube)
    return tube



def make_grip(inner_r, width,thickness,location):
    x,y,z = location
    r=inner_r+mm(1)
    tube=make_tube(r, inner_r, thickness, vertices=80, location=(x,y,z))
    width= width+inner_r
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    left_wing=make_quad_pyramid_y(
    x, y+width/2, z+thickness/2,
    r*2,    # Ausdehnung in X an der Basis (Y-)
    thickness,    # Ausdehnung in Z an der Basis (Y-)
    width,      # Länge entlang Y (Basis -> Spitze/Top)
    inner_r,     # Ausdehnung in X am Top (Y+). 0 => echte Spitze
    thickness/2,     # Ausdehnung in Z am Top (Y+). 0 => echte Spitze
    name="left",
    inverted=False)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    right_wing=make_quad_pyramid_y(
    x, y-width/2, z+thickness/2,
    r*2,    # Ausdehnung in X an der Basis (Y-)
    thickness,    # Ausdehnung in Z an der Basis (Y-)
    width,      # Länge entlang Y (Basis -> Spitze/Top)
    inner_r,     # Ausdehnung in X am Top (Y+). 0 => echte Spitze
    thickness/2,     # Ausdehnung in Z am Top (Y+). 0 => echte Spitze
    name="right",
    inverted=True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    combine(left_wing,tube)
    combine(right_wing,tube)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    cutter=make_cylinder(inner_r, thickness, vertices=80, location=(x,y,z))
    # Boolean an upper hinzufügen
    mod1 = tube.modifiers.new(name="cutter_prep_screen", type='BOOLEAN')
    mod1.operation = 'DIFFERENCE'
    mod1.solver = 'EXACT'
    mod1.object = cutter
    bpy.context.view_layer.objects.active = tube
    tube.select_set(True)
    cutter.select_set(False)
    bpy.ops.object.modifier_apply(modifier=mod1.name)
    bpy.data.objects.remove(cutter, do_unlink=True)

    return tube




    



def make_syringe(asset_path="",rot_syring=False):
    needle=make_tube(mm(0.3), mm(0.16), mm(25), vertices=80, location=(0,0,-mm(35)), name="needle")
    reduction=make_cone(mm(3.5)/2,mm(0.3),mm(1),vertices=80,base_center=(0,0,-mm(11)))
    reduction.rotation_euler.x=math.radians(180)
    luer=make_Luer_slip(mm(4),mm(3.5),mm(10),(0,0,0))
    chamber=make_med_chamber(mm(7),mm(6),mm(4),mm(60),mm(3),(0,0,0))
    grip=make_grip(mm(7),mm(8),mm(2),(0,0,mm(61)))

    plunger,plug=make_plunger(mm(6),mm(70),mm(8),(0,0,mm(5)))
    if rot_syring:
        combine(needle,reduction)
        combine(reduction,luer)
        combine(luer,chamber)
        combine(chamber,grip)
        combine(grip,plug)
        combine(plug,plunger)
        plunger.rotation_euler=(math.radians(90),0,0)
        label_loc=(0,-mm(10),0)
    else:
        label_loc=(0,0,mm(10))


    label=make_tube(outer_radius=mm(7.01), inner_radius=mm(7), height=mm(50.0), vertices=100, location=label_loc, name="label")
    if asset_path == "":
        asset_folder= str(PROJECT_ROOT)+"/assets/content_syringe/"
        paths = general.list_files_by_extension(asset_folder,".png")
        img_path = paths[random.randint(0,len(paths)-1)]
    else:
        img_path = asset_path


    # # Assume you just made a cylinder with make_cylinder(...), select it (or pass obj=...):
    gen_materials.wrap_image_on_cylinder(
        obj=label,
        image_path=img_path,   # relative to .blend or absolute path
        rotation_deg=0,                      # no rotation
        offset_uv=(0.0, 0.0),                # no offset
        force_cylindrical_unwrap=False      # set True if texture seams look off
        )
    
    if rot_syring:
        label.rotation_euler=(math.radians(90),0,0) 
    



    return label