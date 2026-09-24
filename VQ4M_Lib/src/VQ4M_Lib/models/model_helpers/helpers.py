import bpy, bmesh
import math


    
def mm(val): return val * 0.001

def deselect_all():
    for o in bpy.data.objects:
        o.select_set(False)

def new_collection(name, parent=None):
    col = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(col)
    return col

def relink(obj, target_col):
    """Safely move obj into target_col, unlinking from any others."""
    if obj.name not in target_col.objects:
        target_col.objects.link(obj)
    for c in list(obj.users_collection):
        if c != target_col:
            c.objects.unlink(obj)


def add_bevel(obj, width, segments, miter_outer='MITER_ARC'):
    bev = obj.modifiers.new("Bevel", 'BEVEL')
    bev.width = width
    bev.segments = segments
    bev.profile = 0.7
    bev.limit_method = 'WEIGHT'
    bev.use_clamp_overlap = True
    bev.miter_outer = miter_outer
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.transform.edge_bevelweight(value=1.0)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    
def round_corners(obj, width, segments, profile=0.7):
    """
    Bevel only the 4 long edges that run parallel to the Y-axis
    (the vertical rails of the outer bezel frame).
    """

    bpy.context.view_layer.objects.active = obj
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # Bevel modifier using edge weights
    bev = obj.modifiers.get("Bevel_VRails") or obj.modifiers.new("Bevel_VRails", 'BEVEL')
    bev.width = width
    bev.segments = segments
    bev.profile = profile
    bev.limit_method = 'WEIGHT'
    bev.affect = 'EDGES'
    bev.use_clamp_overlap = True
    bev.miter_outer = 'MITER_ARC'

    # Assign weights to just the Y-parallel edges
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data)

    layer = bm.edges.layers.float.get("bevel_weight_edge")
    if not layer:
        layer = bm.edges.layers.float.new("bevel_weight_edge")

    for e in bm.edges:
        e[layer] = 0.0

    xs = [v.co.x for v in bm.verts]
    ys = [v.co.y for v in bm.verts]
    zs = [v.co.z for v in bm.verts]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    min_z, max_z = min(zs), max(zs)
    tol = (max_x - min_x + max_y - min_y + max_z - min_z) * 1e-6 + 1e-9

    def is_y_parallel(e):
        # same X & Z → edge runs only along Y direction
        return abs(e.verts[0].co.x - e.verts[1].co.x) < tol and \
               abs(e.verts[0].co.z - e.verts[1].co.z) < tol

    for e in bm.edges:
        if is_y_parallel(e):
            # also make sure edge is on the outer frame, not inner hole
            if (abs(e.verts[0].co.x - min_x) < tol or abs(e.verts[0].co.x - max_x) < tol) \
               and (abs(e.verts[0].co.z - min_z) < tol or abs(e.verts[0].co.z - max_z) < tol):
                e[layer] = 1.0

    bmesh.update_edit_mesh(obj.data)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=bev.name)
    



def add_mat(name, rgba):
    if name in bpy.data.materials:
        mat = bpy.data.materials[name]
    else:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = 0.6
    return mat

def add_bool_diff(target, cutter, apply=True, name="Cut"):
    mod = target.modifiers.new(name, 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cutter
    bpy.context.view_layer.objects.active = target
    if apply:
        bpy.ops.object.modifier_apply(modifier=mod.name)
    cutter.hide_set(True)
    cutter.hide_render = True

def add_bevel_apply(obj, width, segments=8, profile=0.7, name="BevelTmp"):
    #Add a bevel that affects ALL edges, then APPLY it (convert to geometry).

    bpy.context.view_layer.objects.active = obj
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    bev = obj.modifiers.get(name) or obj.modifiers.new(name, 'BEVEL')
    bev.width = width
    bev.segments = segments
    bev.profile = profile
    bev.limit_method = 'NONE'      # bevel every edge
    bev.affect = 'EDGES'
    bev.use_clamp_overlap = True
    bev.miter_outer = 'MITER_ARC'
    bpy.ops.object.modifier_apply(modifier=bev.name)
    return obj

def generate_cylinder_geometry(radius, height, segments=32, axis='Z'):
    verts = []
    faces = []
    axis = axis.upper()
    def orient(a, h):
        x = radius * math.cos(a)
        y = radius * math.sin(a)
        if axis == 'Z': return (x, y, h)
        elif axis == 'X': return (h, x, y)
        elif axis == 'Y': return (x, h, y)

    for i in range(segments):
        angle =  math.pi * i / segments
        verts.append(orient(angle, 0))
    for i in range(segments):
        angle =  math.pi * i / segments
        verts.append(orient(angle, height))

    center0 = len(verts)
    verts.append(orient(0, 0))
    center1 = len(verts)
    verts.append(orient(0, height))

    for i in range(segments):
        ni = (i + 1) % segments
        faces.append((i, ni, ni + segments, i + segments))  # side
        faces.append((center0, ni, i))  # bottom
        faces.append((center1, i + segments, ni + segments))  # top

    return verts, faces

def combine(obj_to_add, obj_main):
    mod = obj_main.modifiers.new("Union", type='BOOLEAN')
    mod.operation = 'UNION'
    mod.solver = 'EXACT'  # more reliable than 'FAST'
    mod.object = obj_to_add

    bpy.context.view_layer.objects.active = obj_main

    # Apply transforms for safety
    bpy.ops.object.select_all(action='DESELECT')
    obj_main.select_set(True)
    obj_to_add.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    bpy.ops.object.modifier_apply(modifier=mod.name)

    # Delete the added object
    bpy.data.objects.remove(obj_to_add, do_unlink=True)

def join_objects(objects, name="JoinedParts"):
    ctx = bpy.context
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    ctx.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    joined_obj = ctx.active_object
    joined_obj.name = name
    return joined_obj

def create_mesh_object(name, verts, faces,location=(0,0,0), rotation=(0,0,math.radians(90)) ):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    obj.rotation_euler = rotation
    bpy.context.collection.objects.link(obj)
    return obj


def ensure_weighted_bevel(obj, width, segments=6, profile=0.7, name="Bevel_Weighted",use_clamp_overlap = True):
    """Create/reuse a WEIGHT-limited edge bevel modifier."""
    bev = obj.modifiers.get(name) or obj.modifiers.new(name, 'BEVEL')
    bev.width = width
    bev.segments = segments
    bev.profile = profile
    bev.limit_method = 'WEIGHT'
    bev.affect = 'EDGES'
    bev.use_clamp_overlap = use_clamp_overlap
    bev.miter_outer = 'MITER_ARC'
    return bev

def set_edge_weights(obj, edge_indices=None, weight=1.0, clear_others=True):
    """
    Write bevel weights to specific edges.
    - edge_indices: iterable of edge indices (from obj.data.edges), or None
                    If None, uses current Edit-Mode edge selection.
    - clear_others: zero out weights on all other edges first (default True).
    """
    bpy.context.view_layer.objects.active = obj
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data)

    layer = bm.edges.layers.float.get("bevel_weight_edge") or bm.edges.layers.float.new("bevel_weight_edge")

    if clear_others:
        for e in bm.edges:
            e[layer] = 0.0

    if edge_indices is None:
        # use current selection
        target_edges = [e for e in bm.edges if e.select]
    else:
        bm.edges.ensure_lookup_table()
        target_edges = [bm.edges[i] for i in edge_indices]

    for e in target_edges:
        e[layer] = float(weight)

    bmesh.update_edit_mesh(obj.data)
    bpy.ops.object.mode_set(mode='OBJECT')

def set_edge_weights_from_vertices(obj, vert_indices, weight=1.0, clear_others=True):
    """Tag edges whose BOTH endpoints are in vert_indices."""
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data)

    layer = bm.edges.layers.float.get("bevel_weight_edge") or bm.edges.layers.float.new("bevel_weight_edge")
    if clear_others:
        for e in bm.edges:
            e[layer] = 0.0

    vset = set(vert_indices)
    bm.edges.ensure_lookup_table()
    for e in bm.edges:
        v0, v1 = e.verts
        if v0.index in vset and v1.index in vset:
            e[layer] = float(weight)

    bmesh.update_edit_mesh(obj.data)
    bpy.ops.object.mode_set(mode='OBJECT')


def vis_verts(obj,target_verts):
    mesh = obj.data

        # Optional: remove old debug markers
    for o in list(bpy.data.objects):
        if o.name.startswith("VERT_MARK_"):
            bpy.data.objects.remove(o, do_unlink=True)

    for i in target_verts:
        v = mesh.vertices[i]
        world_pos = obj.matrix_world @ v.co
        empty = bpy.data.objects.new(f"VERT_MARK_{i}", None)
        empty.empty_display_size = 0.005
        empty.empty_display_type = 'SPHERE'
        empty.location = world_pos
        bpy.context.collection.objects.link(empty)


def vis_edges(obj, edge_indices, size=0.005, prefix="EDGE_MARK_"):
    """
    Visualize edges by placing small empties at their midpoints (Object Mode safe).
    edge_indices: list of indices from obj.data.edges
    """
    me = obj.data
    M  = obj.matrix_world

    # clear previous markers
    for o in list(bpy.data.objects):
        if o.name.startswith(prefix):
            bpy.data.objects.remove(o, do_unlink=True)

    for ei in edge_indices:
        e = me.edges[ei]
        v0 = me.vertices[e.vertices[0]].co
        v1 = me.vertices[e.vertices[1]].co
        mid_world = M @ ((v0 + v1) * 0.5)

        empt = bpy.data.objects.new(f"{prefix}{ei}", None)
        empt.empty_display_type = 'SPHERE'
        empt.empty_display_size = size
        empt.location = mid_world
        bpy.context.collection.objects.link(empt)


def verts_to_edge_indices(obj, vert_indices, require_both=True):
    """
    Return a list of edge indices from obj.data.edges that connect the given vertices.
    - require_both=True  -> only edges whose two endpoints are in vert_indices
      require_both=False -> edges with at least one endpoint in vert_indices
    """
    me = obj.data
    vset = set(vert_indices)
    hits = []
    for i, e in enumerate(me.edges):
        v0, v1 = e.vertices
        if (v0 in vset and v1 in vset) if require_both else (v0 in vset or v1 in vset):
            hits.append(i)
    return hits

def get_edges(obj, z_filter =None):
    me = obj.data
    M  = obj.matrix_world
    midY_per_edge = []  # (midY, edge_index)
    for i, e in enumerate(me.edges):
        v1, v2 = e.vertices
        p1 = M @ me.vertices[v1].co
        p2 = M @ me.vertices[v2].co
        mid_world = M @ ((p1 + p2) * 0.5)
        midY_per_edge.append((mid_world, i))
    max_midY = max(y.y for y, _ in midY_per_edge)
    if z_filter != None: 
        z_filtered = z_filter(z.z for z, _ in midY_per_edge)        
        edges_indices = [i for y, i in midY_per_edge if abs(y.y - max_midY) < 1e-8 and not(abs(y.z-z_filtered)< 1e-8)]
    else:
        edges_indices = [i for y, i in midY_per_edge if abs(y.y - max_midY) < 1e-8]

    return edges_indices

