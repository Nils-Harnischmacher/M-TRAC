import bpy, math, bmesh
from VQ4M_Lib.models.model_helpers.helpers import mm, relink, round_corners, get_edges,generate_cylinder_geometry, create_mesh_object, combine,add_bevel_apply,verts_to_edge_indices,vis_edges,ensure_weighted_bevel,set_edge_weights_from_vertices,set_edge_weights,vis_verts

from VQ4M_Lib.models.model_helpers.geometry_helpers import make_button_pill,make_spo2_connector
from VQ4M_Lib.models.model_helpers import gen_materials 

def _bbox_local(obj):
    me = obj.data
    xs=[v.co.x for v in me.vertices]; ys=[v.co.y for v in me.vertices]; zs=[v.co.z for v in me.vertices]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))

def _make_cutter_cyl(radius, depth, loc, axis='Z', segments=96):
    bpy.ops.mesh.primitive_cylinder_add(vertices=segments, radius=radius, depth=depth, location=loc)
    c = bpy.context.active_object
    a = axis.upper()
    if a == 'Y':      c.rotation_euler[0] = math.radians(90)
    elif a == 'X':    c.rotation_euler[1] = math.radians(90)
    return c

def boolean_big_corner_round(
    obj,
    radius,
    corners=("MINX_MINY","MINX_MAXY","MAXX_MINY","MAXX_MAXY"),
    axis="Z",
    segments=96,
    extra_depth=0.02,           # same units as your scene scale
    keep_cutters=False,
    apply=True,
    cutters_collection_name="CornerCutters"
):
    """
    Carve big roundovers at selected XY corners by subtracting quarter-cylinders.
    Requires the object to be axis-aligned; apply scale before calling.
    """
    minx,maxx,miny,maxy,minz,maxz = _bbox_local(obj)
    sizeX, sizeY, sizeZ = (maxx-minx), (maxy-miny), (maxz-minz)

    a = axis.upper()
    if a == 'Z':
        depth = sizeZ + extra_depth
    elif a == 'Y':
        depth = sizeY + extra_depth
    else:
        depth = sizeX + extra_depth

    # --- create/find cutters collection (compare by NAME) ---
    cutters_col = (bpy.data.collections.get(cutters_collection_name)
                   or bpy.data.collections.new(cutters_collection_name))
    scene_child_names = {c.name for c in bpy.context.scene.collection.children}
    if cutters_col.name not in scene_child_names:
        bpy.context.scene.collection.children.link(cutters_col)

    cutters = []
    for tag in corners:
        cx_side, cy_side = tag.split("_")
        cx = minx if cx_side=="MINX" else maxx
        cy = miny if cy_side=="MINY" else maxy

        # move inward by the radius to be tangent to both faces
        px = cx + ( radius if cx_side=="MINX" else -radius )
        py = cy + ( radius if cy_side=="MINY" else -radius )

        if a == 'Z':
            loc = (px, py, (minz+maxz)/2.0)
        elif a == 'Y':
            loc = ((minx+maxx)/2.0, py, (minz+maxz)/2.0)
        else:  # 'X'
            loc = (px, (miny+maxy)/2.0, (minz+maxz)/2.0)

        cutter = _make_cutter_cyl(radius, depth, loc, axis=a, segments=segments)
        cutter.name = f"CornerCutter_{tag}"
        # move cutter to collection
        for col in list(cutter.users_collection):
            col.objects.unlink(cutter)
        cutters_col.objects.link(cutter)
        cutters.append(cutter)

    # Apply booleans
    bpy.context.view_layer.objects.active = obj
    for i, cutter in enumerate(cutters, start=1):
        mod = obj.modifiers.new(f"BooleanCorner_{i}", 'BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.solver = 'EXACT'
        mod.object = cutter
        if apply:
            bpy.ops.object.modifier_apply(modifier=mod.name)
            if not keep_cutters:
                bpy.data.objects.remove(cutter, do_unlink=True)
        else:
            cutter.hide_viewport = True
            cutter.hide_render = True

    return obj





def add_ramp_between(bottom_obj, top_obj, inset_x=0.0, inset_z=0.0, overlap_y=0.0,
                     bevel_radius=0.0, bevel_segments=6, name="Pouch_Ramp"):
    """
    Build a solid ramp that connects the front face of `bottom_obj` (its top surface)
    to the front face of `top_obj` (its bottom surface).

    - inset_x: trim a little from left/right so it nests between the cubes
    - inset_z: trim from height so it doesn't poke into either block
    - overlap_y: push a little into both cubes along Y for a seamless junction
    - bevel_radius: optional roundover on ramp edges (0 to skip)
    """


    # convenient dimensions/positions
    b = bottom_obj
    t = top_obj

    # World-space measures
    bx, by, bz = b.dimensions
    tx, ty, tz = t.dimensions

    # front (+Y) plane positions for each cube
    y_front_bottom = b.location.y + by/2
    y_front_top    = t.location.y + ty/2

    # Z levels we want to connect: top of bottom → bottom of top
    z_top_bottom = b.location.z + bz/2
    z_bot_top    = t.location.z - tz/2

    # X span: use the smaller width so it fits between
    half_w = min(bx, tx)/2 - inset_x
    half_w = max(half_w, 1e-6)

    # Optional insets & overlap
    z0 = z_top_bottom - inset_z
    z1 = z_bot_top    + inset_z
    y0 = y_front_top    - overlap_y  # back (toward the upper cube)
    y1 = y_front_bottom + overlap_y  # front (toward the lower cube)

    # Create mesh
    mesh = bpy.data.meshes.new(name)
    ramp = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(ramp)

    bm = bmesh.new()

    # 8 vertices (back = near upper square, front = near lower square)
    # back face at (y0, z1), front face at (y1, z0)
    v = []
    for (x, y, z) in [
        (-half_w, y0, z1),  # back-left-top (relative names just for clarity)
        ( half_w, y0, z1),  # back-right-top
        (-half_w, y0, z1 - (z1 - z0)),  # back-left-bottom (same as z0; explicit for readability)
        ( half_w, y0, z1 - (z1 - z0)),  # back-right-bottom

        (-half_w, y1, z0),  # front-left-bottom (sits on lower cube top)
        ( half_w, y1, z0),  # front-right-bottom
        (-half_w, y1, z0 + (z1 - z0)),  # front-left-top (same as z1)
        ( half_w, y1, z0 + (z1 - z0)),  # front-right-top
    ]:
        v.append(bm.verts.new((x, y, z)))

    bm.verts.ensure_lookup_table()

    # Faces (quads)
    faces = [
        (0,1,3,2),  # back
        (4,5,7,6),  # front
        (0,2,4,6),  # left
        (1,3,5,7),  # right
        (0,1,5,4),  # top-ish (slanted)
        (2,3,7,6),  # bottom-ish (slanted)
    ]
    for f in faces:
        bm.faces.new([bm.verts[i] for i in f])

    bm.to_mesh(mesh)
    bm.free()

    # Optional bevel to soften the ramp edges slightly
    if bevel_radius and bevel_radius > 0:
        bpy.context.view_layer.objects.active = ramp
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

        bev = ramp.modifiers.new("Ramp_Bevel", 'BEVEL')
        bev.width = bevel_radius
        bev.segments = bevel_segments
        bev.profile = 0.7
        bev.limit_method = 'ANGLE'   # only sharper edges
        bev.angle_limit = 0.523599   # ~30°
        bev.affect = 'EDGES'
        bev.use_clamp_overlap = True
        bev.miter_outer = 'MITER_ARC'

    return ramp






def create_base_pouch_left(base_width,base_depth,base_height,cover_depth,corner_r,edge_r=mm(20),location=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(size=1,location=location)
    pouch = bpy.context.active_object
    pouch.scale = (base_width, base_depth,base_height)
    pouch.name = "Pouch_Base_Left"
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    round_corners(pouch, width=corner_r, segments=20, profile=0.7)

    cover_bottom_square_h = base_height/3
    bpy.ops.mesh.primitive_cube_add(size=1,location=(pouch.location.x,pouch.location.y+base_depth/2+cover_depth/2-mm(1),pouch.location.z-base_height/2 +cover_bottom_square_h/2))
    cover_bottom_square = bpy.context.active_object
    cover_bottom_square.scale = (base_width, cover_depth, cover_bottom_square_h)
    cover_bottom_square.name = "Pouch_Cover_Bottom_Square_Left"
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    cover_upper_square_h = base_height/2
    bpy.ops.mesh.primitive_cube_add(size=1,location=(pouch.location.x,pouch.location.y+base_depth/2+cover_depth/4-mm(1),pouch.location.z+base_height/2-cover_upper_square_h/2 ))
    cover_upper_square = bpy.context.active_object
    cover_upper_square.scale = (base_width, cover_depth/2, cover_upper_square_h)
    cover_upper_square.name = "Pouch_Cover_upper_Square_Left"
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bx = base_width/2
    yF_bot = cover_bottom_square.location.y + cover_depth/2      # front of lower
    yB_bot = cover_bottom_square.location.y - cover_depth/2      # back  of lower
    yF_top = cover_upper_square.location.y + cover_depth/4       # front of upper
    yB_top = cover_upper_square.location.y - cover_depth/4       # back  of upper
    z_top_bottom = cover_bottom_square.location.z + cover_bottom_square_h/2  # top of lower cube
    z_bot_top    = cover_upper_square.location.z - cover_upper_square_h/2    # bottom of upper cube
    xC = cover_bottom_square.location.x  # (assume same x for both blocks)

    # ---- vertices (front quad first, then back quad) ----
    v0 = (xC - bx, yF_bot, z_top_bottom)  # front-left  bottom
    v1 = (xC + bx, yF_bot, z_top_bottom)  # front-right bottom
    v2 = (xC + bx, yF_top, z_bot_top)     # front-right top
    v3 = (xC - bx, yF_top, z_bot_top)     # front-left  top

    v4 = (xC - bx, yB_bot, z_top_bottom)  # back-left   bottom
    v5 = (xC + bx, yB_bot, z_top_bottom)  # back-right  bottom
    v6 = (xC + bx, yB_top, z_bot_top)     # back-right  top
    v7 = (xC - bx, yB_top, z_bot_top)     # back-left   top

    verts = [v0, v1, v2, v3, v4, v5, v6, v7]
    faces = [
        (0, 1, 2, 3),   # front (+Y)
        (5, 4, 7, 6),   # back  (reverse winding)
        (0, 3, 7, 4),   # left
        (1, 5, 6, 2),   # right
        (0, 4, 5, 1),   # bottom (touches lower cube)
        (3, 2, 6, 7),   # top    (touches upper cube)
    ]

    mesh = bpy.data.meshes.new("ramp_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update(calc_edges=True)
    ramp = bpy.data.objects.new("ramp_mesh", mesh)
    bpy.context.collection.objects.link(ramp)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

  
    bpy.ops.mesh.primitive_cube_add(size=1,location=(pouch.location.x,pouch.location.y+cover_depth/2,pouch.location.z))
    cutter_inner = bpy.context.active_object
    cutter_inner.scale = (base_width, base_depth+cover_depth+mm(20),base_height)
    cutter_inner.name = "cutter_inner_pouch_Left"
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    round_corners(cutter_inner, width=corner_r, segments=20, profile=0.7)
    bpy.ops.mesh.primitive_cube_add(size=1,location=(pouch.location.x,pouch.location.y+cover_depth/2,pouch.location.z))
    cutter_outter = bpy.context.active_object
    cutter_outter.scale = (base_width+mm(20), base_depth+cover_depth+mm(20),base_height+mm(20))
    cutter_outter.name = "cutter_outter_pouch_Left"
    mod = cutter_outter.modifiers.new(f"cutter_prep", 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cutter_inner
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter_inner, do_unlink=True)

    mod_lower = cover_bottom_square.modifiers.new("cut_lower_corners", 'BOOLEAN')
    mod_lower.operation = 'DIFFERENCE'
    mod_lower.solver    = 'EXACT'
    mod_lower.object    = cutter_outter

    bpy.context.view_layer.objects.active = cover_bottom_square
    cover_bottom_square.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod_lower.name)
    mod_upper = cover_upper_square.modifiers.new("cut_upper_corners", 'BOOLEAN')
    mod_upper.operation = 'DIFFERENCE'
    mod_upper.solver    = 'EXACT'
    mod_upper.object    = cutter_outter

    bpy.context.view_layer.objects.active = cover_upper_square
    cover_upper_square.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod_upper.name)

    bpy.data.objects.remove(cutter_outter, do_unlink=True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


    # List of vertices you want to mark
    # target_verts = [1,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45]  # change this!
    # vis_verts(cover_upper_square,target_verts)
    # target_edges=verts_to_edge_indices(cover_upper_square,target_verts)
    # vis_edges(cover_upper_square,target_edges)
    #target_edges_middel=[473,474,475,757,759,761,764,810,814,816,976,977,978,979,980,982,1305,1473,1474,1475,1476,1477,1750,1753,1755,1798,1803,1805,1807,1967,1968,1969,1970,1971,1972,1973,1974,1975,1976,1977,2240,2243,2245,2294,2297,2450,2451,2741,2743,2746,2794,2797,2800,2977,3231,3233,3237,3292,3449,3450,3451,3452,3453,3456,3474,3476,3477,3725,3728,3776,3778,3781,3783,3950,3951,3952,3953,3954,3955,3956,3957,3958,3959,3960,3961]

    target_edges_upper = get_edges(cover_upper_square,min)
    target_edges_lower= get_edges(cover_bottom_square,max)
    
    
    vis_edges(ramp,get_edges(ramp,None))


    #target_edges_upper=[1, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 18,19, 20, 21, 22, 23, 24, 25, 26, 27, 28,29, 30, 31, 32, 33, 34, 35,  36,37, 38, 39, 40, 41, 42, 43, 44, 45, 46]
    #target_edges_lower=[1,   7,8, 9, 10, 11,12,13,14, 15, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46,47,48,49,50]
    #vis_edges(cover_upper_square,[f for f in range(len(cover_upper_square.data.edges))])
    #vis_edges(cover_bottom_square,[f for f in range(len(cover_bottom_square.data.edges))])
    
    
    bpy.context.view_layer.objects.active = cover_bottom_square
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ensure_weighted_bevel(cover_bottom_square, width=edge_r, segments=20, profile=0.7, name="Bevel_Weighted_Cover_Bottom_Left")
    set_edge_weights(cover_bottom_square,target_edges_lower)
    ensure_weighted_bevel(ramp, width=edge_r, segments=20, profile=0.7, name="Bevel_Weighted_Cover_ramp_Left")
    set_edge_weights(ramp,[0,2,])
    ensure_weighted_bevel(cover_upper_square, width=edge_r, segments=20, profile=0.7, name="Bevel_Weighted_Cover_upper_Left")
    set_edge_weights(cover_upper_square,target_edges_upper)
    for ob in [cover_bottom_square, ramp, cover_upper_square]:
        for mod in ob.modifiers:
            if mod.type == 'BEVEL':
                bpy.context.view_layer.objects.active = ob
                bpy.ops.object.modifier_apply(modifier=mod.name)
    combine(ramp,cover_bottom_square)
    combine(cover_bottom_square,cover_upper_square)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    # pouch.hide_set(True)
    # cover_upper_square.hide_set(True)


    # CREAT VALCRO COVER LEFT 
    upper_vcover_width = base_width/3
    vcover_thickness = mm(3)
    lower_vcover_hight = base_height/3
    distance_from_edge_left = mm(8)
    distance_from_edge_top = 0
    vcover_depht = base_depth - mm(20)

    bpy.ops.mesh.primitive_cube_add(size=1,location=(pouch.location.x+base_width/2-upper_vcover_width+distance_from_edge_left-vcover_thickness,pouch.location.y,pouch.location.z+base_height/2-lower_vcover_hight+distance_from_edge_top))
    corner_cut_inner = bpy.context.active_object
    corner_cut_inner.scale = (upper_vcover_width*2+vcover_thickness*2, base_depth*2,lower_vcover_hight*2)
    corner_cut_inner.name = "corner_cut_inner"
    round_corners(corner_cut_inner, width=corner_r, segments=20, profile=0.7)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    bpy.ops.mesh.primitive_cube_add(size=1,location=(corner_cut_inner.location.x-upper_vcover_width/2+vcover_thickness/2,corner_cut_inner.location.y,corner_cut_inner.location.z+vcover_thickness))
    velcorcover_top_cutter = bpy.context.active_object
    velcorcover_top_cutter.scale = (upper_vcover_width+vcover_thickness*3, base_depth*2,lower_vcover_hight*2+2)
    velcorcover_top_cutter.name = "velcorcover_top_cutter"

    bpy.ops.mesh.primitive_cube_add(size=1,location=(corner_cut_inner.location.x+distance_from_edge_left,corner_cut_inner.location.y,corner_cut_inner.location.z-lower_vcover_hight))
    velcorcover_side_cutter = bpy.context.active_object
    velcorcover_side_cutter.scale = (2, base_depth*2,lower_vcover_hight*2)
    velcorcover_side_cutter.name = "velcorcover_side_cutter"
    
    
    combine(velcorcover_top_cutter,velcorcover_side_cutter)
    combine(velcorcover_side_cutter,corner_cut_inner)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    bpy.ops.mesh.primitive_cube_add(size=1,location=(pouch.location.x+base_width/2-upper_vcover_width+distance_from_edge_left,pouch.location.y,pouch.location.z+base_height/2-lower_vcover_hight+distance_from_edge_top))
    corner = bpy.context.active_object
    corner.scale = (upper_vcover_width*2+vcover_thickness*2, vcover_depht,lower_vcover_hight*2+vcover_thickness*2)
    corner.name = "corner_pouch_Left"
    round_corners(corner, width=corner_r+vcover_thickness, segments=20, profile=0.7)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    mod = corner.modifiers.new(f"cutter_velcro", 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = corner_cut_inner
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(corner_cut_inner, do_unlink=True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    cover_edges=[v for v in range(len(corner.data.edges)) ]
    
    ensure_weighted_bevel(corner, width=edge_r, segments=20, profile=0.7, name="velcor_corner_round")
    set_edge_weights(corner,[61,92])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    x=pouch.location.x+base_width/2
    y=pouch.location.y
    z=pouch.location.z
    bottom_thickness = 0.0   # 0 → a sharp edge; >0 → small bottom thickness

    # center the bottom thickness between the original x..x+top_thickness
    xb = x + (distance_from_edge_left - bottom_thickness) * 0.5

    z_bot = z - base_height/2 + corner_r
    z_top = z + base_height/2 - lower_vcover_hight/2
    yL    = y - vcover_depht/2
    yR    = y + vcover_depht/2

    # --- vertices: front (lower x) then back (higher x) ---
    # bottom (tapered along X)
    v0 = (x,                    yL, z_bot)  # front-left  bottom
    v1 = (x,                    yR, z_bot)  # front-right bottom
    v4 = (x + bottom_thickness, yL, z_bot)  # back-left   bottom
    v5 = (x + bottom_thickness, yR, z_bot)  # back-right  bottom

    # top (full thickness)
    v2 = (x,               yL, z_top)        # front-left  top
    v3 = (x,               yR, z_top)        # front-right top
    v6 = (x + distance_from_edge_left, yL, z_top)      # back-left   top
    v7 = (x + distance_from_edge_left, yR, z_top)      # back-right  top

    verts = [v0, v1, v2, v3, v4, v5, v6, v7]

    # consistent windings, outward normals
    faces = [
        (0, 1, 3, 2),   # front
        (4, 6, 7, 5),   # back
        (0, 2, 6, 4),   # left
        (1, 5, 7, 3),   # right
        (0, 4, 5, 1),   # bottom (tapered)
        (2, 3, 7, 6),   # top
    ]



    mesh = bpy.data.meshes.new("ramp_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update(calc_edges=True)
    ramp = bpy.data.objects.new("ramp_mesh", mesh)
    bpy.context.collection.objects.link(ramp)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    gen_materials.assign_single_material(pouch,gen_materials.LP_Pouches())
    gen_materials.assign_single_material(cover_upper_square,gen_materials.LP_Pouches())
    gen_materials.assign_single_material(corner,gen_materials.Lp_leather_pouches())
    gen_materials.assign_single_material(ramp,gen_materials.Lp_leather_pouches())




def ensure_group_bevel(obj, group_name, width, segments=20, profile=0.7, name="Bevel"):
    # Bevel-Mod für eine Vertex Group anlegen/konfigurieren
    mod = obj.modifiers.new(name=name, type='BEVEL')
    mod.limit_method = 'VGROUP'
    mod.vertex_group  = group_name
    mod.width     = width
    mod.segments  = segments
    mod.profile   = profile
    mod.affect    = 'EDGES'  # nur Kanten beveln
    # Optional schönere Shading-Kanten:
    # mod.harden_normals = True
    return mod

def add_vertex_group_from_edges(obj, group_name, edge_indices):
    me = obj.data
    # zugehörige Vertex-IDs sammeln (beide Endpunkte der Edges)
    vert_ids = set()
    for ei in edge_indices:
        e = me.edges[ei]
        vert_ids.update(e.vertices)
    # Gruppe anlegen/holen und befüllen
    vg = obj.vertex_groups.get(group_name) or obj.vertex_groups.new(name=group_name)
    vg.add(list(vert_ids), 1.0, 'REPLACE')
    return vg


def get_edge_indeces_x(obj):
    me = obj.data
    M  = obj.matrix_world
    mid_edges = []  # (midY, edge_index)
    for i, e in enumerate(me.edges):
        v1, v2 = e.vertices
        p1 = M @ me.vertices[v1].co
        p2 = M @ me.vertices[v2].co
        mid_world = M @ ((p1 + p2) * 0.5)
        mid_edges.append((mid_world, i))
    max_midX = max(x.x for x, _ in mid_edges)
    min_midX = min(x.x for x, _ in mid_edges)
    edges_indices = [i for y, i in mid_edges if abs(y.x - min_midX) < 1e-8 or abs(y.x - max_midX) < 1e-8 ]
    return edges_indices

def create_zipper(location,corner_r,hight,width,zipper_thickniss = mm(5),rounded=True):

    bpy.ops.mesh.primitive_cube_add(size=1,location=location)
    zipper = bpy.context.active_object
    zipper.scale = (width, zipper_thickniss,hight)
    zipper.name = "Pouch_Base_Left"
    zipper.rotation_euler = (0,0,math.radians(90))
    round_corners(zipper, width=corner_r, segments=20, profile=0.7)

    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    if rounded:
        me = zipper.data
        M  = zipper.matrix_world
        mid_edges = []  # (midY, edge_index)
        for i, e in enumerate(me.edges):
            v1, v2 = e.vertices
            p1 = M @ me.vertices[v1].co
            p2 = M @ me.vertices[v2].co
            mid_world = M @ ((p1 + p2) * 0.5)
            mid_edges.append((mid_world, i))
        max_midX = max(x.x for x, _ in mid_edges)
        min_midX = min(x.x for x, _ in mid_edges)
        edges_indices = [i for y, i in mid_edges if abs(y.x - min_midX) < 1e-8 or abs(y.x - max_midX) < 1e-8 ]
        #vis_edges(zipper,edges_indices)
        #vis_edges(zipper,range(len(me.edges)))

        ensure_weighted_bevel(zipper, width=zipper_thickniss/2, segments=20, profile=0.7, name="Bevel_Weighted_Cover_Bottom_Left",use_clamp_overlap=False)
        set_edge_weights(zipper,edges_indices)
    return zipper


def create_base_pouch_right(base_width,base_depth,base_height,cover_depth,corner_r,edge_r=mm(20),location=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(size=1,location=location)
    pouch = bpy.context.active_object
    pouch.scale = (base_width, base_depth,base_height)
    pouch.name = "Pouch_Base_Left"
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    bpy.ops.mesh.primitive_cube_add(size=1,location=(pouch.location.x,pouch.location.y,pouch.location.z))
    cutter_inner = bpy.context.active_object
    cutter_inner.scale = (base_width, base_depth+mm(50),base_height-mm(1))
    cutter_inner.name = "cutter_inner_pouch_right"
    round_corners(cutter_inner, width=corner_r, segments=20, profile=0.7)
    cutter_inner.rotation_euler = (0,0,math.radians(90))
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.mesh.primitive_cube_add(size=1,location=(pouch.location.x,pouch.location.y,pouch.location.z))
    cutter_outter = bpy.context.active_object
    cutter_outter.scale = (base_width+mm(20), base_depth+cover_depth,base_height+mm(20))
    cutter_outter.name = "cutter_outter_pouch_right"
    mod = cutter_outter.modifiers.new(f"cutter_prep", 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cutter_inner
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter_inner, do_unlink=True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


    mod_pouch = pouch.modifiers.new("cut_corners", 'BOOLEAN')
    mod_pouch.operation = 'DIFFERENCE'
    mod_pouch.solver    = 'EXACT'
    mod_pouch.object    = cutter_outter
    bpy.context.view_layer.objects.active = pouch
    bpy.ops.object.modifier_apply(modifier=mod_pouch.name)
    bpy.data.objects.remove(cutter_outter, do_unlink=True)

    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    ensure_weighted_bevel(pouch, width=edge_r, segments=20, profile=0.7, name="Bevel_Weighted_Cover_Bottom_Left",use_clamp_overlap=False)
    set_edge_weights(pouch,get_edge_indeces_x(pouch))
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

 # CREAT VALCRO COVER LEFT 
    upper_vcover_width = base_width/3
    vcover_thickness = mm(3)
    lower_vcover_hight = base_height/3
    distance_from_edge_left = mm(8)
    distance_from_edge_top = -mm(1)
    vcover_depht = base_depth - mm(40)

    bpy.ops.mesh.primitive_cube_add(size=1,location=(pouch.location.x-base_width/2+upper_vcover_width-distance_from_edge_left+vcover_thickness,pouch.location.y,pouch.location.z+base_height/2-lower_vcover_hight+distance_from_edge_top))
    corner_cut_inner = bpy.context.active_object
    corner_cut_inner.scale = (upper_vcover_width*2+vcover_thickness*2, base_depth*2,lower_vcover_hight*2)
    corner_cut_inner.name = "corner_cut_inner"
    round_corners(corner_cut_inner, width=corner_r, segments=20, profile=0.7)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    bpy.ops.mesh.primitive_cube_add(size=1,location=(corner_cut_inner.location.x+upper_vcover_width/2-vcover_thickness/2,corner_cut_inner.location.y,corner_cut_inner.location.z+vcover_thickness))
    velcorcover_top_cutter = bpy.context.active_object
    velcorcover_top_cutter.scale = (upper_vcover_width+vcover_thickness*3, base_depth*2,lower_vcover_hight*2+2)
    velcorcover_top_cutter.name = "velcorcover_top_cutter"

    bpy.ops.mesh.primitive_cube_add(size=1,location=(corner_cut_inner.location.x+distance_from_edge_left,corner_cut_inner.location.y,corner_cut_inner.location.z-lower_vcover_hight))
    velcorcover_side_cutter = bpy.context.active_object
    velcorcover_side_cutter.scale = (2, base_depth*2,lower_vcover_hight*2)
    velcorcover_side_cutter.name = "velcorcover_side_cutter"
    
    
    combine(velcorcover_top_cutter,velcorcover_side_cutter)
    combine(velcorcover_side_cutter,corner_cut_inner)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    bpy.ops.mesh.primitive_cube_add(size=1,location=(pouch.location.x-base_width/2+upper_vcover_width-distance_from_edge_left,pouch.location.y,pouch.location.z+base_height/2-lower_vcover_hight+distance_from_edge_top))
    corner = bpy.context.active_object
    corner.scale = (upper_vcover_width*2+vcover_thickness*2, vcover_depht,lower_vcover_hight*2+vcover_thickness*2)
    corner.name = "corner_pouch_Left"
    round_corners(corner, width=corner_r+vcover_thickness, segments=20, profile=0.7)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    mod = corner.modifiers.new(f"cutter_velcro", 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = corner_cut_inner
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(corner_cut_inner, do_unlink=True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    cover_edges=[v for v in range(len(corner.data.edges)) ]
    
    ensure_weighted_bevel(corner, width=edge_r, segments=20, profile=0.7, name="velcor_corner_round")
    set_edge_weights(corner,[61,92])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    x=pouch.location.x-base_width/2
    y=pouch.location.y
    z=pouch.location.z
    bottom_thickness = 0.0   # 0 → a sharp edge; >0 → small bottom thickness

    # center the bottom thickness between the original x..x+top_thickness
    xb = x + (distance_from_edge_left - bottom_thickness) * 0.5

    z_bot = z - base_height/2 + corner_r
    z_top = z + base_height/2 - lower_vcover_hight/2
    yL    = y - vcover_depht/2
    yR    = y + vcover_depht/2

    # --- vertices: front (lower x) then back (higher x) ---
    # bottom (tapered along X)
    v0 = (x,                    yL, z_bot)  # front-left  bottom
    v1 = (x,                    yR, z_bot)  # front-right bottom
    v4 = (x - bottom_thickness, yL, z_bot)  # back-left   bottom
    v5 = (x - bottom_thickness, yR, z_bot)  # back-right  bottom

    # top (full thickness)
    v2 = (x,               yL, z_top)        # front-left  top
    v3 = (x,               yR, z_top)        # front-right top
    v6 = (x - distance_from_edge_left, yL, z_top)      # back-left   top
    v7 = (x - distance_from_edge_left, yR, z_top)      # back-right  top

    verts = [v0, v1, v2, v3, v4, v5, v6, v7]

    # consistent windings, outward normals
    faces = [
        (0, 1, 3, 2),   # front
        (4, 6, 7, 5),   # back
        (0, 2, 6, 4),   # left
        (1, 5, 7, 3),   # right
        (0, 4, 5, 1),   # bottom (tapered)
        (2, 3, 7, 6),   # top
    ]



    mesh = bpy.data.meshes.new("ramp_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update(calc_edges=True)
    ramp = bpy.data.objects.new("ramp_mesh", mesh)
    bpy.context.collection.objects.link(ramp)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

 #ZIPPER BUILD
    offset = mm(6)
    offset2 = mm(4)
    zipper_offset = mm(2)
    thickniss = mm(5)
    x=pouch.location.x
    y=pouch.location.y
    z=pouch.location.z
    zip1=create_zipper(location=(x-mm(30),y,z),corner_r=corner_r,hight=base_height+offset,width=base_width+offset,zipper_thickniss=thickniss)
    zip2=create_zipper(location=(x-mm(18.25),y,z),corner_r=corner_r,hight=base_height+zipper_offset,width=base_width+zipper_offset,zipper_thickniss=mm(19),rounded=False)
    zip3=create_zipper(location=(x-mm(7.5),y,z),corner_r=corner_r,hight=base_height+offset,width=base_width+offset,zipper_thickniss=thickniss)
    zip4=create_zipper(location=(x,y,z),corner_r=corner_r,hight=base_height+offset2,width=base_width+offset2,zipper_thickniss=mm(10),rounded=False)
    zip5=create_zipper(location=(x+mm(7.5),y,z),corner_r=corner_r,hight=base_height+offset,width=base_width+offset,zipper_thickniss=thickniss)
    zip6=create_zipper(location=(x+mm(30),y,z),corner_r=corner_r,hight=base_height+offset,width=base_width+offset,zipper_thickniss=thickniss)
    zip7=create_zipper(location=(x+mm(18.25),y,z),corner_r=corner_r,hight=base_height+zipper_offset,width=base_width+zipper_offset,zipper_thickniss=mm(19),rounded=False)
        
    gen_materials.assign_single_material(pouch,gen_materials.LP_Pouches())
    gen_materials.assign_single_material(corner,gen_materials.Lp_leather_pouches())
    gen_materials.assign_single_material(ramp,gen_materials.Lp_leather_pouches())
    gen_materials.assign_single_material(zip1,gen_materials.Lp_leather_pouches())
    gen_materials.assign_single_material(zip3,gen_materials.Lp_leather_pouches())
    gen_materials.assign_single_material(zip4,gen_materials.Lp_leather_pouches())
    gen_materials.assign_single_material(zip5,gen_materials.Lp_leather_pouches())
    gen_materials.assign_single_material(zip6,gen_materials.Lp_leather_pouches())

    gen_materials.assign_single_material(zip2,gen_materials.Lp_zipper())
    gen_materials.assign_single_material(zip7,gen_materials.Lp_zipper())





