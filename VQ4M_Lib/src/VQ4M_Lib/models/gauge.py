import bpy
import math
from VQ4M_Lib import general as gen
from VQ4M_Lib import boundingbox as bb
def create_gauge_dial(radius=5, vertex_count=100, location=(0, 0, 0)):
    bpy.ops.mesh.primitive_circle_add(vertices=vertex_count, radius=radius, fill_type='NOTHING', location=location)
    dial = bpy.context.active_object
    dial.name = "GaugeDial"
    return dial


def add_number_labels(
    min_val, max_val,
    start_angle=0, sweep_angle=360,
    radius=5.8, scale=0.4, location=(0, 0, 0),
    label_orientation_deg=0  # <- fixed orientation for all labels
):
    label_objects = []

    # Create or reuse a black material
    mat_name = "BlackTextMaterial"
    if mat_name in bpy.data.materials:
        black_material = bpy.data.materials[mat_name]
    else:
        black_material = bpy.data.materials.new(name=mat_name)
        black_material.diffuse_color = (0, 0, 0, 1)

    fixed_rot = math.radians(label_orientation_deg)

    for i in range(min_val, max_val):
        # position along the arc
        t = (i - min_val) / (max_val - min_val)
        angle_deg = start_angle + t * sweep_angle
        angle_rad = math.radians(angle_deg)

        x = radius * math.cos(angle_rad) + location[0]
        y = radius * math.sin(angle_rad) + location[1]-0.36
        z = location[2]

        bpy.ops.object.text_add(location=(x, y, z))
        txt = bpy.context.active_object
        txt.data.body = str(i)

        # keep all labels with the same orientation like a real gauge
        txt.rotation_euler = (0, 0, fixed_rot)
        txt.scale = (scale, scale, scale)

        # center the text so numbers sit on the tick nicely
        txt.data.align_x = 'CENTER'
        # (Optional, if available in your Blender version)
        # txt.data.align_y = 'CENTER'

        # Assign the black material
        if len(txt.data.materials) == 0:
            txt.data.materials.append(black_material)
        else:
            txt.data.materials[0] = black_material

        label_objects.append(txt)

    return label_objects


def add_tick_marks(min_val, max_val, major=True, minor_ticks=2, start_angle=0, sweep_angle=360,
                   outer_radius=5.3, inner_radius=5.0, tick_height=0.1, tick_thickness=0.05, location=(0, 0, 0)):
    tick_objects = []
    step = 1 / minor_ticks if not major else 1
    count = int((max_val - min_val) / step)
     # Create or reuse a black material
    mat_name = "RedTextMaterial"
    if mat_name in bpy.data.materials:
        black_material = bpy.data.materials[mat_name]
        black_material.diffuse_color = (255,0,0, 1) 
    else:
        black_material = bpy.data.materials.new(name=mat_name)
        black_material.diffuse_color = (139, 0, 0, 1)  # Black with full alpha
    
    for i in range(count):
        value = min_val + i * step
        if major and value % 1 != 0:
            continue
        if not major and value % 1 == 0:
            continue
        
        t = (value - min_val) / (max_val - min_val)
        angle_deg = start_angle + t * sweep_angle
        angle_rad = math.radians(angle_deg)

        r_in = inner_radius + 0.2 if not major else inner_radius
        r_out = outer_radius

        x_outer = r_out * math.cos(angle_rad) + location[0]
        y_outer = r_out * math.sin(angle_rad) + location[1]
        x_inner = r_in * math.cos(angle_rad) + location[0]
        y_inner = r_in * math.sin(angle_rad) + location[1]
        z = location[2] + 0.01

        bpy.ops.mesh.primitive_cube_add(size=1, location=((x_outer + x_inner) / 2, (y_outer + y_inner) / 2, z))
        tick = bpy.context.active_object
        tick.scale = ((tick_height * 0.6) if not major else tick_height, tick_thickness, 0.02)
        tick.rotation_euler = (0, 0, angle_rad)
        tick.name = f"{'Minor' if not major else 'Tick'}_{value:.2f}"
         # Assign the black material
        if len(tick.data.materials) == 0:
            tick.data.materials.append(black_material)
        else:
            tick.data.materials[0] = black_material
        tick_objects.append(tick)
    return tick_objects

def create_needle(length=2.5, thickness=0.05, location=(0, 0, 0)):
    mat_name = "BlackTextMaterial"
    if mat_name in bpy.data.materials:
        black_material = bpy.data.materials[mat_name]
    else:
        black_material = bpy.data.materials.new(name=mat_name)
        black_material.diffuse_color = (0, 0, 0, 1)

    # Create a unit cube centered at origin
    bpy.ops.mesh.primitive_cube_add(size=1, location=(location[0], location[1], location[2] + 0.01))
    needle = bpy.context.active_object
    needle.name = "Needle"

    # Make it the desired size
    needle.scale = (length, thickness, 0.02)

    # Shift mesh so the left end sits at the object's origin (the base)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.transform.translate(value=(length / 2.0, 0, 0), orient_type='LOCAL')
    bpy.ops.object.mode_set(mode='OBJECT')

    # Material
    if len(needle.data.materials) == 0:
        needle.data.materials.append(black_material)
    else:
        needle.data.materials[0] = black_material

    return needle


def create_hub(radius=0.2, location=(0, 0, 0)):
    mat_name = "BlackTextMaterial"
    if mat_name in bpy.data.materials:
        black_material = bpy.data.materials[mat_name]
    else:
        black_material = bpy.data.materials.new(name=mat_name)
        black_material.diffuse_color = (0, 0, 0, 1)  # Black with full alphaV
    bpy.ops.mesh.primitive_circle_add(radius=radius, fill_type='NGON', location=(location[0], location[1], location[2] + 0.02))
    hub = bpy.context.active_object
    hub.name = "NeedleHub"
    if len(hub.data.materials) == 0:
        hub.data.materials.append(black_material)
    else:
        hub.data.materials[0] = black_material
    return hub

# === ANIMATION ===

def animate_needle_to(needle, value, min_value, max_value,
                      start_angle=0, sweep_angle=360,
                      duration=25, start_frame=1):
    # Map value -> angle
    t = (value - min_value) / (max_value - min_value)
    angle = math.radians(start_angle + t * sweep_angle)

    needle.rotation_mode = 'XYZ'
    # ← DO NOT reset to start_angle here.
    # Use the current rotation (set from start_val) as the first key:
    needle.keyframe_insert(data_path="rotation_euler", frame=start_frame)

    # Animate to the target angle
    needle.rotation_euler[2] = angle
    needle.keyframe_insert(data_path="rotation_euler", frame=start_frame + duration)

    # Linear interpolation
    if needle.animation_data and needle.animation_data.action:
        for fcurve in needle.animation_data.action.fcurves:
            for kf in fcurve.keyframe_points:
                kf.interpolation = 'LINEAR'




def get_or_create_material(name, base_color=(0.95, 0.95, 0.95, 1.0), metallic=0.0, roughness=0.7):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
    # Configure Principled BSDF
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = base_color
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
    return mat

def create_backing(radius=6.2, thickness=0.2, location=(0, 0, 0),
                   color=(0.95, 0.95, 0.95, 1.0), metallic=0.0, roughness=0.7,
                   segments=64):
    """
    Creates a visible backing plate for the gauge.

    segments: higher = smoother circle; lower = more faceted look.
    """
    # Slightly behind the dial
    z = location[2] - thickness * 0.5 - 0.02
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius,
        depth=thickness,
        vertices=segments,  # here’s the control
        location=(location[0], location[1], z)
    )
    back = bpy.context.active_object
    back.name = "GaugeBack"

    mat = get_or_create_material("GaugeBackingMaterial", base_color=color, metallic=metallic, roughness=roughness)
    if len(back.data.materials) == 0:
        back.data.materials.append(mat)
    else:
        back.data.materials[0] = mat

    return back





def create_full_gauge(anim=True, start_val=0, end_val=7, min_val=1, max_val=10,
                      start_angle=180, sweep_angle=360, location=(0, 0, 0), rotation=(0, 0, 0)):
    parent = gen.create_parent("GaugeRoot", location, rotation)

    backing = create_backing(radius=6.2, thickness=0.2, location=location,
                            color=(0.96, 0.96, 0.96, 1.0),
                            metallic=0.0, roughness=0.7,
                            segments=100)

    backing.parent = parent

    dial = create_gauge_dial(location=location)
    dial.parent = parent

    labels = add_number_labels(min_val, max_val, start_angle, sweep_angle, location=location, scale=1)
    targets=[]
    parents =[]
    for idx, obj in enumerate(labels): 
        obj.parent = parent
        bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0,0.36,0))
        target = bpy.context.active_object
        target.name = str(range(min_val,max_val)[idx])
        target.parent = obj
        targets.append(target) 
        parents.append(obj)
        #bb.show_bb(target,width=float(0.8), height=float(0.8),offset=(0,0,0.001))



    ticks_major = add_tick_marks(min_val, max_val, major=True, start_angle=start_angle, sweep_angle=sweep_angle, location=location,tick_height=0.4, tick_thickness=0.2,)
    for obj in ticks_major: obj.parent = parent

    ticks_minor = add_tick_marks(min_val, max_val, major=False, minor_ticks=2, start_angle=start_angle, sweep_angle=sweep_angle, location=location,tick_height=0.3, tick_thickness=0.2,)
    for obj in ticks_minor: obj.parent = parent

    needle = create_needle(length=4.5, location=location, thickness=0.2)
    needle.parent = parent

    # Start needle at start_val
    t_start = (start_val - min_val) / (max_val - min_val)
    angle_start = math.radians(start_angle + t_start * sweep_angle)
    needle.rotation_mode = 'XYZ'
    needle.rotation_euler = (0, 0, angle_start)

    hub = create_hub(location=location, radius=0.3)
    hub.parent = parent

    if anim:
        animate_needle_to(needle, value=end_val, min_value=min_val, max_value=max_val,
                          start_angle=start_angle, sweep_angle=sweep_angle)

    return parent,targets,parents
