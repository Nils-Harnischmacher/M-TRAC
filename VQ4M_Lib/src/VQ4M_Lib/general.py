import bpy, math,json
import os
import os
from pathlib import Path
from typing import Union, Iterable, List,Dict, Tuple, Any
def clean_scene():
    try:
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
    except Exception:
        pass  
    for obj in tuple(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

    root = bpy.context.scene.collection
    for coll in tuple(bpy.data.collections):
        if coll is not root:
            bpy.data.collections.remove(coll)
    def purge_once():
        libs = (
            bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.images,
            bpy.data.lights, bpy.data.cameras, bpy.data.armatures, bpy.data.metaballs,
            getattr(bpy.data, "grease_pencils", ()),  # GP v3 (Blender 4.x)
            bpy.data.textures if hasattr(bpy.data, "textures") else (),
            bpy.data.node_groups,
        )
        removed = 0
        for lib in libs:
            for datablock in tuple(lib):
                if getattr(datablock, "users", 0) == 0:
                    lib.remove(datablock)
                    removed += 1
        return removed

    for _ in range(5):
        if purge_once() == 0:
            break


def create_parent(name, location, rotation):
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=location)
    parent = bpy.context.active_object
    parent.name = name
    parent.rotation_euler = rotation
    return parent

def ensure_camera(location=(0, -10, 5), rotation=(math.radians(75), 0, 0)):
    scene = bpy.context.scene
    for obj in bpy.data.objects:
        if obj.type == 'CAMERA':
            scene.camera = obj
            return obj
    bpy.ops.object.camera_add(location=location, rotation=rotation)
    cam = bpy.context.active_object
    cam.name = "Camera"
    scene.camera = cam
    return cam

def list_files_by_extension(
    root_dir: Union[str, os.PathLike],
    extension: Union[str, Iterable[str]],
    *,
    absolute: bool = True,
    include_root: bool = True
) -> List[str]:
    """
    Find files under `root_dir` (recursively) that match the given extension(s).

    Args:
        root_dir: Directory to search.
        extension: A single extension like "png" or ".png",
                   or an iterable like ("png", "jpg").
        absolute: If True, return absolute paths; else paths relative to root_dir.
        include_root: If False, exclude files in the top-level root_dir itself
                      (i.e., only consider subdirectories).

    Returns:
        Sorted list of matching file paths (as strings).
    """
    root = Path(root_dir).expanduser().resolve()
    if isinstance(extension, (str, os.PathLike)):
        exts = {str(extension).lower().lstrip('.')}
    else:
        exts = {str(e).lower().lstrip('.') for e in extension}

    matches: List[str] = []
    for dirpath, _, filenames in os.walk(root):
        if not include_root and Path(dirpath) == root:
            continue

        for fname in filenames:
            suf = fname.rsplit('.', 1)[-1].lower() if '.' in fname else ''
            if suf in exts:
                p = Path(dirpath) / fname
                matches.append(str(p if absolute else p.relative_to(root)))

    matches.sort()
    return matches



def load_profile(base_dir: str = "configs") -> Dict[str, Any]:
    base_dir = Path(base_dir)
    base_path = base_dir / "base.json"
    if not base_path.exists():
        raise FileNotFoundError(f"Missing base defaults JSON: {base_path}")
    base = _read_json(base_path)
    # --- required fields in profile ---
    scene_length = _require_int(base, "scene_length", min_val=1)
    # --- merge settings ---
    base_settings = base.get("shake_settings", {})
    shake_settings = {**base_settings}
    cfg = {
        "scene_length": scene_length,
        "shake_settings": shake_settings
    }
    return cfg

# ------------- helpers -------------
def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise TypeError(f"Top-level JSON must be an object: {path}")
    return data

def _require_int(d: Dict[str, Any], key: str, *, min_val: int = None) -> int:
    if key not in d:
        raise KeyError(f"Missing required key '{key}'")
    val = d[key]
    if not isinstance(val, int):
        raise TypeError(f"'{key}' must be int (got {type(val).__name__})")
    if min_val is not None and val < min_val:
        raise ValueError(f"'{key}' must be >= {min_val}")
    return val

def _require_seq_len(d: Dict[str, Any], key: str, n: int, types) -> Tuple[Any, ...]:
    if key not in d:
        raise KeyError(f"Missing required key '{key}'")
    val = d[key]
    if not isinstance(val, (list, tuple)) or len(val) != n or not all(isinstance(x, types) for x in val):
        raise TypeError(f"'{key}' must be a list of {n} numbers")
    return tuple(val)

def _reject_unknown(d: Dict[str, Any], allowed: set, where: str = "object") -> None:
    unknown = [k for k in d.keys() if k not in allowed]
    if unknown:
        raise KeyError(f"Unknown keys in {where}: {unknown}")