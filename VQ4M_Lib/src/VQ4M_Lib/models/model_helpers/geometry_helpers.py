import bpy
from math import radians
from VQ4M_Lib.models.model_helpers.helpers import mm, relink, round_corners, generate_cylinder_geometry, create_mesh_object, combine,add_bevel_apply
import math

def make_button_round(name, x, z, y, mat, radius_mm,col_ui, h):
    r = mm(radius_mm)
    y = y + mm(1)
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, location=(x, y, z))
    b = bpy.context.active_object
    b.name = name
    b.rotation_euler.x = radians(90)
    b.data.materials.append(mat)
    relink(b, col_ui)
    return b




def make_button_pill(name, x, z, y, mat, radius_mm, length_mm, col_ui, h=None):
    r = mm(radius_mm)
    h = h or r*2
    length = mm(length_mm)  # total length of pill
    y = y+mm(1)

    # Compute box length (subtract two semi-circles)
    box_length = length - 2 * r

    # Create center box
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, z))
    center = bpy.context.active_object
    center.name = name + "_center"
    center.scale = (box_length , r*2 ,h)
    center.rotation_euler.x = radians(90)

    # Create left rounded end
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, location=(x - box_length / 2, y, z))
    left_cap = bpy.context.active_object
    left_cap.name = name + "_cap_L"
    left_cap.rotation_euler.x = radians(90)

    # Create right rounded end
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, location=(x + box_length / 2, y, z))
    right_cap = bpy.context.active_object
    right_cap.name = name + "_cap_R"
    right_cap.rotation_euler.x = radians(90)

    # Join parts into one mesh
    bpy.context.view_layer.objects.active = center
    for part in [left_cap, right_cap]:
        part.select_set(True)
    center.select_set(True)
    bpy.ops.object.join()

    pill = bpy.context.active_object
    pill.name = name
    pill.data.materials.append(mat)
    relink(pill, col_ui)

    return pill


def make_spo2_connector(cable_len=mm(20),sp_con_r= mm(12),sp_con_h = mm(110),ports_x=0,y = 0, sp_vertices=128,col_ui=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=sp_vertices, radius=sp_con_r+mm(2), depth=mm(3), location=(ports_x, y, sp_con_h))
    sp_con_b = bpy.context.active_object
    sp_con_b.rotation_euler.x = radians(90)

    sp_con_s_d = mm(20)
    bpy.ops.mesh.primitive_cylinder_add(vertices=sp_vertices,radius=sp_con_r, depth=sp_con_s_d, location=(ports_x, sp_con_b.location.y+sp_con_s_d/2, sp_con_h))
    sp_con_s = bpy.context.active_object
    sp_con_s.rotation_euler.x = radians(90)


    cutt_offset=mm(6.5)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(ports_x-sp_con_r/2-cutt_offset,sp_con_b.location.y+sp_con_s_d/2, sp_con_h))
    sp_con_s_cut1 = bpy.context.active_object
    sp_con_s_cut1.scale = (mm(3), sp_con_s_d-mm(6),  mm(30))

    bool_mod = sp_con_s.modifiers.new("sp_con_cut", 'BOOLEAN')
    bool_mod.operation = 'DIFFERENCE'
    bool_mod.solver    = 'EXACT'
    bool_mod.object    = sp_con_s_cut1
    bpy.context.view_layer.objects.active = sp_con_s
    bpy.ops.object.modifier_apply(modifier=bool_mod.name)
    bpy.data.objects.remove(sp_con_s_cut1, do_unlink=True)

    bpy.ops.mesh.primitive_cube_add(size=1, location=(ports_x+sp_con_r/2+cutt_offset,sp_con_b.location.y+sp_con_s_d/2, sp_con_h))
    sp_con_s_cut2 = bpy.context.active_object
    sp_con_s_cut2.scale = (mm(3), sp_con_s_d-mm(6),  mm(30))

    bool_mod = sp_con_s.modifiers.new("sp_con_cut", 'BOOLEAN')
    bool_mod.operation = 'DIFFERENCE'
    bool_mod.solver    = 'EXACT'
    bool_mod.object    = sp_con_s_cut2
    bpy.context.view_layer.objects.active = sp_con_s
    bpy.ops.object.modifier_apply(modifier=bool_mod.name)
    bpy.data.objects.remove(sp_con_s_cut2, do_unlink=True)

    bpy.ops.mesh.primitive_cylinder_add(vertices=sp_vertices,radius=sp_con_r+mm(1), depth=mm(2), location=(ports_x, sp_con_s.location.y+sp_con_s_d/2, sp_con_h))
    sp_con_s_cap = bpy.context.active_object
    sp_con_s_cap.rotation_euler.x = radians(90)
    add_bevel_apply(sp_con_s_cap, mm(20), segments=40, profile=0.6, name="BevelTmp")


    bpy.ops.mesh.primitive_cylinder_add(vertices=sp_vertices,radius=mm(2), depth=cable_len, location=(ports_x+sp_con_r+cable_len/2-mm(2), sp_con_s_cap.location.y-mm(1), sp_con_h+mm(3)))
    sp_con_cable_1 = bpy.context.active_object
    sp_con_cable_1.rotation_euler.x = radians(90)
    sp_con_cable_1.rotation_euler.z = radians(90)

    bpy.ops.mesh.primitive_cylinder_add(vertices=sp_vertices,radius=mm(2), depth=cable_len, location=(ports_x+sp_con_r+cable_len/2-mm(2), sp_con_s_cap.location.y-mm(1), sp_con_h-mm(3)))
    sp_con_cable_2 = bpy.context.active_object
    sp_con_cable_2.rotation_euler.x = radians(90)
    sp_con_cable_2.rotation_euler.z = radians(90)

    bpy.ops.mesh.primitive_cube_add(size=1, location=(ports_x+sp_con_r+cable_len/2-mm(2), sp_con_s_cap.location.y-mm(1), sp_con_h))
    sp_con_cable = bpy.context.active_object
    sp_con_cable.scale = (cable_len,mm(4),mm(6))

    combine(sp_con_cable_1,sp_con_cable)
    combine(sp_con_cable_2,sp_con_cable)
    combine(sp_con_cable,sp_con_s_cap)
    combine(sp_con_b,sp_con_s)
    combine(sp_con_s_cap,sp_con_s)
    sp_con_s.name="Spo2_connector"
    relink(sp_con_s,col_ui)
    return sp_con_s



def set_active(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

# --- 1) Quad-Pyramide entlang Y (spitz zu +Y) ---
def make_quad_pyramid_y(
    x, y, z,
    base_width,    # Ausdehnung in X an der Basis (Y-)
    base_depth,    # Ausdehnung in Z an der Basis (Y-)
    length_y,      # Länge entlang Y (Basis -> Spitze/Top)
    top_width,     # Ausdehnung in X am Top (Y+). 0 => echte Spitze
    top_depth,     # Ausdehnung in Z am Top (Y+). 0 => echte Spitze
    name="quad_pyramid_y",
    inverted=False
):
    bx = base_width * 0.5
    bz = base_depth * 0.5
    tx = top_width  * 0.5
    tz = top_depth  * 0.5

    y_back  = y - length_y * 0.5   # Basis (Y-)
    y_front = y + length_y * 0.5   # Top/Spitze (Y+)
    if inverted:
        y_back, y_front = y_front, y_back   
    # Basis-Quad (Y-)
    b0 = (x - bx, y_back, z + bz)
    b1 = (x + bx, y_back, z + bz)
    b2 = (x + bx, y_back, z - bz)
    b3 = (x - bx, y_back, z - bz)

    verts = [b0, b1, b2, b3]
    faces = [(0, 1, 2, 3)]  # Basis

    if top_width == 0 and top_depth == 0:
        # Spitze
        apex = (x, y_front, z)
        verts += [apex]
        faces += [
            (0, 4, 1),
            (1, 4, 2),
            (2, 4, 3),
            (3, 4, 0),
        ]
    else:
        # Top-Quad
        t0 = (x - tx, y_front, z + tz)
        t1 = (x + tx, y_front, z + tz)
        t2 = (x + tx, y_front, z - tz)
        t3 = (x - tx, y_front, z - tz)
        base_idx = len(verts)
        verts += [t0, t1, t2, t3]
        # Seiten + Top
        faces += [
            (base_idx+0, base_idx+1, base_idx+2, base_idx+3),  # Top
            (0, 3, base_idx+3, base_idx+0),   # X- Seite
            (1, base_idx+1, base_idx+2, 2),   # X+ Seite
            (0, base_idx+0, base_idx+1, 1),   # Z+ Seite
            (3, 2, base_idx+2, base_idx+3),   # Z- Seite
        ]

    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update(calc_edges=True)

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj






def make_quarter_donut_trapezoid(
    r_corner=0.20,                 # äußerer Radius (unten)
    bottom_wall=0.02,              # Wandstärke unten (y=0)
    top_wall=0.02,                 # Wandstärke oben  (y=height)
    location=(0,0,0),              # Mittelpunkt (Drehachse) im Raum
    height=0.03,                   # Profilhöhe in +Y
    angle_deg=90,                  # Drehwinkel um Y (Viertelkreis)
    steps=64,                      # Auflösung entlang der Drehung
    merge_threshold=1e-5,          # Verschmelz-Toleranz für Screw
    name="QuarterDonutTrapezoid"
):
    # --- Checks ---
    if bottom_wall <= 0 or top_wall <= 0:
        raise ValueError("bottom_wall und top_wall müssen > 0 sein.")
    if r_corner <= 0:
        raise ValueError("r_corner muss > 0 sein.")
    r_in_bottom = r_corner - bottom_wall
    if r_in_bottom <= 0:
        raise ValueError("bottom_wall muss kleiner als r_corner sein.")
    # Symmetrische Verteilung der Wandänderung um die Mittenlinie
    # delta > 0 bedeutet oben dünner, delta < 0 bedeutet oben dicker.
    delta = (bottom_wall - top_wall) / 2.0
    r_out_top = r_corner - delta
    r_in_top  = r_out_top - top_wall
    if r_in_top <= 0:
        raise ValueError("top_wall ist zu groß (innerer Radius oben <= 0).")

    # --- 2D-Profil (XY-Ebene, Z=0); Y ist später Screw-Achse ---
    # Reihenfolge der Punkte so, dass Normalen nach außen zeigen
    verts_xy = [
        (r_corner,        0.0,    0.0),  # 0: unten außen
        (r_in_bottom,     0.0,    0.0),  # 1: unten innen
        (r_in_top,        height, 0.0),  # 2: oben innen
        (r_out_top,       height, 0.0),  # 3: oben außen
    ]
    faces = [(0, 1, 2, 3)]

    # --- Mesh + Objekt ---
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts_xy, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    # Drehachse Y geht durch den Objektursprung -> Objekt an Zielposition setzen
    obj.location = location
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # --- Screw-Modifier (Rotation um Y) ---
    mod = obj.modifiers.new(name="Screw", type='SCREW')
    mod.axis = 'Y'
    mod.angle = math.radians(angle_deg)
    mod.steps = max(3, int(steps))
    mod.render_steps = max(3, int(steps))
    mod.use_merge_vertices = True
    mod.merge_threshold = merge_threshold
    mod.use_smooth_shade = True

    # Anwenden (falls du’s prozedural halten willst: Zeile auskommentieren)
    bpy.ops.object.modifier_apply(modifier=mod.name)


    return obj
