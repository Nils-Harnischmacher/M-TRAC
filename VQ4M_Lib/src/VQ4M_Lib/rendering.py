import bpy

def _force_eevee_engine(render):
    """Set EEVEE/EEVEE_NEXT depending on what's available."""
    try:
        render.engine = 'BLENDER_EEVEE'          # Blender ≤3.x
    except TypeError:
        render.engine = 'BLENDER_EEVEE_NEXT'     # Blender 4.x

def _eevee_settings(scene):
    """Return the Eevee settings struct (guard for future renames)."""
    eevee = getattr(scene, "eevee", None)
    if eevee is None:
        eevee = getattr(scene, "eevee_next", None)
    if eevee is None:
        raise RuntimeError("Eevee settings not found on scene.")
    return eevee

def set_render_settings(
    output_path,
    file_format='FFMPEG',
    codec='H264',
    frame_start = 200,
    frame_end   = 280,
    overwrite_res=False,
    resolution=(1280, 720),
    fps=24,
    exposure_time=1/90,
    blur_steps=32
):
    """
    EEVEE/EEVEE_NEXT render with:
      - Frame range: 1–80, step 1
      - Render samples: 64
      - Shadows: on (soft if available)
      - Motion blur: position=CENTER, shutter=1.0, max=32 px, bleed bias=100 (if available)
    """
    scene = bpy.context.scene
    render = scene.render

    scene.frame_start = frame_start
    scene.frame_end   = frame_end 
    scene.frame_step  = 1
    render.compositor_device = 'GPU'

    _force_eevee_engine(render)
    eevee = _eevee_settings(scene)

    if hasattr(eevee, "taa_render_samples"):
        eevee.taa_render_samples = 64
    elif hasattr(eevee, "samples"):
        eevee.samples = 64
    if hasattr(eevee, "taa_samples"):
        eevee.taa_samples = max(16, min(64, 64))

    if hasattr(eevee, "use_shadow"):
        eevee.use_shadow = True
    if hasattr(eevee, "use_soft_shadows"):
        eevee.use_soft_shadows = True
    for attr in ("shadow_bleed_bias", "shadow_bleeding_bias"):
        if hasattr(eevee, attr):
            try:
                setattr(eevee, attr, 100)
            except Exception:
                pass


    if hasattr(render, "use_motion_blur"):
         render.use_motion_blur = True
    if hasattr(render, "motion_blur_shutter"):
        render.motion_blur_shutter = exposure_time / (1.0 / fps)
    if hasattr(render, "motion_blur_position"):
        render.motion_blur_position = 'CENTER'   
    if hasattr(render, "motion_blur_steps"):
        render.motion_blur_steps = blur_steps


    dst = bpy.path.abspath(output_path)
    render.filepath = dst
    render.image_settings.file_format = file_format
    if overwrite_res:
        render.resolution_x, render.resolution_y = resolution
    render.resolution_percentage = 100
    scene.render.fps = fps
    scene.render.fps_base = 1.0

    if file_format == 'FFMPEG':
        render.ffmpeg.format = 'MPEG4'
        render.ffmpeg.codec = codec               
        render.ffmpeg.constant_rate_factor = 'MEDIUM'
        render.ffmpeg.ffmpeg_preset = 'GOOD'
        render.ffmpeg.gopsize = 12
        render.ffmpeg.max_b_frames = 2
        render.ffmpeg.video_bitrate = 6000
        render.ffmpeg.audio_codec = 'NONE'

def render():
    bpy.ops.render.render(animation=True)
    print("EEVEE/EEVEE_NEXT render finished.")