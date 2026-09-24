import bpy
from math import radians
from mathutils import Vector, Matrix

def _ensure_light_data(name, type):
    li = bpy.data.lights.get(name)
    if li and li.type != type:
        li.type = type
        return li
    if not li:
        li = bpy.data.lights.new(name=name, type=type)
    return li

def _ensure_object(name, datablock):
    obj = bpy.data.objects.get(name)
    if obj and obj.data != datablock:
        obj.data = datablock
    if not obj:
        obj = bpy.data.objects.new(name, datablock)
        bpy.context.scene.collection.objects.link(obj)
    return obj

def _axis_vector(axis_str):
    """Return unit vector for '+X','-X','+Y','-Y','+Z','-Z'."""
    m = {
        '+X': Vector((1,0,0)), '-X': Vector((-1,0,0)),
        '+Y': Vector((0,1,0)), '-Y': Vector((0,-1,0)),
        '+Z': Vector((0,0,1)), '-Z': Vector((0,0,-1)),
    }
    return m[axis_str]

def _look_at_rotation(from_loc, to_loc, align_axis='-Z', up_axis='+Y'):
    """
    Compute world rotation for an object so that its local `align_axis`
    points toward `to_loc` using `up_axis` as reference.
    """
    fwd = (Vector(to_loc) - Vector(from_loc)).normalized()
    if fwd.length == 0:
        return None  
    obj_fwd = _axis_vector(align_axis)
    obj_up  = _axis_vector(up_axis)
    world_up = Vector((0,0,1)) if abs(fwd.dot(Vector((0,0,1)))) < 0.999 else Vector((0,1,0))
    right = fwd.cross(world_up).normalized()
    up = right.cross(fwd).normalized()
    axes = {
        '+X': Vector((1,0,0)), '-X': Vector((-1,0,0)),
        '+Y': Vector((0,1,0)), '-Y': Vector((0,-1,0)),
        '+Z': Vector((0,0,1)), '-Z': Vector((0,0,-1)),
    }
    basis_world = [None, None, None]  
    for idx, local in enumerate((Vector((1,0,0)), Vector((0,1,0)), Vector((0,0,1)))):
        if obj_fwd ==  local: basis_world[idx] = fwd
        if obj_fwd == -local: basis_world[idx] = -fwd
    for idx, local in enumerate((Vector((1,0,0)), Vector((0,1,0)), Vector((0,0,1)))):
        if obj_up ==  local: basis_world[idx] = up
        if obj_up == -local: basis_world[idx] = -up
    for i in range(3):
        if basis_world[i] is None:
            basis_world[i] = right

    R = Matrix((
        (basis_world[0].x, basis_world[1].x, basis_world[2].x),
        (basis_world[0].y, basis_world[1].y, basis_world[2].y),
        (basis_world[0].z, basis_world[1].z, basis_world[2].z),
    ))
    return R.to_euler()

def upsert_light(
    name="KeyLight",
    type='SPOT',                  # 'POINT','SUN','SPOT','AREA'
    location=(0,0,0),
    energy=1000.0,                # Watts in Eevee/Cycles
    color=(1.0, 1.0, 1.0),        # linear RGB
    use_nodes=False,
    temperature=None,             # set e.g. 5600 for daylight, if nodes
    # Aiming options (choose ONE of the two):
    target_obj=None,              # bpy.types.Object to Track To
    target_location=None,         # (x,y,z) world location to look at
    align_axis='-Z',              # light “points” down -Z in Blender
    up_axis='+Y',
    make_constraint=True,         # create Track To when target_obj passed
    # Type-specific extras:
    spot_size_deg=45.0,
    spot_blend=0.15,              # 0..1
    spot_show_cone=True,
    sun_angle_deg=0.53,           # apparent sun size
    area_shape='SQUARE',          # 'SQUARE','RECTANGLE','DISK','ELLIPSE'
    area_size=(1.0, 1.0),         # (size_x, size_y)
    shadow_soft_size=0.25,        # for POINT/SPOT “radius”
    casts_shadows=True
):
    """
    Create or update a light with rich controls and optional aiming.
    Returns the light object.
    """
    li = _ensure_light_data(name, type)
    obj = _ensure_object(name, li)
    obj.location = location
    li.color = color
    if hasattr(li, "energy"):
        li.energy = energy
    if hasattr(li, "use_shadow"):
        li.use_shadow = bool(casts_shadows)
    if use_nodes and hasattr(li, "use_nodes"):
        li.use_nodes = True
        nt = li.node_tree
        if temperature is not None:
            nodes = nt.nodes
            links = nt.links
            bb = nodes.get("Blackbody") or nodes.new("ShaderNodeBlackbody")
            bb.name = "Blackbody"; bb.outputs[0].default_value = temperature
            emit = nodes.get("Emission") or nodes.new("ShaderNodeEmission")
            emit.name = "Emission"; emit.inputs["Strength"].default_value = energy
            out = nodes.get("Light Output") or nodes.new("ShaderNodeOutputLight")
            if not emit.inputs["Color"].is_linked:
                links.new(bb.outputs["Color"], emit.inputs["Color"])
            if not out.inputs["Surface"].is_linked:
                links.new(emit.outputs["Emission"], out.inputs["Surface"])
    else:
        if hasattr(li, "use_nodes"):
            li.use_nodes = False
    if type == 'SPOT':
        li.spot_size = radians(max(0.1, min(179.9, spot_size_deg)))
        li.spot_blend = max(0.0, min(1.0, spot_blend))
        if hasattr(obj.data, "show_cone"):
            obj.data.show_cone = bool(spot_show_cone)
        if hasattr(li, "shadow_soft_size"):
            li.shadow_soft_size = shadow_soft_size
    elif type == 'SUN':
        if hasattr(li, "angle"):
            li.angle = radians(max(0.0, sun_angle_deg))
    elif type == 'AREA':
        li.shape = area_shape
        if area_shape in {'RECTANGLE', 'ELLIPSE'} and hasattr(li, "size_y"):
            li.size = area_size[0]
            li.size_y = area_size[1]
        else:
            li.size = area_size[0]
    else:
        if hasattr(li, "shadow_soft_size"):
            li.shadow_soft_size = shadow_soft_size
    if target_obj and make_constraint:
        for c in [c for c in obj.constraints if c.type == 'TRACK_TO']:
            obj.constraints.remove(c)
        con = obj.constraints.new(type='TRACK_TO')
        con.target = target_obj
        con.track_axis = {
            '+X':'TRACK_X','-X':'TRACK_NEGATIVE_X',
            '+Y':'TRACK_Y','-Y':'TRACK_NEGATIVE_Y',
            '+Z':'TRACK_Z','-Z':'TRACK_NEGATIVE_Z',
        }[align_axis]
        con.up_axis = {'+X':'UP_X','+Y':'UP_Y','+Z':'UP_Z'}[up_axis]
    elif target_location is not None:
        eul = _look_at_rotation(obj.location, target_location, align_axis=align_axis, up_axis=up_axis)
        if eul is not None:
            obj.rotation_euler = eul

    return obj
