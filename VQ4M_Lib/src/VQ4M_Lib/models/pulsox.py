import math
import bpy 
from VQ4M_Lib.models.model_helpers.helpers import mm, relink, round_corners, get_edges,generate_cylinder_geometry, create_mesh_object, combine,add_bevel_apply,verts_to_edge_indices,vis_edges,ensure_weighted_bevel,set_edge_weights_from_vertices,set_edge_weights,vis_verts
from VQ4M_Lib.models.model_helpers import gen_materials 

#def mm(val): return val *  0.001  # mm -> m
import bpy

def mm(val): return val *  0.01  # mm -> m

def apply_image_fit_uv(
    obj: bpy.types.Object,
    img_path: str,
    material_name: str = "ImageFitMat",
    face_index: int | None = None,   # None => alle Faces, sonst nur diese Face
    roughness: float = 1.0,
    rotation_degrees: float = 0.0 
) -> bpy.types.Material:
    """
    Weist einem Mesh-Objekt ein Material mit Image-Texture zu und setzt die UVs so,
    dass das Bild vollständig sichtbar ist (Aspect-FIT ohne Abschneiden, ggf. mit Rändern).

    Parameters
    ----------
    obj : bpy.types.Object
        Mesh-Objekt (z.B. dein Cube).
    img_path : str
        Pfad zum Bild.
    material_name : str
        Name des zu erstellenden/zu verwendenden Materials.
    face_index : int | None
        Nur diese Face texturieren (Edit: Index aus obj.data.polygons). None = alle Faces.
    roughness : float
        Roughness des Principled BSDF (1.0 = matt).

    Returns
    -------
    bpy.types.Material
        Das verwendete/erstellte Material.
    """

    # --- Preconditions ---
    if obj is None or obj.type != 'MESH':
        raise TypeError("Bitte ein Mesh-Objekt übergeben (z.B. einen Cube).")

    # Bild laden/holen
    try:
        img = bpy.data.images.load(img_path)
    except RuntimeError:
        # Falls bereits geladen
        img = bpy.data.images.get(bpy.path.basename(img_path))
        if img is None:
            raise

    # --- Material + Nodes ---
    mat = bpy.data.materials.get(material_name) or bpy.data.materials.new(material_name)
    mat.use_nodes = True
    nt = mat.node_tree

    # Nodebaum sauber neu aufbauen
    for n in list(nt.nodes):
        nt.nodes.remove(n)

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tex  = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.extension = 'CLIP'  # keine Wiederholung, kein Abschneiden durch Tiling
    bsdf.inputs["Roughness"].default_value = roughness

    # Links
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    # Material dem Objekt zuweisen (als Slot 0, wenn leer)
    if not obj.data.materials:
        obj.data.materials.append(mat)
    else:
        # Falls nur eine Face gemappt werden soll, Material zusätzlich hinzufügen
        if face_index is not None and mat.name not in [m.name for m in obj.data.materials]:
            obj.data.materials.append(mat)
        else:
            obj.data.materials[0] = mat

    # --- UV Layer vorbereiten ---
    me = obj.data
    if not me.uv_layers:
        me.uv_layers.new(name="ImageFit")
    me.uv_layers.active = me.uv_layers[0]
    uv_layer = me.uv_layers.active.data

    # --- Aspect-FIT Rechteck in [0..1] berechnen ---
    w, h = img.size[:]
    aspect = w / h if h != 0 else 1.0

    u_scale = 1.0
    v_scale = 1.0
    u_off   = 0.0
    v_off   = 0.0

    if aspect >= 1.0:
        # Bild breiter -> Balken oben/unten
        v_scale = 1.0 / aspect
        v_off = (1.0 - v_scale) * 0.5
    else:
        # Bild höher -> Balken links/rechts
        u_scale = aspect
        u_off = (1.0 - u_scale) * 0.5

    # UV-Quad (CCW)
    base_uvs = [
        (u_off,            v_off),              # unten links
        (u_off+u_scale,    v_off),              # unten rechts
        (u_off+u_scale,    v_off+v_scale),      # oben rechts
        (u_off,            v_off+v_scale),      # oben links
    ]


    rot = rotation_degrees % 360
    if rot != 0.0:
        ang = math.radians(rot)
        c, s = math.cos(ang), math.sin(ang)
        rotated_uvs = []
        for (u, v) in base_uvs:
            # zum Zentrum
            u0, v0 = u - 0.5, v - 0.5
            # Rotation im Uhrzeigersinn: (u',v') = (u0*c + v0*s, -u0*s + v0*c)
            # (entspricht Standard-Rotation mit vertauschter v-Achse)
            ur = u0 * c + v0 * s
            vr = -u0 * s + v0 * c
            rotated_uvs.append((ur + 0.5, vr + 0.5))
        uvs = rotated_uvs
    else:
        uvs = base_uvs

    # --- UVs schreiben ---
    # Optional: nur eine Face mappen
    polys = me.polygons if face_index is None else [me.polygons[face_index]]

    for poly in polys:
        for i in range(poly.loop_total):
            uv_layer[poly.loop_start + i].uv = uvs[i % 4]

    me.update()

    # Falls nur eine Face gemappt werden soll: Materialindex dieser Face setzen
    if face_index is not None:
        # sicherstellen, dass Material im Objekt ist
        try:
            mat_index = [m.name for m in obj.data.materials].index(mat.name)
        except ValueError:
            obj.data.materials.append(mat)
            mat_index = len(obj.data.materials) - 1

        me.polygons[face_index].material_index = mat_index

    return mat


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
    max_midX = max(x.x for x, _ in mid_edges)
    min_midX = min(x.x for x, _ in mid_edges)
    max_midZ= max(x.z for x, _ in mid_edges)
    min_midZ= min(x.z for x, _ in mid_edges)

    edges_indices = [i for y, i in mid_edges if (abs(y.x - min_midX) < 1e-8 or abs(y.x - max_midX) < 1e-8) and not (abs(y.z - min_midZ) < 1e-8 or abs(y.z - max_midZ) < 1e-8)]
    
    ensure_weighted_bevel(obj, width, segments=200, profile=0.7, name="corner_roundover",use_clamp_overlap=False)
    set_edge_weights(obj,edges_indices)  
    return edges_indices


def create_pulsOX(width,depth,hight,screen_widht,screen_hight,location,asset_path=""):
    width = mm(width)
    depth = mm(depth)
    hight = mm(hight)
    screen_widht = mm(screen_widht)
    screen_hight = mm(screen_hight)

    x,y,z = location
    bpy.ops.mesh.primitive_cube_add(size=1,location=(x-mm(3),y,z+hight/3))
    base_upper = bpy.context.active_object
    base_upper.name = "base_upper"
    base_upper.scale = (width, depth, hight/1.5)
    round_over(base_upper)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    base_upper.rotation_euler=(0,math.radians(-10),0)
    

    # upper anlegen
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x - mm(6), y, z + hight/3 + (hight/1.5)/2 - mm(0.8)))
    upper = bpy.context.active_object
    upper.name = "upper"
    upper.scale = (width - mm(10), depth - mm(10), mm(1))
    round_over(upper, width=mm(20))
    upper.rotation_euler = (0, math.radians(-10), 0)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

 
    # screen_cut anlegen
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + width/2 - screen_widht/2 - mm(13), y, z + hight/3 + (hight/1.5)/2))
    screen_cut = bpy.context.active_object
    screen_cut.name = "screen_cut"
    screen_cut.scale = (screen_widht, screen_hight, mm(6))
    screen_cut.rotation_euler = (0, math.radians(-10), 0)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    
    # Boolean an upper hinzufügen
    mod1 = base_upper.modifiers.new(name="cutter_prep_screen", type='BOOLEAN')
    mod1.operation = 'DIFFERENCE'
    mod1.solver = 'EXACT'
    mod1.object = screen_cut
    # SICHERSTELLEN: upper ist aktiv, dann Modifier anwenden
    bpy.context.view_layer.objects.active = base_upper
    base_upper.select_set(True)
    screen_cut.select_set(False)
    bpy.ops.object.modifier_apply(modifier=mod1.name)
    
    mod2 = upper.modifiers.new(name="cutter_prep_screen_cover", type='BOOLEAN')
    mod2.operation = 'DIFFERENCE'
    mod2.solver = 'EXACT'
    mod2.object = screen_cut
    bpy.context.view_layer.objects.active = upper
    upper.select_set(True)
    screen_cut.select_set(False)
    bpy.ops.object.modifier_apply(modifier=mod2.name)
    # Jetzt darf der Cutter weg
    bpy.data.objects.remove(screen_cut, do_unlink=True)

    # screen_cut anlegen
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + width/2 - screen_widht/2 - mm(13), y, z + hight/3 + (hight/1.5)/2+mm(2))) #set to plus 1 mm if used with glass
    screen_img = bpy.context.active_object
    screen_img.name = "screen_img"
    screen_img.scale = (screen_widht, screen_hight, mm(2))
    screen_img.rotation_euler = (0, math.radians(-10), 0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    
    # bpy.ops.mesh.primitive_cube_add(size=1, location=(x + width/2 - screen_widht/2 - mm(13), y, z + hight/3 + (hight/1.5)/2+mm(2.3)))
    # screen_glass = bpy.context.active_object
    # screen_glass.name = "screen_glass"
    # screen_glass.scale = (screen_widht, screen_hight, mm(1))
    # screen_glass.rotation_euler = (0, math.radians(-10), 0)
    # bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    bpy.ops.mesh.primitive_cube_add(size=1,location=(x,y,z-hight/2))
    base_lower = bpy.context.active_object
    base_lower.name = "base_lower"
    base_lower.scale = (width, depth, hight/2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    round_over(base_lower)

    bpy.ops.mesh.primitive_cylinder_add(vertices=200,radius=mm(20), depth=depth+mm(1), location=(x-mm(15), y, z))
    piviot = bpy.context.active_object
    piviot.rotation_euler.x = math.radians(90)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    
    
    bpy.ops.mesh.primitive_cylinder_add(vertices=200,radius=mm(10), depth=mm(15), location=(x-mm(30), y, z+hight/3+mm(3.5)))
    Button = bpy.context.active_object
    Button.rotation_euler.y = math.radians(-10)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    gen_materials.assign_single_material(base_upper,gen_materials.pulsOx_body())
    gen_materials.assign_single_material(base_lower,gen_materials.pulsOx_body())
    gen_materials.assign_single_material(upper,gen_materials.pulsOx_screen_cover())
    gen_materials.add_image(screen_img,gen_materials.PulsOx_screenImg(asset_path),rotation_degrees=180)
    #gen_materials.assign_single_material(screen_glass,gen_materials.PulsOx_screen())



    return screen_img

