import argparse, json, os, cv2, numpy as np

# Nice distinct BGR colors to cycle through
PALETTE = [
    (0,255,0), (0,200,255), (255,200,0), (255,0,255), (0,128,255),
    (255,128,0), (200,255,0), (255,0,128), (128,255,255), (255,128,255)
]

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
    # poly: (N, 2) float or int array

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True, help="Input video")
    ap.add_argument("--json", required=True, nargs="+", help="One or more bb_tracking.json files")
    ap.add_argument("--out", required=True, help="Output video path")
    ap.add_argument("--start-frame", type=int, default=1, help="1 if JSON frames are 1-based (Blender), 0 if zero-based")
    ap.add_argument("--alpha", type=float, default=0.25, help="Fill opacity 0..1")
    ap.add_argument("--thickness", type=int, default=2, help="Outline thickness")
    ap.add_argument("--draw-invisible", action="store_true", help="Also draw if visible==False")
    args = ap.parse_args()

    # Load all JSONs -> list of (name, frame_map)
    trackers = []
    for i, path in enumerate(args.json):
        fm = load_json_as_frame_map(path)
        trackers.append((os.path.basename(path), fm))

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {args.video}")
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    fourcc = cv2.VideoWriter_fourcc(*"avc1")
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    writer = cv2.VideoWriter(args.out, fourcc, fps, (w, h))

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret: break
        fr = frame_idx + args.start_frame

        for k, (name, fmap) in enumerate(trackers):
            entry = fmap.get(fr)
            if entry is None: continue
            if not entry["visible"] and not args.draw_invisible: continue

            color = PALETTE[k % len(PALETTE)]
            poly = entry["poly"].copy()
            # clamp
            poly[:,0] = np.clip(poly[:,0], 0, w-1)
            poly[:,1] = np.clip(poly[:,1], 0, h-1)

            label = entry.get("name") or name
            draw_poly(frame, poly, color, args.thickness, args.alpha,scale=1.5)#, label=label)

        writer.write(frame)
        frame_idx += 1

    cap.release(); writer.release()
    print(f"✅ Wrote: {args.out}")

if __name__ == "__main__":
    main()
