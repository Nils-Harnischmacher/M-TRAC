import bpy
import os, csv, json
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view


def project_object_space_box(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    obj: bpy.types.Object,
    box_name: str = "box",
    box_width: float = 1.0,
    box_height: float = 1.0,
    use_empty_frame: bool = True,
    frame_empty: bpy.types.Object | None = None,
    local_center: Vector = Vector((0, 0, 0)),
    out_base_dir: str | None = None,
    log_json: bool = True,
    log_csv: bool = True
):
    """
    Projects a bounding box defined in object or empty space into 2D screen coordinates per frame.
    Saves JSON and CSV logs under ./boundingbox/<box_name>/.
    """

    # Image resolution (px)
    rx = int(scene.render.resolution_x * scene.render.resolution_percentage / 100)
    ry = int(scene.render.resolution_y * scene.render.resolution_percentage / 100)
    fps = scene.render.fps

    # --- Output paths ---
    if out_base_dir is None:
        out_base_dir = bpy.path.abspath("//")

    # Folder: ./boundingbox/<name>/
    out_dir = os.path.join(out_base_dir, "boundingbox", box_name)
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, "bb_tracking.csv")
    json_path = os.path.join(out_dir, "bb_tracking.json")

    def get_corners_world():
        half_w, half_h = box_width / 2, box_height / 2
        corners_local = [
            Vector((-half_w,  half_h, 0.0)),  # TL
            Vector(( half_w,  half_h, 0.0)),  # TR
            Vector(( half_w, -half_h, 0.0)),  # BR
            Vector((-half_w, -half_h, 0.0)),  # BL
        ]

        if use_empty_frame and frame_empty:
            M = frame_empty.matrix_world
            return [M @ p for p in corners_local]
        else:
            M = obj.matrix_world
            center_w = M @ local_center
            x_axis = (M.to_3x3() @ Vector((1, 0, 0))).normalized()
            y_axis = (M.to_3x3() @ Vector((0, 1, 0))).normalized()
            z_axis = (M.to_3x3() @ Vector((0, 0, 1))).normalized()
            return [center_w + p.x*x_axis + p.y*y_axis + p.z*z_axis for p in corners_local]

    def to_pixels(vec3):
        uvw = world_to_camera_view(scene, camera, vec3)
        u, v, w = uvw.x, uvw.y, uvw.z
        x_px = u * rx
        y_px = (1.0 - v) * ry
        visible = (0.0 <= u <= 1.0) and (0.0 <= v <= 1.0) and (w >= 0.0)
        return x_px, y_px, visible, w

    results = []
    for f in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(f)

        cam_loc = camera.matrix_world.translation.copy()
        cam_rot_quat = camera.matrix_world.to_quaternion()
        cam_data = camera.data

        corners_world = get_corners_world()
        center_w = sum(corners_world, Vector()) / 4
        normal_w = (corners_world[1] - corners_world[0]).cross(corners_world[3] - corners_world[0]).normalized()

        corners_px = [to_pixels(p) for p in corners_world]
        xs = [c[0] for c in corners_px]
        ys = [c[1] for c in corners_px]
        visible = all(c[2] for c in corners_px)

        # bounding box
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        # corners (explicit)
        tl_x, tl_y = xs[0], ys[0]
        tr_x, tr_y = xs[1], ys[1]
        br_x, br_y = xs[2], ys[2]
        bl_x, bl_y = xs[3], ys[3]

        results.append({
            "frame": f,
            "time_sec": f / fps,
            "box_name": box_name,
            "camera": {
                "name": camera.name,
                "location": tuple(cam_loc),
                "rotation_quat": tuple(cam_rot_quat),
                "lens_mm": cam_data.lens,
                "sensor_width_mm": cam_data.sensor_width,
                "sensor_height_mm": cam_data.sensor_height,
                "shift_xy": (cam_data.shift_x, cam_data.shift_y),
            },
            "object": {
                "name": obj.name,
                "box_width_m": box_width,
                "box_height_m": box_height,
                "center_world": tuple(center_w),
                "normal_world": tuple(normal_w),
                "corners_world": [tuple(c) for c in corners_world],
            },
            "projection": {
                "tl": (tl_x, tl_y),
                "tr": (tr_x, tr_y),
                "br": (br_x, br_y),
                "bl": (bl_x, bl_y),
                "min_x": min_x,
                "min_y": min_y,
                "max_x": max_x,
                "max_y": max_y,
                "visible": visible,
            }
        })

    # --- Save minimal CSV ---
    if log_csv:
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["frame", "min_x", "min_y", "max_x", "max_y", "visible"])
            for r in results:
                p = r["projection"]
                writer.writerow([
                    r["frame"], p["min_x"], p["min_y"], p["max_x"], p["max_y"], p["visible"]
                ])
    # --- Save full JSON ---
    if log_json:
        with open(json_path, "w") as f:
            json.dump(results, f, indent=2)

    return results


def show_bb(target, height, width, offset=(0,0,0)): 
   
    color = (1.0, 0.0, 0.0, 1.0) # RGBA red 
    bpy.ops.mesh.primitive_plane_add(size=1, location=offset) 
    obj = bpy.context.active_object 
    obj.scale = (width,height,1) 
    obj.parent=target
    
    
    
    
    mat = bpy.data.materials.new(name="RedWire") 
    mat.use_nodes = True 
    nodes = mat.node_tree.nodes 
    bsdf = nodes.get("Principled BSDF") 
    bsdf.inputs["Base Color"].default_value = color 
    bsdf.inputs["Alpha"].default_value = 0.4 
    obj.data.materials.append(mat) 
    obj.hide_render = True