import argparse
import csv
import json
import os
from pathlib import Path
from tqdm import tqdm
import cv2
import numpy as np
import subprocess


def load_json_as_frame_map(path, default_name=None):
    with open(path, "r") as f:
        data = json.load(f)
    m = {}
    for r in data:
        p = r["projection"]
        poly = np.array([p["tl"], p["tr"], p["br"], p["bl"]], dtype=np.float32)
        m[int(r["frame"])] = {
            "poly": poly,
            "visible": bool(p.get("visible", True)),
            "name": r.get("box_name", default_name or os.path.splitext(os.path.basename(path))[0]),
        }
    return m


def scale_poly(poly: np.ndarray, scale: float) -> np.ndarray:
    if scale == 1.0:
        return poly
    center = poly.mean(axis=0)
    return center + (poly - center) * scale


def compute_crop_rect(fm, w, h, use_visible_only=True, scale=1.0, pad_px=0,
                      q_lo=5.0, q_hi=95.0, skip_border_touch=True):
    """
    Robust crop:
    - compute per-frame axis-aligned bbox of the quad
    - take quantiles over time (q_lo/q_hi) to ignore outliers
    - optionally skip frames where bbox touches image border (often cutoff/jitter)
    """
    xmins, ymins, xmaxs, ymaxs = [], [], [], []

    for _, entry in fm.items():
        if use_visible_only and not entry.get("visible", True):
            continue

        poly = entry["poly"]
        if not isinstance(poly, np.ndarray):
            poly = np.asarray(poly, dtype=np.float32)

        poly = scale_poly(poly.astype(np.float32), scale)

        # clip to frame
        poly2 = poly.copy()
        np.clip(poly2[:, 0], 0, w - 1, out=poly2[:, 0])
        np.clip(poly2[:, 1], 0, h - 1, out=poly2[:, 1])

        xmin = float(poly2[:, 0].min())
        ymin = float(poly2[:, 1].min())
        xmax = float(poly2[:, 0].max())
        ymax = float(poly2[:, 1].max())

        # Often cutoff boxes get clipped to 0 or w-1/h-1: skip those frames
        if skip_border_touch and (xmin <= 0.5 or ymin <= 0.5 or xmax >= w - 1.5 or ymax >= h - 1.5):
            continue

        xmins.append(xmin); ymins.append(ymin); xmaxs.append(xmax); ymaxs.append(ymax)

    # fallback if everything got filtered out
    if not xmins:
        # fallback to old behavior: union over all (including border-touch)
        xs, ys = [], []
        for _, entry in fm.items():
            if use_visible_only and not entry.get("visible", True):
                continue
            poly = np.asarray(entry["poly"], dtype=np.float32)
            poly = scale_poly(poly, scale)
            poly2 = poly.copy()
            np.clip(poly2[:, 0], 0, w - 1, out=poly2[:, 0])
            np.clip(poly2[:, 1], 0, h - 1, out=poly2[:, 1])
            xs.extend(poly2[:, 0].tolist()); ys.extend(poly2[:, 1].tolist())
        if not xs:
            return (0, 0, w, h)
        x0 = int(max(0, np.floor(min(xs)) - pad_px))
        y0 = int(max(0, np.floor(min(ys)) - pad_px))
        x1 = int(min(w, np.ceil(max(xs)) + pad_px))
        y1 = int(min(h, np.ceil(max(ys)) + pad_px))
        return make_even_crop(x0, y0, x1, y1, w, h)

    # quantile crop
    x0 = int(max(0, np.floor(np.percentile(xmins, q_lo)) - pad_px))
    y0 = int(max(0, np.floor(np.percentile(ymins, q_lo)) - pad_px))
    x1 = int(min(w, np.ceil(np.percentile(xmaxs, q_hi)) + pad_px))
    y1 = int(min(h, np.ceil(np.percentile(ymaxs, q_hi)) + pad_px))

    return make_even_crop(x0, y0, x1, y1, w, h)


def make_even_crop(x0, y0, x1, y1, w, h):
    # ensure valid
    x0 = max(0, min(x0, w - 2))
    y0 = max(0, min(y0, h - 2))
    x1 = max(x0 + 2, min(x1, w))
    y1 = max(y0 + 2, min(y1, h))

    # force even dimensions for yuv420p
    cw = x1 - x0
    ch = y1 - y0
    if cw % 2 == 1:
        if x1 < w:
            x1 += 1
        else:
            x1 -= 1
    if ch % 2 == 1:
        if y1 < h:
            y1 += 1
        else:
            y1 -= 1

    # clamp again
    x1 = min(w, max(x0 + 2, x1))
    y1 = min(h, max(y0 + 2, y1))
    return (x0, y0, x1, y1)


def process_video(video_path, json_path, name, out_dir, crop_scale=1.0, crop_pad=0, visible_only=True):
    save_path = os.path.join(out_dir, name)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    if os.path.exists(save_path) and os.path.getsize(save_path) > 1024:
        return

    fm = load_json_as_frame_map(json_path)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    # Compute a CONSTANT crop rect for this whole output video
    x0, y0, x1, y1 = compute_crop_rect(
        fm, w, h,
        use_visible_only=visible_only,
        scale=crop_scale,
        pad_px=crop_pad,
    )
    cw = int(x1 - x0)
    ch = int(y1 - y0)

    # Feed CROPPED raw frames to ffmpeg (so output is actually cropped)
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-loglevel", "error",

        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", f"{cw}x{ch}",
        "-r", str(fps),
        "-i", "pipe:0",

        # Use videotoolbox if available; otherwise switch to libx264 manually if needed
        "-c:v", "h264_videotoolbox",
        "-b:v", "60M",
        "-maxrate", "80M",
        "-bufsize", "120M",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",

        save_path
    ]

    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    frame_idx = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1

            # Crop frame to constant bbox
            cropped = frame[y0:y1, x0:x1]

            if proc.poll() is not None:
                err = proc.stderr.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"ffmpeg died early:\n{err}")

            try:
                proc.stdin.write(cropped.tobytes())
            except BrokenPipeError:
                err = proc.stderr.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"Broken pipe (ffmpeg exited). ffmpeg said:\n{err}")

        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            raise RuntimeError(f"ffmpeg failed with return code {rc}")
    finally:
        cap.release()
        if proc and proc.stdin and not proc.stdin.closed:
            try:
                proc.stdin.close()
            except Exception:
                pass
        if proc and proc.poll() is None:
            proc.terminate()


def find_files(root: Path, exts):
    for p in root.rglob("*"):
        if any(part.startswith(".") for part in p.parts):
            continue
        if p.is_file() and p.suffix.lower() in exts:
            render_list = ["center", "close_up", "horizontal", "vertical", "far_away"]
            # Keep your original filter logic, but guard index errors
            if len(p.parts) > 13 and p.parts[13] in render_list:
                yield p


def gen_name(json_path: Path):
    obj = json_path.parts[9]
    mov = json_path.parts[10]
    img = json_path.parts[11]
    bg = json_path.parts[12]
    view = json_path.parts[13]
    bb = json_path.parts[15]
    bg = "nb" if "without" in bg else "wb"
    mov = ''.join(w[0] for w in mov.split('_')) if '_' in mov else mov[:3].lower()
    return f"{obj[:3]}-{mov}-{img}-{bg}-{view[:3]}-{bb.replace('.','')}.mp4"


def load_allowed_names_from_csv(csv_path: Path, column="files"):
    allowed = set()
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        if column not in reader.fieldnames:
            raise ValueError(f"CSV missing required column '{column}'. Found: {reader.fieldnames}")
        for row in reader:
            v = (row.get(column) or "").strip()
            if v:
                allowed.add(v)
    return allowed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="path to folder")
    ap.add_argument("--csv", default=None, help="CSV with a column 'files' containing generated output names to render")
    ap.add_argument("--csv_col", default="files", help="CSV column name (default: files)")
    ap.add_argument("--out_dir", default="out_filtered", help="output folder")
    ap.add_argument("--crop_scale", type=float, default=1.0, help="scale bbox before cropping (1.0 = exact)")
    ap.add_argument("--crop_pad", type=int, default=0, help="extra pixels padding around bbox")
    ap.add_argument("--visible_only", action="store_true", help="use only entries with visible==True for crop union")
    args = ap.parse_args()

    root = Path(args.root).resolve()

    allowed = None
    if args.csv:
        allowed = load_allowed_names_from_csv(Path(args.csv), column=args.csv_col)
        print(f"Allowed names from CSV: {len(allowed)}")

    jobs = []
    for video_path in find_files(root, {".mp4"}):
        jsons = list(find_files(video_path.parent, {".json"}))
        for json_path in jsons:
            temp_name = gen_name(json_path)
            if allowed is not None and temp_name not in allowed:
                continue
            jobs.append((video_path, json_path, temp_name))

    print(f"Jobs: {len(jobs)}")

    for vp, jp, name in tqdm(jobs):
        process_video(
            vp, jp, name,
            out_dir=args.out_dir,
            crop_scale=args.crop_scale,
            crop_pad=args.crop_pad,
            visible_only=args.visible_only,
        )


if __name__ == "__main__":
    main()