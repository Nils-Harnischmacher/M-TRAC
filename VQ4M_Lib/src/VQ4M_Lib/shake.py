# imu_preprocess.py  (du kannst das in eine eigene Datei legen/ importieren)
import csv, os, math
import math
from mathutils import Vector, Quaternion,Euler,Matrix
import bpy
from pathlib import Path
import random
        
G_TO_MS2 = 9.80665

def load_ios_coremotion_csv(csv_path, correction_matrix=None):
    """
    Liest eine iOS/CoreMotion-CSV mit den Spaltennamen aus deiner App.
    Rückgabe: Liste von dicts mit:
      t: float (s, since reboot)
      q: Quaternion (qw,qx,qy,qz) als mathutils.Quaternion
      a_dev_ms2: Vector (ax,ay,az) in m/s^2, UserAcceleration im Geräteraum
      gyro: Vector (rad/s), kann (0,0,0) sein wenn nicht vorhanden
    """
    rows = []
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for r in reader:
            t  = float(r['motionTimestamp_sinceReboot(s)'])
            yaw= float(r['motionYaw(rad)'])
            pitch= float(r['motionPitch(rad)'])
            roll= float(r['motionRoll(rad)'])
            ax = float(r['motionUserAccelerationX(G)']) * G_TO_MS2
            ay = float(r['motionUserAccelerationY(G)']) * G_TO_MS2
            az = float(r['motionUserAccelerationZ(G)']) * G_TO_MS2
            grx = float(r.get('motionRotationRateX(rad/s)', '0') or 0.0)
            gry = float(r.get('motionRotationRateY(rad/s)', '0') or 0.0)
            grz = float(r.get('motionRotationRateZ(rad/s)', '0') or 0.0)
            
            if correction_matrix is None:
                correction_matrix = Matrix(((0.0, 0.0, -1.0),
                                            (0.0, -1.0, 0.0),
                                            (1.0, 0.0, 0.0)))
            rows.append({
                't': t,
                'q': Quaternion((Euler((yaw,pitch,roll), 'XYZ'))),
                'a_dev_ms2': correction_matrix @ Vector((ax,ay,az)),
                'gyro': Vector((grx,gry,grz)),
            })

    rows.sort(key=lambda r: r['t'])
    return rows

def imu_to_trajectory(
    rows,
    fps,
    trapezoid=True,
    rubberband=False,
    k_spring=2.0,
    alpha_exp=0.0,
    c_damp=3.0,
    deadband=0.01,
    offset = (math.radians(90), 0.0, 0.0),
):
    if not rows:
        return []

    t0 = rows[0]['t']
    traj = []
    v = Vector((0.0,0.0,0.0))
    p = Vector((0.0,0.0,0.0))
    prev_t = rows[0]['t']
    prev_a_tot = None
    zero_center= None
    first_frame = True
    for i, r in enumerate(rows):

        t = r['t']
        dt = (t - prev_t) if i > 0 else (1.0 / max(1, fps))
        if dt <= 0:
            prev_t = t
            continue

        q = r['q']
        if first_frame:
            zero_center= q.copy()
            first_frame = False

        R_fix = Euler(offset, 'XYZ').to_quaternion()

        R_world =  zero_center.inverted() @ q

        a_corr_dev = r['a_dev_ms2'] 
        a_world = R_world @ a_corr_dev
        R_world = R_fix @ R_world 

        if rubberband:
            p_len = p.length
            if p_len > deadband:
                if alpha_exp > 0.0:
                    a_spring = -(k_spring * math.exp(alpha_exp * p_len)) * (p / p_len)
                else:
                    a_spring = -k_spring * p
            else:
                a_spring = Vector((0.0,0.0,0.0))
            a_damp = -c_damp * v
            a_tot = a_world + a_spring + a_damp
        else:
            a_tot = a_world

        if trapezoid and prev_a_tot is not None:
            v = v + 0.5 * (prev_a_tot + a_tot) * dt
        else:
            v = v + a_tot * dt

        p = p + v * dt
        R_cam = R_world

        traj.append({
            't': t,
            'R_world': R_cam.copy(),
            'p': p.copy(),
            'v': v.copy(),
        })

        prev_t = t
        prev_a_tot = a_tot

    return traj


def apply_trajectory_to_object(
    obj,
    traj,
    frame0=1,
    fps=30,
    clear_anim=True,
    base_location=None,   # <- NEU: Ankerpunkt
):
    """
    Schreibt Rotation (Quaternion) und Location aus 'traj' als Keyframes.
    Die Trajektorie 'p' wird als RELATIVE Verschiebung interpretiert und
    um 'base_location' verschoben. Standard: aktuelle Objektposition.
    """
    if not traj:
        return

    if clear_anim and obj.animation_data:
        obj.animation_data_clear()
    obj.rotation_mode = 'QUATERNION'

    try:
        bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
    except Exception:
        pass

    anchor = base_location.copy() if base_location is not None else obj.location.copy()

    t0 = traj[0]['t']
    for sample in traj:
        frame = frame0 + round((sample['t'] - t0) * fps)
        # Rotation: direkt
        obj.rotation_quaternion = sample['R_world']
        obj.keyframe_insert(data_path="rotation_quaternion", frame=frame)

        # Translation: RELATIV + ANKER
        obj.location = anchor + sample['p']
        obj.keyframe_insert(data_path="location", frame=frame)

def apply_camera_motion_from_csv(
    camera,
    csv_path,
    correction_matrix=None,
    trapezoid=True,         # stabiler als Vorwärts-Euler
    rubberband=True,        # <- hier ein/aus
    k_spring=2.0,
    alpha_exp=0.0,          # 0 = linear; >0 macht's nichtlinear
    c_damp=3.0,
    deadband=0.01,
    offset = (0,0 ,0), 
):
    """
    Reads a CSV and writes camera keyframes.
    Supported headers:
      - Quaternion: frame,x,y,z,qw,qx,qy,qz    (qw..qz are delta if interpret_csv_as_offsets=True)
      - Euler:      frame,x,y,z,roll,pitch,yaw (radians if euler_input_in_degrees=False)

    When apply_relative=True and interpret_csv_as_offsets=True:
      - Position (x,y,z) is treated as a small offset around 0.
      - Rotation is a delta around identity, composed with the camera's current rotation.
    """
 
    rows = load_ios_coremotion_csv(csv_path,correction_matrix)
    fps = bpy.context.scene.render.fps


    traj = imu_to_trajectory(
        rows,
        fps=fps,
        trapezoid=trapezoid,         # stabiler als Vorwärts-Euler
        rubberband=rubberband,        # <- hier ein/aus
        k_spring=k_spring,
        alpha_exp=alpha_exp,          # 0 = linear; >0 macht's nichtlinear
        c_damp=c_damp,
        deadband=deadband,
        offset = offset,
    )
    apply_trajectory_to_object(camera,traj,frame0=1,fps=fps)



def add_camera_shake(type="walking", camera=None, csv_path=None,settings=None):
    """
    Loads motion from walking.csv or running.csv and applies it to the camera.
    Expects CSV in the working dir or in base_dir with either:
      - frame,x,y,z,qw,qx,qy,qz
      - frame,x,y,z,roll,pitch,yaw
    """
    if camera is None:
        print("PLACE CAMERA IN SCENE BEFOR CALLING THIS!")
    
    offset = camera.rotation_euler
    if not settings:
        # Apply the CSV track
        apply_camera_motion_from_csv(
            camera=camera,
            csv_path=csv_path,
            offset=offset,
        )

    else:
        apply_camera_motion_from_csv(
        camera,
        csv_path,
        Matrix(settings['correction_matrix']),
        settings['trapezoid'],         
        settings['rubberband'],        
        settings['k_spring'],
        settings['alpha_exp'],        
        settings['c_damp'],
        settings['deadband'], 
        offset,
    )

    return camera

