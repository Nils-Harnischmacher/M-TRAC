import bpy
import math
import os
from VQ4M_Lib import general
from pathlib import Path
import random
PROJECT_ROOT = Path(__file__).resolve().parents[5]


#helpers
def teximage_nodes_from_material(mat: bpy.types.Material):
    mat.use_nodes = True
    return [n for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE']

def first_teximage_size(mat: bpy.types.Material):
    nodes = teximage_nodes_from_material(mat)
    if not nodes:
        return None
    tex = nodes[0]
    img = tex.image
    if not img:
        return None
    # Größe (Pixel)
    if img.source == 'GENERATED':
        return img.generated_width, img.generated_height
    if not img.has_data:
        try: img.reload()
        except: pass
    w, h = img.size[:]
    return int(w), int(h)
# Application functions

def add_image(obj: bpy.types.Object,material,face_index: int | None = None, rotation_degrees = 0):
        # --- Preconditions ---
    if obj is None or obj.type != 'MESH':
        raise TypeError("Bitte ein Mesh-Objekt übergeben (z.B. einen Cube).")
    mat = material
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

    w, h = first_teximage_size(mat)
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





def assign_single_material(obj: bpy.types.Object, material: bpy.types.Material | str, apply_to_all_faces: bool = True):
    """
    Entfernt alle vorhandenen Materials vom Mesh-Objekt und weist genau EIN neues Material zu.

    Parameters
    ----------
    obj : bpy.types.Object
        Zielobjekt (MESH).
    material : bpy.types.Material | str
        Material-Objekt oder Materialname. Wenn der Name nicht existiert, wird ein neues Material erstellt.
    apply_to_all_faces : bool
        Setzt alle polygon.material_index = 0, damit das Material wirklich auf allen Faces liegt.
    """
    if obj is None or obj.type != 'MESH':
        raise TypeError("Bitte ein Mesh-Objekt übergeben.")

    # Material-Objekt ermitteln/erstellen
    if isinstance(material, str):
        mat = bpy.data.materials.get(material)
        if mat is None:
            mat = bpy.data.materials.new(material)
    elif isinstance(material, bpy.types.Material):
        mat = material
    else:
        raise TypeError("`material` muss ein Material oder Materialname (str) sein.")

    # Sicherstellen, dass wir in Object Mode sind, um Slots zu ändern
    prev_mode = None
    if obj.mode != 'OBJECT':
        prev_mode = obj.mode
        bpy.ops.object.mode_set(mode='OBJECT')

    # Alle bisherigen Materialslots entfernen
    obj.data.materials.clear()

    # Das neue Material zuweisen (einziger Slot)
    obj.data.materials.append(mat)
    obj.active_material = mat

    # Optional: alle Faces auf Slot 0 setzen
    if apply_to_all_faces and obj.data.polygons:
        for poly in obj.data.polygons:
            poly.material_index = 0

    # Ursprungsmodus wiederherstellen
    if prev_mode is not None:
        bpy.ops.object.mode_set(mode=prev_mode)

    return mat


# Materials 

def hand_mat(): 
    # --- Material + Nodes ---
    mat = bpy.data.materials.get("hand") or bpy.data.materials.new("hand")
    mat.use_nodes = True
    nt = mat.node_tree

    for n in list(nt.nodes):
        nt.nodes.remove(n)

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    displacment = nt.nodes.new("ShaderNodeDisplacement")
    Normalmap = nt.nodes.new("ShaderNodeNormalMap")
    BaseColorTex  = nt.nodes.new("ShaderNodeTexImage")
    IORTex  = nt.nodes.new("ShaderNodeTexImage")
    RoughnessTex  = nt.nodes.new("ShaderNodeTexImage")
    DisplacementTex  = nt.nodes.new("ShaderNodeTexImage")
    NormalTex  = nt.nodes.new("ShaderNodeTexImage")
    Mapping = nt.nodes.new("ShaderNodeMapping")
    TextureCords = nt.nodes.new("ShaderNodeTexCoord")

    
    BaseColorTex.image = bpy.data.images.load(str(PROJECT_ROOT)+"/assets/textures/hand/038F_05SET_04SHOT_DIFFUSE.png")
    IORTex.image = bpy.data.images.load(str(PROJECT_ROOT)+"/assets/textures/hand/038F_05SET_04SHOT_SPECULAR.png") 
    RoughnessTex.image = bpy.data.images.load(str(PROJECT_ROOT)+"/assets/textures/hand/038F_05SET_04SHOT_ROUGHNESS.png") 
    DisplacementTex.image = bpy.data.images.load(str(PROJECT_ROOT)+"/assets/textures/hand/038F_05SET_04SHOT_DISPLACEMENT.png") 
    NormalTex.image = bpy.data.images.load(str(PROJECT_ROOT)+"/assets/textures/hand/038F_05SET_04SHOT_NORMAL.png") 

    #Settings
    IORTex.image.colorspace_settings.name = "Non-Color"
    RoughnessTex.image.colorspace_settings.name = "Non-Color"
    DisplacementTex.image.colorspace_settings.name = "Non-Color"
    NormalTex.image.colorspace_settings.name = "Non-Color"


    # Links
    #start Links
    nt.links.new(TextureCords.outputs["UV"], Mapping.inputs["Vector"])

    nt.links.new(Mapping.outputs["Vector"], BaseColorTex.inputs["Vector"])
    nt.links.new(Mapping.outputs["Vector"], IORTex.inputs["Vector"])
    nt.links.new(Mapping.outputs["Vector"], RoughnessTex.inputs["Vector"])
    nt.links.new(Mapping.outputs["Vector"], DisplacementTex.inputs["Vector"])
    nt.links.new(Mapping.outputs["Vector"], NormalTex.inputs["Vector"])


    

    #intermediat links
    nt.links.new(NormalTex.outputs["Color"], Normalmap.inputs["Color"])
    nt.links.new(DisplacementTex.outputs["Color"], displacment.inputs["Height"])

    #bsdf links
    nt.links.new(BaseColorTex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(RoughnessTex.outputs["Color"], bsdf.inputs["Roughness"])
    nt.links.new(IORTex.outputs["Color"], bsdf.inputs["Specular IOR Level"])
    nt.links.new(Normalmap.outputs["Normal"], bsdf.inputs["Normal"])
    
    #output links
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    nt.links.new(displacment.outputs["Displacement"], out.inputs["Displacement"])

    return mat

def pulsOx_body():
    mat = bpy.data.materials.get("pulsOxBody") or bpy.data.materials.new("pulsOxBody")
    mat.use_nodes = True
    nt = mat.node_tree

    for n in list(nt.nodes):
        nt.nodes.remove(n)

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")

    # Basis
    bsdf.inputs["Base Color"].default_value = (0.95, 0.95, 0.93, 1.0)

    # Mikro-Glanz
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Roughness"].default_value = 0.35
    bsdf.inputs["Diffuse Roughness"].default_value = 0.10

    # Optik
    bsdf.inputs["IOR"].default_value = 1.45
    bsdf.inputs["Alpha"].default_value = 1.0

    # SSS – leichtes, milchiges Plastik
    bsdf.inputs["Subsurface Weight"].default_value = 0.05
    bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.8, 0.6)
    bsdf.inputs["Subsurface Scale"].default_value = 1.0
    #bsdf.inputs["Subsurface IOR"].default_value = 1.40
    bsdf.inputs["Subsurface Anisotropy"].default_value = 0.0

    # Specular
    bsdf.inputs["Specular IOR Level"].default_value = 1.0
    bsdf.inputs["Specular Tint"].default_value = (0, 0, 0, 0)

    # Keine Anisotropie
    bsdf.inputs["Anisotropic"].default_value = 0.0
    bsdf.inputs["Anisotropic Rotation"].default_value = 0.0

    # Kein Transmission-Glas
    bsdf.inputs["Transmission Weight"].default_value = 0.0

    # Leichter „Lack“-Überzug
    bsdf.inputs["Coat Weight"].default_value = 0.15
    bsdf.inputs["Coat Roughness"].default_value = 0.05
    bsdf.inputs["Coat IOR"].default_value = 1.50
    bsdf.inputs["Coat Tint"].default_value = (1.0, 1.0, 1.0, 1.0)

    # Kein Sheen / Emission / Thin Film
    bsdf.inputs["Sheen Weight"].default_value = 0.0
    bsdf.inputs["Sheen Roughness"].default_value = 0.0
    bsdf.inputs["Sheen Tint"].default_value = (1.0, 1.0, 1.0, 1.0)
    bsdf.inputs["Emission Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    bsdf.inputs["Emission Strength"].default_value = 0.0
    bsdf.inputs["Thin Film Thickness"].default_value = 0.0
    bsdf.inputs["Thin Film IOR"].default_value = 1.0

    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat

def pulsOx_screen_cover():
    mat = bpy.data.materials.get("pulsOxScreen_cover") or bpy.data.materials.new("pulsOxScreen_cover")
    mat.use_nodes = True
    nt = mat.node_tree

    for n in list(nt.nodes):
        nt.nodes.remove(n)

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    # Basis
    bsdf.inputs["Base Color"].default_value = (0.03, 0.03, 0.03, 1.0)

    # Spiegel / Glanz
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Roughness"].default_value = 0.05
    bsdf.inputs["Diffuse Roughness"].default_value = 0.0
    bsdf.inputs["Specular IOR Level"].default_value = 1.0
    bsdf.inputs["Specular Tint"].default_value = (0, 0, 0, 0)

    # Optik / Glas
    bsdf.inputs["IOR"].default_value = 1.49
    bsdf.inputs["Transmission Weight"].default_value = 0.9

    # Clearcoat (Lack-Schicht)
    bsdf.inputs["Coat Weight"].default_value = 0.2
    bsdf.inputs["Coat Roughness"].default_value = 0.03
    bsdf.inputs["Coat IOR"].default_value = 1.5
    bsdf.inputs["Coat Tint"].default_value = (1.0, 1.0, 1.0, 1.0)

    # Sheen (nicht nötig)
    bsdf.inputs["Sheen Weight"].default_value = 0.0
    bsdf.inputs["Sheen Roughness"].default_value = 0.0

    # SSS / Emission / Thin Film (aus)
    bsdf.inputs["Subsurface Weight"].default_value = 0.0
    bsdf.inputs["Emission Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    bsdf.inputs["Emission Strength"].default_value = 0.0
    bsdf.inputs["Thin Film Thickness"].default_value = 0.0
    bsdf.inputs["Thin Film IOR"].default_value = 1.0
    try:
        mat.blend_method = 'BLEND'          # oder 'HASHED'
        mat.shadow_method = 'HASHED'
        mat.use_screen_refraction = True
        mat.refraction_depth = 0.2
        bsdf.inputs["Alpha"].default_value = 1.0  # Transmission steuert „Durchsicht“
    except Exception:
        pass


    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    return mat


def PulsOx_screenImg(asset_path=""):
    if asset_path == "":
        asset_folder= str(PROJECT_ROOT)+"/assets/content_pulsOX/"
        paths = general.list_files_by_extension(asset_folder,".png")
        img_path = paths[random.randint(0,len(paths)-1)]
    else:
        img_path = asset_path
    img = bpy.data.images.load(img_path)
    mat = bpy.data.materials.get("screen_image") or bpy.data.materials.new("screen_image")
    mat.use_nodes = True
    nt = mat.node_tree

    # Nodebaum sauber neu aufbauen
    for n in list(nt.nodes):
        nt.nodes.remove(n)

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    emit = nt.nodes.new("ShaderNodeEmission")
    tex  = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.extension = 'CLIP'  # keine Wiederholung, kein Abschneiden durch Tiling
    emit.inputs["Strength"].default_value = 6.0
    nt.links.new(tex.outputs["Color"], emit.inputs["Color"])
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat

def PulsOx_screen():
    mat = bpy.data.materials.get("Plexiglass_Clear") or bpy.data.materials.new("Plexiglass_Clear")
    mat.use_nodes = True
    nt = mat.node_tree

    # Nodebaum säubern
    for n in list(nt.nodes):
        nt.nodes.remove(n)

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (-200, 0)

    # Parameter für durchsichtiges Plexiglas
    bsdf.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Roughness"].default_value = 0.03
    bsdf.inputs["Diffuse Roughness"].default_value = 0.0
    bsdf.inputs["IOR"].default_value = 1.49
    bsdf.inputs["Transmission Weight"].default_value = 1.0
    bsdf.inputs["Specular IOR Level"].default_value = 1.0
    bsdf.inputs["Specular Tint"].default_value = (0.0,0.0,0.0,0.0)
    bsdf.inputs["Coat Weight"].default_value = 0.2
    bsdf.inputs["Coat Roughness"].default_value = 0.03
    bsdf.inputs["Coat IOR"].default_value = 1.5
    bsdf.inputs["Coat Tint"].default_value = (1.0, 1.0, 1.0, 1.0)
    bsdf.inputs["Alpha"].default_value = 1.0
    bsdf.inputs["Emission Strength"].default_value = 0.0

    # Verbinden
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    try:
        # Material-Einstellungen für Transparenz
        mat.blend_method = 'BLEND'
        mat.shadow_method = 'HASHED'
        mat.use_screen_refraction = True
        mat.refraction_depth = 0.3
    except AttributeError:
        pass

    return mat



def LP_body():
    mat = bpy.data.materials.get("LP_body") or bpy.data.materials.new("LP_body")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (-200, 0)

    # Parameter für durchsichtiges Plexiglas
    bsdf.inputs["Base Color"].default_value = (0.3, 0.3, 0.3, 1.0)
    # Mikro-Glanz
    bsdf.inputs["Metallic"].default_value = 0.15
    bsdf.inputs["Roughness"].default_value = 0.5
    bsdf.inputs["Diffuse Roughness"].default_value = 0.10

    # Optik
    bsdf.inputs["IOR"].default_value = 1.45
    bsdf.inputs["Alpha"].default_value = 1.0

    # SSS – leichtes, milchiges Plastik
    bsdf.inputs["Subsurface Weight"].default_value = 0.05
    bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.8, 0.6)
    bsdf.inputs["Subsurface Scale"].default_value = 1.0
    #bsdf.inputs["Subsurface IOR"].default_value = 1.40
    bsdf.inputs["Subsurface Anisotropy"].default_value = 0.0

    # Specular
    bsdf.inputs["Specular IOR Level"].default_value = 1.0
    bsdf.inputs["Specular Tint"].default_value = (0, 0, 0, 0)

    # Keine Anisotropie
    bsdf.inputs["Anisotropic"].default_value = 0.0
    bsdf.inputs["Anisotropic Rotation"].default_value = 0.0

    # Kein Transmission-Glas
    bsdf.inputs["Transmission Weight"].default_value = 0.0

    # Leichter „Lack“-Überzug
    bsdf.inputs["Coat Weight"].default_value = 0.15
    bsdf.inputs["Coat Roughness"].default_value = 0.05
    bsdf.inputs["Coat IOR"].default_value = 1.50
    bsdf.inputs["Coat Tint"].default_value = (1.0, 1.0, 1.0, 1.0)

    # Kein Sheen / Emission / Thin Film
    bsdf.inputs["Sheen Weight"].default_value = 0.0
    bsdf.inputs["Sheen Roughness"].default_value = 0.0
    bsdf.inputs["Sheen Tint"].default_value = (1.0, 1.0, 1.0, 1.0)
    bsdf.inputs["Emission Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    bsdf.inputs["Emission Strength"].default_value = 0.0
    bsdf.inputs["Thin Film Thickness"].default_value = 0.0
    bsdf.inputs["Thin Film IOR"].default_value = 1.0

    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat

def LP_bezel():
    mat = bpy.data.materials.get("LP_bezel") or bpy.data.materials.new("LP_bezel")
    mat.use_nodes = True
    nt = mat.node_tree

    for n in list(nt.nodes):
        nt.nodes.remove(n)

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
  
    # Basis
    bsdf.inputs["Base Color"].default_value = (0.065, 0.065, 0.065, 1.0)

    # Mikro-Glanz
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Roughness"].default_value = 0.35
    bsdf.inputs["Diffuse Roughness"].default_value = 0.10

    # Optik
    bsdf.inputs["IOR"].default_value = 1.45
    bsdf.inputs["Alpha"].default_value = 1.0

    # SSS – leichtes, milchiges Plastik
    bsdf.inputs["Subsurface Weight"].default_value = 0.05
    bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.8, 0.6)
    bsdf.inputs["Subsurface Scale"].default_value = 1.0
    #bsdf.inputs["Subsurface IOR"].default_value = 1.40
    bsdf.inputs["Subsurface Anisotropy"].default_value = 0.0

    # Specular
    bsdf.inputs["Specular IOR Level"].default_value = 1.0
    bsdf.inputs["Specular Tint"].default_value = (0, 0, 0, 0)

    # Keine Anisotropie
    bsdf.inputs["Anisotropic"].default_value = 0.0
    bsdf.inputs["Anisotropic Rotation"].default_value = 0.0

    # Kein Transmission-Glas
    bsdf.inputs["Transmission Weight"].default_value = 0.0

    # Leichter „Lack“-Überzug
    bsdf.inputs["Coat Weight"].default_value = 0.15
    bsdf.inputs["Coat Roughness"].default_value = 0.05
    bsdf.inputs["Coat IOR"].default_value = 1.50
    bsdf.inputs["Coat Tint"].default_value = (1.0, 1.0, 1.0, 1.0)

    # Kein Sheen / Emission / Thin Film
    bsdf.inputs["Sheen Weight"].default_value = 0.0
    bsdf.inputs["Sheen Roughness"].default_value = 0.0
    bsdf.inputs["Sheen Tint"].default_value = (1.0, 1.0, 1.0, 1.0)
    bsdf.inputs["Emission Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    bsdf.inputs["Emission Strength"].default_value = 0.0
    bsdf.inputs["Thin Film Thickness"].default_value = 0.0
    bsdf.inputs["Thin Film IOR"].default_value = 1.0

    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat

def LP_screen_img(asset_path=""):
    if asset_path == "":
        asset_folder= str(PROJECT_ROOT)+"/assets/content_patient_monitor/"
        paths = general.list_files_by_extension(asset_folder,".png")
        img_path = paths[random.randint(0,len(paths)-1)]
    else:
        img_path = asset_path
    img = bpy.data.images.load(img_path)
    mat = bpy.data.materials.get("screen_image") or bpy.data.materials.new("screen_image")
    mat.use_nodes = True
    nt = mat.node_tree

    # Nodebaum sauber neu aufbauen
    for n in list(nt.nodes):
        nt.nodes.remove(n)

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    emit = nt.nodes.new("ShaderNodeEmission")
    tex  = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.extension = 'CLIP'  # keine Wiederholung, kein Abschneiden durch Tiling
    emit.inputs["Strength"].default_value = 6.0
    nt.links.new(tex.outputs["Color"], emit.inputs["Color"])
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat



def LP_Pouches():
    mat = bpy.data.materials.get("LP_Pouches") or bpy.data.materials.new("LP_Pouches")
    mat.use_nodes = True
    nt = mat.node_tree

    for n in list(nt.nodes):
        nt.nodes.remove(n)

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")

    # Basis
    bsdf.inputs["Base Color"].default_value = (0, 0,0, 1.0)

    # Mikro-Glanz
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Roughness"].default_value = 0.9
    bsdf.inputs["Diffuse Roughness"].default_value = 0.10

    # # Optik
    # bsdf.inputs["IOR"].default_value = 1.45
    # bsdf.inputs["Alpha"].default_value = 1.0

    # # SSS – leichtes, milchiges Plastik
    # bsdf.inputs["Subsurface Weight"].default_value = 0.05
    # bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.8, 0.6)
    # bsdf.inputs["Subsurface Scale"].default_value = 1.0
    # #bsdf.inputs["Subsurface IOR"].default_value = 1.40
    # bsdf.inputs["Subsurface Anisotropy"].default_value = 0.0

    # # Specular
    # bsdf.inputs["Specular IOR Level"].default_value = 1.0
    # bsdf.inputs["Specular Tint"].default_value = (0, 0, 0, 0)

    # # Keine Anisotropie
    # bsdf.inputs["Anisotropic"].default_value = 0.0
    # bsdf.inputs["Anisotropic Rotation"].default_value = 0.0

    # # Kein Transmission-Glas
    # bsdf.inputs["Transmission Weight"].default_value = 0.0

    # # Leichter „Lack“-Überzug
    # bsdf.inputs["Coat Weight"].default_value = 0.15
    # bsdf.inputs["Coat Roughness"].default_value = 0.05
    # bsdf.inputs["Coat IOR"].default_value = 1.50
    # bsdf.inputs["Coat Tint"].default_value = (1.0, 1.0, 1.0, 1.0)

    # # Kein Sheen / Emission / Thin Film
    # bsdf.inputs["Sheen Weight"].default_value = 0.0
    # bsdf.inputs["Sheen Roughness"].default_value = 0.0
    # bsdf.inputs["Sheen Tint"].default_value = (1.0, 1.0, 1.0, 1.0)
    # bsdf.inputs["Emission Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    # bsdf.inputs["Emission Strength"].default_value = 0.0
    # bsdf.inputs["Thin Film Thickness"].default_value = 0.0
    # bsdf.inputs["Thin Film IOR"].default_value = 1.0

    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def Lp_leather_pouches():
    # --- Material + Nodes ---
    mat = bpy.data.materials.get("Lp_leather_pouches") or bpy.data.materials.new("Lp_leather_pouches")
    mat.use_nodes = True
    nt = mat.node_tree

    for n in list(nt.nodes):
        nt.nodes.remove(n)

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    Normalmap = nt.nodes.new("ShaderNodeNormalMap")
    RoughnessTex  = nt.nodes.new("ShaderNodeTexImage")
    NormalTex  = nt.nodes.new("ShaderNodeTexImage")
    Mapping = nt.nodes.new("ShaderNodeMapping")
    TextureCords = nt.nodes.new("ShaderNodeTexCoord")
    bsdf.inputs["Base Color"].default_value = (0, 0,0, 1.0)
    
    RoughnessTex.image = bpy.data.images.load(str(PROJECT_ROOT)+"/assets/textures/leather_white_4k.blend/textures/leather_white_rough_4k.exr") 
    NormalTex.image = bpy.data.images.load(str(PROJECT_ROOT)+"/assets/textures/leather_white_4k.blend/textures/leather_white_nor_gl_4k.exr") 

    #Settings
    RoughnessTex.image.colorspace_settings.name = "Non-Color"
    NormalTex.image.colorspace_settings.name = "Non-Color"


    # Links
    #start Links
    nt.links.new(TextureCords.outputs["UV"], Mapping.inputs["Vector"])

    nt.links.new(Mapping.outputs["Vector"], RoughnessTex.inputs["Vector"])
    nt.links.new(Mapping.outputs["Vector"], NormalTex.inputs["Vector"])


    

    #intermediat links
    nt.links.new(NormalTex.outputs["Color"], Normalmap.inputs["Color"])

    #bsdf links
    nt.links.new(RoughnessTex.outputs["Color"], bsdf.inputs["Roughness"])
    nt.links.new(Normalmap.outputs["Normal"], bsdf.inputs["Normal"])
    
    #output links
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat

def Lp_zipper():
    # --- Material + Nodes ---
    mat = bpy.data.materials.get("Lp_zipper") or bpy.data.materials.new("Lp_zipper")
    mat.use_nodes = True
    nt = mat.node_tree

    for n in list(nt.nodes):
        nt.nodes.remove(n)

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    Normalmap = nt.nodes.new("ShaderNodeNormalMap")
    RoughnessTex  = nt.nodes.new("ShaderNodeTexImage")
    NormalTex  = nt.nodes.new("ShaderNodeTexImage")
    Mapping = nt.nodes.new("ShaderNodeMapping")
    TextureCords = nt.nodes.new("ShaderNodeTexCoord")
    bsdf.inputs["Base Color"].default_value = (.1, 0.1,0.1, 1.0)

    # Mikro-Glanz
    bsdf.inputs["Metallic"].default_value = .8
    bsdf.inputs["Roughness"].default_value = 0.2
    bsdf.inputs["Diffuse Roughness"].default_value = 0.10
    
    RoughnessTex.image = bpy.data.images.load(str(PROJECT_ROOT)+"/assets/textures/leather_white_4k.blend/textures/leather_white_rough_4k.exr") 
    NormalTex.image = bpy.data.images.load(str(PROJECT_ROOT)+"/assets/textures/leather_white_4k.blend/textures/leather_white_nor_gl_4k.exr") 

    #Settings
    RoughnessTex.image.colorspace_settings.name = "Non-Color"
    NormalTex.image.colorspace_settings.name = "Non-Color"


    # Links
    #start Links
    nt.links.new(TextureCords.outputs["UV"], Mapping.inputs["Vector"])

    nt.links.new(Mapping.outputs["Vector"], RoughnessTex.inputs["Vector"])
    nt.links.new(Mapping.outputs["Vector"], NormalTex.inputs["Vector"])


    

    #intermediat links
    nt.links.new(NormalTex.outputs["Color"], Normalmap.inputs["Color"])

    #bsdf links
    nt.links.new(RoughnessTex.outputs["Color"], bsdf.inputs["Roughness"])
    nt.links.new(Normalmap.outputs["Normal"], bsdf.inputs["Normal"])
    
    #output links
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat

def wrap_image_on_cylinder(
    obj=None,
    image_path="",
    repeat_uv=(1.0, 1.0),      # tile count (U, V)
    rotation_deg=0.0,          # rotate texture around the cylinder (in degrees)
    offset_uv=(0.0, 0.0),      # shift texture (U, V)
    force_cylindrical_unwrap=False,
    material_name="Cyl_Image_Mat"
):
    """
    Wraps an image around a cylinder-like mesh using UVs.
    - obj: the object to texture (defaults to active object)
    - image_path: absolute or blend-file-relative path to the image
    - repeat_uv: tiles the image (U, V)
    - rotation_deg: rotation of the texture around the cylinder (Z in Mapping)
    - offset_uv: translation of the texture (U, V)
    - force_cylindrical_unwrap: run a cylindrical UV unwrap on the mesh
    - material_name: name for the created/reused material
    """
    if obj is None:
        obj = bpy.context.active_object
    if obj is None or obj.type != 'MESH':
        raise ValueError("Please select a mesh object or pass one via obj=...")

    # --- Load image ---
    if not image_path:
        raise ValueError("Please provide image_path to your texture file.")
    # Allow relative paths
    if not os.path.isabs(image_path):
        image_path = bpy.path.abspath(image_path)
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    img = bpy.data.images.load(image_path, check_existing=True)

    # --- Optionally: Cylindrical unwrap for clean seam/UVs ---
    if force_cylindrical_unwrap:
        # Make this object active
        bpy.context.view_layer.objects.active = obj
        # Enter Edit mode and select all faces
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')

        # Try to call cylinder_project; if context issues arise, fall back to smart_project
        try:
            bpy.ops.uv.cylinder_project(direction='ALIGN_TO_OBJECT')
        except Exception:
            bpy.ops.uv.smart_project(angle_limit=66, island_margin=0.02)

        bpy.ops.object.mode_set(mode='OBJECT')

    # --- Create or reuse a material with nodes ---
    mat = (bpy.data.materials.get(material_name) or 
           bpy.data.materials.new(material_name))
    mat.use_nodes = True
    nt = mat.node_tree

    # Clear default nodes except output
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(n)

    out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')

    # Create nodes
    tex_coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping   = nt.nodes.new("ShaderNodeMapping")
    img_tex   = nt.nodes.new("ShaderNodeTexImage")
    bsdf      = nt.nodes.new("ShaderNodeBsdfPrincipled")

    # Place nodes nicely
    tex_coord.location = (-1000, 0)
    mapping.location   = (-800, 0)
    img_tex.location   = (-600, 0)
    bsdf.location      = (-300, 0)
    out.location       = (-50, 0)

    # Configure nodes
    img_tex.image = img
    img_tex.extension = 'REPEAT'  # allow tiling

    # Mapping transforms (scale=tiling, rotation around Z, translation=offset)
    mapping.inputs['Scale'].default_value[0] = float(repeat_uv[0])
    mapping.inputs['Scale'].default_value[1] = float(repeat_uv[1])
    mapping.inputs['Rotation'].default_value[2] = math.radians(rotation_deg)
    mapping.inputs['Location'].default_value[0] = float(offset_uv[0])
    mapping.inputs['Location'].default_value[1] = float(offset_uv[1])

    # Wire nodes: UV -> Mapping -> Image -> Base Color
    nt.links.new(tex_coord.outputs['UV'], mapping.inputs['Vector'])
    nt.links.new(mapping.outputs['Vector'], img_tex.inputs['Vector'])
    nt.links.new(img_tex.outputs['Color'], bsdf.inputs['Base Color'])
    nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    # Assign material to object
    if mat.name not in [slot.material.name if slot.material else "" for slot in obj.material_slots]:
        if not obj.data.materials:
            obj.data.materials.append(mat)
        else:
            obj.data.materials[0] = mat

    return mat





def create_and_apply_material(
    obj,
    name="MyMaterial",
    base_color=(0.8, 0.8, 0.8),   # (R,G,B) in 0..1 or "#RRGGBB"/"#RRGGBBAA"
    metallic=0.0,
    roughness=0.5,
    texture_path=None,            # optional path to base-color texture
    replace_all_slots=True,
    emission_color=(0.0, 0.0, 0.0),  # RGB/RGBA or hex; set strength>0 to enable
    emission_strength=0.0
):
    def _ensure_object(o):
        if isinstance(o, str):
            oo = bpy.data.objects.get(o)
            if not oo:
                raise ValueError(f'Object named "{o}" not found.')
            return oo
        if not isinstance(o, bpy.types.Object):
            raise TypeError("obj must be a bpy.types.Object or an object name (str).")
        return o

    def _to_rgba(c):
        if isinstance(c, str):
            s = c.strip().lstrip("#")
            if len(s) not in (6, 8):
                raise ValueError('Hex color must be "#RRGGBB" or "#RRGGBBAA".')
            r = int(s[0:2], 16) / 255.0
            g = int(s[2:4], 16) / 255.0
            b = int(s[4:6], 16) / 255.0
            a = int(s[6:8], 16) / 255.0 if len(s) == 8 else 1.0
            return (r, g, b, a)
        vals = list(c)
        if len(vals) == 3: return (vals[0], vals[1], vals[2], 1.0)
        if len(vals) == 4: return tuple(vals[:4])
        raise TypeError("Color must be an RGB/RGBA tuple or a hex string.")

    def _get_or_create_material(mat_name):
        mat = bpy.data.materials.get(mat_name)
        if mat is None:
            mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        return mat

    def _get_nodes(mat):
        nt = mat.node_tree
        nodes, links = nt.nodes, nt.links
        out = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)
        if out is None:
            out = nodes.new("ShaderNodeOutputMaterial")
            out.location = (600, 0)
        bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if bsdf is None:
            bsdf = nodes.new("ShaderNodeBsdfPrincipled")
            bsdf.location = (200, 0)
        # ensure something is connected to output
        if not any(l.to_node == out and l.to_socket.name == "Surface" for l in links):
            links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
        return nt, nodes, links, out, bsdf

    def _link_to_output(links, node_out, output_node, socket_name="Surface"):
        # Clear existing links to output surface
        for l in [l for l in list(links) if l.to_node == output_node and l.to_socket.name == socket_name]:
            links.remove(l)
        links.new(node_out, output_node.inputs[socket_name])

    # --- main ---
    obj = _ensure_object(obj)
    rgba_base = _to_rgba(base_color)
    rgba_emit = _to_rgba(emission_color)

    mat = _get_or_create_material(name)
    nt, nodes, links, out, bsdf = _get_nodes(mat)

    # Base params
    bsdf.inputs["Base Color"].default_value = rgba_base
    bsdf.inputs["Metallic"].default_value = float(metallic)
    bsdf.inputs["Roughness"].default_value = float(roughness)

    # Optional Base Color texture
    if texture_path:
        path = str(Path(texture_path))
        img_node = next((n for n in nodes if n.type == "TEX_IMAGE" and getattr(n, "label", "") == "BaseColorTex"), None)
        if img_node is None:
            img_node = nodes.new("ShaderNodeTexImage")
            img_node.label = "BaseColorTex"
            img_node.location = (-200, 0)
        img = bpy.data.images.get(Path(path).name)
        try:
            if img is None:
                img = bpy.data.images.load(path)
            img_node.image = img
            # reconnect Base Color
            for l in [l for l in list(links) if l.to_node == bsdf and l.to_socket.name == "Base Color"]:
                links.remove(l)
            links.new(img_node.outputs["Color"], bsdf.inputs["Base Color"])
        except RuntimeError as e:
            print(f"[create_and_apply_material] Could not load image '{path}': {e}")

    # ----- Emission: support both Principled variants -----
    if emission_strength > 0.0:
        # Try to use Principled's own emission sockets if they exist
        input_names = {s.name.lower(): s for s in bsdf.inputs}
        has_principled_emission = any(k in input_names for k in ("emission", "emission color"))
        strength_socket = input_names.get("emission strength") or input_names.get("strength")

        if has_principled_emission and strength_socket:
            # Set directly on Principled
            (input_names.get("emission") or input_names.get("emission color")).default_value = rgba_emit
            strength_socket.default_value = float(emission_strength)
            # Ensure Principled goes straight to output
            _link_to_output(links, bsdf.outputs["BSDF"], out, "Surface")
        else:
            # Create Emission + Add Shader and route to Output
            emis = next((n for n in nodes if n.type == "EMISSION"), None)
            if emis is None:
                emis = nodes.new("ShaderNodeEmission")
                emis.location = (200, -200)
            emis.inputs["Color"].default_value = rgba_emit
            emis.inputs["Strength"].default_value = float(emission_strength)

            add = next((n for n in nodes if n.type == "ADD_SHADER"), None)
            if add is None:
                add = nodes.new("ShaderNodeAddShader")
                add.location = (400, -100)

            # Connect BSDF + Emission into Add, then to Output
            # Clear prior output link and re-route through Add
            _link_to_output(links, add.outputs["Shader"], out, "Surface")

            # Make sure inputs are connected (order doesn't matter visually)
            # First, clear any existing links to add inputs to avoid duplicates
            for l in [l for l in list(links) if l.to_node == add]:
                links.remove(l)
            links.new(bsdf.outputs["BSDF"], add.inputs[0])
            links.new(emis.outputs["Emission"], add.inputs[1])
    else:
        # No emission requested: ensure BSDF goes to output surface
        _link_to_output(links, bsdf.outputs["BSDF"], out, "Surface")

    # Apply to object
    if obj.type in {'MESH','CURVE','META','SURFACE','FONT','VOLUME','GPENCIL'}:
        if not obj.data.materials:
            obj.data.materials.append(mat)
        if replace_all_slots:
            for i in range(len(obj.data.materials)):
                obj.data.materials[i] = mat
        else:
            obj.data.materials[0] = mat
    else:
        obj.active_material = mat

    return mat

def monitor_body(color=(0.95, 0.95, 0.93, 1.0), metallic=0, roughness =0.35,name="mon_body"):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree

    for n in list(nt.nodes):
        nt.nodes.remove(n)

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")

    # Basis
    bsdf.inputs["Base Color"].default_value = color

    # Mikro-Glanz
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Roughness"].default_value = 0.35
    bsdf.inputs["Diffuse Roughness"].default_value = 0.10

    # Optik
    bsdf.inputs["IOR"].default_value = 1.45
    bsdf.inputs["Alpha"].default_value = 1.0

    # SSS – leichtes, milchiges Plastik
    bsdf.inputs["Subsurface Weight"].default_value = 0.05
    bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.8, 0.6)
    bsdf.inputs["Subsurface Scale"].default_value = 1.0
    #bsdf.inputs["Subsurface IOR"].default_value = 1.40
    bsdf.inputs["Subsurface Anisotropy"].default_value = 0.0

    # Specular
    bsdf.inputs["Specular IOR Level"].default_value = 1.0
    bsdf.inputs["Specular Tint"].default_value = (0, 0, 0, 0)

    # Keine Anisotropie
    bsdf.inputs["Anisotropic"].default_value = 0.0
    bsdf.inputs["Anisotropic Rotation"].default_value = 0.0

    # Kein Transmission-Glas
    bsdf.inputs["Transmission Weight"].default_value = 0.0

    # Leichter „Lack“-Überzug
    bsdf.inputs["Coat Weight"].default_value = 0.15
    bsdf.inputs["Coat Roughness"].default_value = 0.05
    bsdf.inputs["Coat IOR"].default_value = 1.50
    bsdf.inputs["Coat Tint"].default_value = (1.0, 1.0, 1.0, 1.0)

    # Kein Sheen / Emission / Thin Film
    bsdf.inputs["Sheen Weight"].default_value = 0.0
    bsdf.inputs["Sheen Roughness"].default_value = 0.0
    bsdf.inputs["Sheen Tint"].default_value = (1.0, 1.0, 1.0, 1.0)
    bsdf.inputs["Emission Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    bsdf.inputs["Emission Strength"].default_value = 0.0
    bsdf.inputs["Thin Film Thickness"].default_value = 0.0
    bsdf.inputs["Thin Film IOR"].default_value = 1.0

    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat



def mon_screen_img(asset_path="",offset_uv=(0.0, 0.0),repeat_uv=(1.0, 1.0),rotation_deg=0):
    if asset_path == "":
        asset_folder= str(PROJECT_ROOT)+"/assets/content_monitor/"
        paths = general.list_files_by_extension(asset_folder,".png")
        img_path = paths[random.randint(0,len(paths)-1)]
    else:
        img_path = asset_path
        img = bpy.data.images.load(img_path)
    mat = bpy.data.materials.get("screen_image") or bpy.data.materials.new("screen_image")
    mat.use_nodes = True
    nt = mat.node_tree

    # Nodebaum sauber neu aufbauen
    for n in list(nt.nodes):
        nt.nodes.remove(n)

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    #bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    emit = nt.nodes.new("ShaderNodeEmission")
    tex  = nt.nodes.new("ShaderNodeTexImage")
    tex_coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping   = nt.nodes.new("ShaderNodeMapping")

    mapping.inputs['Scale'].default_value[1] = 1.45
    mapping.inputs['Location'].default_value[1] = -0.25 



    tex.image = img
    tex.extension = 'CLIP'  # keine Wiederholung, kein Abschneiden durch Tiling
    emit.inputs["Strength"].default_value = 0.5
    nt.links.new(tex_coord.outputs['UV'], mapping.inputs['Vector'])
    nt.links.new(mapping.outputs['Vector'], tex.inputs['Vector'])
    nt.links.new(tex.outputs["Color"], emit.inputs["Color"])
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat

