import bpy
from math import radians
from VQ4M_Lib.models.model_helpers.helpers import mm, relink, round_corners, generate_cylinder_geometry, create_mesh_object, combine
from VQ4M_Lib.models.model_helpers.geometry_helpers import make_button_round, make_button_pill, make_quad_pyramid_y, set_active, make_quarter_donut_trapezoid
from VQ4M_Lib.models.model_helpers import gen_materials 


def make_main_body(bw,bd,bh, corner_r,mat_body, col):
    bpy.ops.mesh.primitive_cube_add(size=1)
    body = bpy.context.active_object
    body.name = "MainBody"
    body.scale = (bw, bd, bh)
    body.data.materials.append(mat_body)
    relink(body, col)
    round_corners(body, width=corner_r, segments=20, profile=0.5)
    gen_materials.assign_single_material(body,gen_materials.LP_body())
    return body

def make_screen_bezel(width, height,thicknes,body_d ,corner_r,mat_bezel , col):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, body_d/2, 0))
    bezel = bpy.context.active_object
    bezel.name = "Bezel"
    bezel.scale = (width, thicknes, height)
    bezel.data.materials.append(mat_bezel)
    relink(bezel, col)
    round_corners(bezel, width=corner_r, segments=20, profile=0.5)
    gen_materials.assign_single_material(bezel,gen_materials.pulsOx_screen_cover())

    return bezel

def make_screen(width,height,margin,glass_inset,bezel_width,bezel_thick,bezel_obj, mat_glass, col,asset_path=""):
    screen_loc_y=bezel_width/2-width/2-margin
    bpy.ops.mesh.primitive_cube_add(size=1, location=(screen_loc_y, 0, 0))
    screen_cut = bpy.context.active_object
    screen_cut.scale = (width, bezel_thick, height)
    screen_cut.location.y = bezel_obj.location.y 
  
    bool_mod = bezel_obj.modifiers.get("ScreenAperture") or bezel_obj.modifiers.new("ScreenAperture", 'BOOLEAN')
    bool_mod.operation = 'DIFFERENCE'
    bool_mod.solver = 'EXACT'
    bool_mod.object = screen_cut
    bpy.context.view_layer.objects.active = bezel_obj
    bpy.ops.object.modifier_apply(modifier=bool_mod.name)
    bpy.data.objects.remove(screen_cut, do_unlink=True)
    # make glass
    bpy.ops.mesh.primitive_plane_add(size=1)
    glass = bpy.context.active_object
    glass.name = "ScreenGlass"
    glass.scale = (width - mm(1.5), height - mm(1.5), 1)
    glass.location = (screen_loc_y, bezel_obj.location.y + mm(1.2), 0)
    glass.rotation_euler = (radians(90),0, 0)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value": (0, -glass_inset, 0)})
    bpy.ops.object.mode_set(mode='OBJECT')
    glass.data.materials.append(mat_glass)
    relink(glass, col)
    gen_materials.add_image(glass,gen_materials.LP_screen_img(asset_path),None,-90)

    return glass

def make_handle(bh,dims, col):
    span = mm(dims["handle_span"])
    height = mm(dims["handle_height"])
    thick = mm(dims["handle_thick"])
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, bh/2 + mm(5)))
    handel = bpy.context.active_object
    handel.name = "Handel"
    handel.scale = (span, thick, height)
    round_corners(handel, width=mm(20), segments=20, profile=0.7)
    #handel.data.materials.append(mat_handel)
    relink(handel, col)

    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, bh/2 + mm(5)))
    handel_cut = bpy.context.active_object
    handel_cut.name = "handel_cut"
    handel_cut.scale = (span - mm(20), thick+mm(2), height- mm(20))

    bool_mod = handel.modifiers.new("HandleCut", 'BOOLEAN')
    bool_mod.operation = 'DIFFERENCE'
    bool_mod.solver    = 'EXACT'
    bool_mod.object    = handel_cut
    bpy.context.view_layer.objects.active = handel
    bpy.ops.object.modifier_apply(modifier=bool_mod.name)
    bpy.data.objects.remove(handel_cut, do_unlink=True)
    radius=thick/2
    handle_round_1 = create_mesh_object("tube1",*generate_cylinder_geometry(radius,height/2),(-span/2+mm(9),0, bh/2 ),(0,0,radians(-90)))
    handle_round_2 = create_mesh_object("tube2",*generate_cylinder_geometry(radius,span-mm(20),axis="y"),(-span/2+mm(10),0, bh/2+mm(46) ),(0,radians(180),radians(-90)))
    handle_round_3 = create_mesh_object("tube3",*generate_cylinder_geometry(radius,height/2),(span/2-mm(7.5),0, bh/2 ),(0,0,radians(90)))
    combine(handle_round_1,handle_round_2)
    combine(handle_round_3,handel)
    combine(handle_round_2,handel)
    gen_materials.assign_single_material(handel,gen_materials.LP_bezel())
    return handel

def make_buttons(hight,screen_w, screen_margin, y, mat_green, mat_orange, mat_bezel,mat_red, col):
    btn_x = -(screen_w/2 + screen_margin-mm(10)) 
    make_button_pill("Btn_Green",btn_x, mm(110),y,  mat_green, radius_mm=10, length_mm=35,col_ui=col,h=hight)
    make_button_pill("Btn_Orange",btn_x, mm(85),y,  mat_orange, radius_mm=10, length_mm=35,col_ui=col,h=hight)
    make_button_round("Btn_red",btn_x, mm(40),y, mat_red,radius_mm= 20,col_ui=col,h=hight )
    make_button_pill("Btn_Grey",btn_x, mm(00),y,  mat_bezel, radius_mm=10, length_mm=35,col_ui=col,h=hight)
    make_button_round("selection_dial",btn_x, -mm(40),y, mat_bezel,radius_mm= 20,col_ui=col,h=hight)
    make_button_round("speaker",btn_x, -mm(85),y, mat_bezel,radius_mm= 20 ,col_ui=col,h=hight )

# def make_pyramidal_bezel(
#     x, y, z,
#     base_width, base_depth, length_y,
#     top_width, top_depth,
#     top_boarder,
#     wall=0.05,
#     name="pyramidal_bezel"
# ):
#     # 1) äußere Frustum/Pyramide
#     outer = make_quad_pyramid_y(
#         x, y, z,
#         base_width=base_width,
#         base_depth=base_depth,
#         length_y=length_y,
#         top_width=top_width+top_boarder,
#         top_depth=top_depth+top_boarder,
#         name=f"{name}_outer"
#     )

#     # 2) Würfel, der innen „stehen bleiben“ soll (Vorderkante der Schräge)
#     bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x, y, z))
#     inner_cube = bpy.context.active_object
#     # Statt Scale -> direkt Dimensionen setzen (robuster):
#     inner_cube.dimensions = (top_width+top_boarder/2, length_y, top_depth+top_boarder/2)
#     inner_cube.name = f"{name}_innerCube"

#     # 3) Cutter (inner) – etwas größer in Y, damit er sicher durchschneidet
#     inner = make_quad_pyramid_y(
#         x, y, z,
#         base_width=max(0.0, base_width  - top_boarder),
#         base_depth=max(0.0, base_depth  - top_boarder),
#         length_y=length_y,# + 0.002,  # minimal länger statt mm(2)
#         top_width=max(0.0, top_width),
#         top_depth=max(0.0, top_depth),
#         name=f"{name}_cutter",
#         inverted=True
#     )

#     # # WICHTIG: zweite, unabhängige Kopie des Cutters für den Würfel
#     cutter2 = inner.copy()
#     cutter2.data = inner.data.copy()
#     bpy.context.collection.objects.link(cutter2)

#     # 4) Boolean an outer (Difference)
#     set_active(outer)
#     mod1 = outer.modifiers.new(name=f"{name}_bool_outer", type='BOOLEAN')
#     mod1.operation = 'DIFFERENCE'
#     mod1.solver = 'EXACT'
#     mod1.object = inner
#     bpy.ops.object.modifier_apply(modifier=mod1.name)

#     # # 5) Boolean an inner_cube (Difference) mit zweitem Cutter
#     set_active(inner_cube)
#     mod2 = inner_cube.modifiers.new(name=f"{name}_bool_cube", type='BOOLEAN')
#     mod2.operation = 'DIFFERENCE'
#     mod2.solver = 'EXACT'
#     mod2.object = cutter2
#     bpy.ops.object.modifier_apply(modifier=mod2.name)

#     # # 6) Cutter löschen (jetzt sind beide Modifier gebacken)
#     # for ob in (inner, cutter2):
#     #     bpy.data.objects.remove(ob, do_unlink=True)

#     # # 7) Objekte zusammenführen
#     # set_active(outer)
#     # inner_cube.select_set(True)
#     # bpy.ops.object.join()

#     # # 8) Normalen nach außen
#     # bpy.ops.object.editmode_toggle()
#     # bpy.ops.mesh.normals_make_consistent(inside=False)
#     # bpy.ops.object.editmode_toggle()

#     outer.name = name
#     return outer


def make_pyramidal_bezel(
    x, y, z,
    base_width, base_depth, length_y,
    bottom_boarder,
    top_boarder,
    corner_r_outer,
    name="pyramidal_bezel",
):
    corner_1 = make_quarter_donut_trapezoid(
    r_corner=corner_r_outer,
    top_wall=top_boarder,
    bottom_wall=bottom_boarder,
    location=(x+base_width/2 - corner_r_outer, y-length_y/2, z+base_depth/2- corner_r_outer),
    height=length_y,
    angle_deg=-90,
    steps=96
    )
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    corner_2 = make_quarter_donut_trapezoid(
    r_corner=corner_r_outer,
    top_wall=top_boarder,
    bottom_wall=bottom_boarder,
    location=(x+base_width/2 - corner_r_outer, y-length_y/2, z-base_depth/2+ corner_r_outer),
    height=length_y,
    angle_deg=90,
    steps=96
    )
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


    corner_3 = make_quarter_donut_trapezoid(
    r_corner=corner_r_outer,
    top_wall=top_boarder,
    bottom_wall=bottom_boarder,
    location=(x-base_width/2 + corner_r_outer, y-length_y/2, z+base_depth/2- corner_r_outer),
    height=length_y,
    angle_deg=90,
    steps=96
    )
    corner_3.rotation_euler = (0,radians(180),0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    corner_4 = make_quarter_donut_trapezoid(
    r_corner=corner_r_outer,
    top_wall=top_boarder,
    bottom_wall=bottom_boarder,
    location=(x-base_width/2 + corner_r_outer, y-length_y/2, z-base_depth/2+ corner_r_outer),
    height=length_y,
    angle_deg=-90,
    steps=96
    )
    corner_4.rotation_euler = (0,radians(180),0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    vert_length = base_depth -corner_r_outer*2+mm(0.01)

    left = make_quad_pyramid_y(
        0,0,0,
        base_width=bottom_boarder,
        base_depth=vert_length,
        length_y=length_y,
        top_width=top_boarder,
        top_depth=vert_length,
        name=f"left_wall"
    )
    left.location = (x+base_width/2-bottom_boarder/2, y, z)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    right = make_quad_pyramid_y(
        0,0,0,
        base_width=bottom_boarder,
        base_depth=vert_length,
        length_y=length_y,
        top_width=top_boarder,
        top_depth=vert_length,
        name=f"left_wall"
    )
    right.location = (x-base_width/2+bottom_boarder/2, y, z)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    horiz_length = base_width -corner_r_outer*2+mm(0.01)

    top = make_quad_pyramid_y(
        0,0,0,
        base_width=horiz_length,
        base_depth=bottom_boarder,
        length_y=length_y,
        top_width=horiz_length,
        top_depth=top_boarder,
        name=f"upper_wall"
    )
    top.location = (x, y, z+base_depth/2-bottom_boarder/2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bottom = make_quad_pyramid_y(
        0,0,0,
        base_width=horiz_length,
        base_depth=bottom_boarder,
        length_y=length_y,
        top_width=horiz_length,
        top_depth=top_boarder,
        name=f"upper_wall"
    )
    bottom.location = (x, y, z-base_depth/2+bottom_boarder/2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


    combine(corner_2,left)
    combine(corner_4,right)
    combine(corner_1,left)
    combine(corner_3,right)
    combine(left,bottom)
    combine(bottom,top)
    combine(top,right)






    # combine(corner_1, left)
    # combine(corner_4, right)
    # combine(corner_3, top)
    # combine(corner_2, bottom)
    # combine(top, left)
    # combine(bottom, right)
    # combine(left, right)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    right.name = name
    gen_materials.assign_single_material(right,gen_materials.LP_bezel())
    #gen_materials.assign_single_material(top,gen_materials.LP_bezel())

    return right#,top



    


