import bpy, json, math
import mathutils



def create_camera_from_calibration_json(
    json_path: str,
    name: str = "RealWear_N500",
    location=(0.0, 0.0, 0.0),
    rotation_euler_deg=(0.0, 0.0, 0.0),
    sensor_width_mm: float | None = None,   
    set_scene_resolution: bool = True,
    apply_principal_point_shift: bool = True,
    add_simple_lens_node: bool = False      
):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    w = int(data["image_size_px"]["width"])
    h = int(data["image_size_px"]["height"])
    fx = float(data["intrinsics_px"]["fx"])
    fy = float(data["intrinsics_px"]["fy"])
    cx = float(data["intrinsics_px"]["cx"])
    cy = float(data["intrinsics_px"]["cy"])
    k1 = float(data.get("distortion", {}).get("k1", 0.0))
    et = float(data.get("exif_exposure_time", 0.01))

    if sensor_width_mm is None:
        sensor_width_mm = (data.get("derived_mm") or {}).get("sensor_width_mm", None)
    if sensor_width_mm is None:
        sensor_width_mm = 6.30  

    f_mm = fx * float(sensor_width_mm) / float(w)

    cam_data = bpy.data.cameras.new(name)
    cam_obj = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)

    cam_obj.location = mathutils.Vector(location)
    cam_obj.rotation_euler = mathutils.Euler(tuple(math.radians(a) for a in rotation_euler_deg), 'XYZ')

    cam_data.type = 'PERSP'
    cam_data.sensor_fit = 'HORIZONTAL'
    cam_data.sensor_width = float(sensor_width_mm)
    cam_data.lens = float(f_mm)

    if apply_principal_point_shift:
        cam_data.shift_x = (cx - (w / 2.0)) / w
        cam_data.shift_y = - (cy - (h / 2.0)) / h

    if set_scene_resolution:
        scn = bpy.context.scene
        scn.render.resolution_x = w
        scn.render.resolution_y = h
        scn.render.pixel_aspect_x = 1.0
        scn.render.pixel_aspect_y = 1.0

    if add_simple_lens_node:
        scn = bpy.context.scene
        scn.use_nodes = True
        tree = scn.node_tree
        for n in list(tree.nodes): tree.nodes.remove(n)
        rl = tree.nodes.new("CompositorNodeRLayers")
        ld = tree.nodes.new("CompositorNodeLensdist")
        comp = tree.nodes.new("CompositorNodeComposite")
        rl.location = (-400, 0); ld.location = (-150, 0); comp.location = (150, 0)
        # Heuristik: Blender-Node ≠ OpenCV; visuell anpassen!
        ld.inputs[1].default_value = float(k1) * 0.7
        tree.links.new(rl.outputs["Image"], ld.inputs["Image"])
        tree.links.new(ld.outputs["Image"], comp.inputs["Image"])

    cam_obj["calib_json"] = bpy.path.abspath(json_path)
    cam_obj["fx_px"] = fx; cam_obj["fy_px"] = fy
    cam_obj["cx_px"] = cx; cam_obj["cy_px"] = cy
    cam_obj["k1"] = k1

    cam_obj.hide_render = False
    cam_obj.hide_viewport = False
    return cam_obj,et
