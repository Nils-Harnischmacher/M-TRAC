import argparse
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

def draw_poly(frame, poly, color, thickness, alpha, label=None, scale=1.0):

    if scale != 1.0:
        center = poly.mean(axis=0)
        poly = center + (poly - center) * scale

    pts = poly.astype(np.int32).reshape(-1, 1, 2)

    if alpha > 0:
        overlay = frame.copy()
        cv2.fillPoly(overlay, [pts], color)
        frame[:] = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

    cv2.polylines(frame, [pts], True, color, thickness, cv2.LINE_AA)

    if label:
        tl = tuple(pts[0, 0])
        cv2.putText(frame,label,(tl[0], max(0, tl[1] - 6)),cv2.FONT_HERSHEY_SIMPLEX,0.5,color,1,cv2.LINE_AA)


def process_video(video_path, json_path, name):
    save_path = os.path.join("out_filtered", name)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    if os.path.exists(save_path) and os.path.getsize(save_path) > 1024:
        return

    fm = load_json_as_frame_map(json_path)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    # Fast + browser-safe H.264 MP4:
    # - h264_videotoolbox nutzt Apple Media Engine (sehr schnell)
    # - yuv420p = maximale Browser-Kompatibilität
    # - hohe Bitrate = "visually same"
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-loglevel", "error",

        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", f"{w}x{h}",
        "-r", str(fps),
        "-i", "pipe:0",

        "-c:v", "h264_videotoolbox",
        "-b:v", "60M",
        "-maxrate", "80M",
        "-bufsize", "120M",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",

        save_path
    ]

    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

    color = (0, 255, 0)
    thickness = 3
    alpha = 0.25
    scale = 1.5

    frame_idx = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1

            entry = fm.get(frame_idx)
            if entry is not None: #and entry.get("visible", False):
                poly = entry["poly"]
                if not isinstance(poly, np.ndarray):
                    poly = np.asarray(poly)

                poly2 = poly.copy()
                np.clip(poly2[:, 0], 0, w - 1, out=poly2[:, 0])
                np.clip(poly2[:, 1], 0, h - 1, out=poly2[:, 1])

                draw_poly(frame, poly2, color, thickness, alpha, scale=scale)

            proc.stdin.write(frame.tobytes())

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


def find_files( root, exts):
    for p in root.rglob("*"):
        if any(part.startswith(".") for part in p.parts):
            continue
        if p.is_file() and p.suffix.lower() in exts:
            render_list=["center","close_up","horizontal","vertical","far_away"]
            if p.parts[13] in render_list : 
                #print(p.parts[13])
                yield p

def gen_name(json_path):
    obj = json_path.parts[9]
    mov = json_path.parts[10]
    img = json_path.parts[11]
    bg = json_path.parts[12]
    view = json_path.parts[13]
    bb = json_path.parts[15]
    bg = "nb" if "without" in bg else "wb"
    mov = ''.join(w[0] for w in mov.split('_')) if '_' in mov else mov[:3].lower()
    return f"{obj[:3]}-{mov}-{img}-{bg}-{view[:3]}-{bb.replace('.','')}.mp4"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="path to folder")
    args=ap.parse_args()
    root = Path(args.root).resolve()
    jobs = []
    for video_path in find_files(root, {".mp4"}):
        jsons = list(find_files(video_path.parent, {".json"}))
        for json_path in jsons:
            temp_name = gen_name(json_path)
            jobs.append((video_path, json_path, temp_name))
    print(len(jobs))
    for vp,jp,name in tqdm(jobs): 
        process_video(vp,jp,name)

if __name__ == "__main__":
    main()
