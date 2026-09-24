import argparse
import os
from moviepy import VideoFileClip


def trim_video_by_frames(input_path: str, output_path: str,
                         start_frame: int, end_frame: int) -> None:
    """
    Trim a video between start_frame and end_frame (inclusive) and save it.

    Parameters
    ----------
    input_path : str
        Path to the input video file.
    output_path : str
        Path to the output (trimmed) video file.
    start_frame : int
        Index of the first frame to keep (0-based).
    end_frame : int
        Index of the last frame to keep (0-based, inclusive).
    """
    if start_frame < 0:
        raise ValueError("start_frame must be >= 0")
    if end_frame < start_frame:
        raise ValueError("end_frame must be >= start_frame")

    # Load video
    clip = VideoFileClip(input_path)
    fps = clip.fps

    # Compute max possible frame index
    max_frame = int(clip.duration * fps) - 1

    if start_frame > max_frame:
        raise ValueError(
            f"start_frame ({start_frame}) is beyond last frame ({max_frame})"
        )

    # Clamp end_frame to the video length if needed
    if end_frame > max_frame:
        print(f"Warning: end_frame ({end_frame}) > max_frame ({max_frame}), "
              f"clamping to {max_frame}")
        end_frame = max_frame

    # Convert frames to times (seconds)
    start_t = start_frame / fps
    # +1 so that end_frame is included (frames are [n/fps, (n+1)/fps))
    end_t = (end_frame + 1) / fps

    subclip = clip.subclipped(start_t, end_t)

    # Write out the result
    # You can tweak codec and bitrate here if needed
    subclip.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac"
    )

    clip.close()
    subclip.close()


def main():
    parser = argparse.ArgumentParser(
        description="Trim a video by start and end frame numbers."
    )
    parser.add_argument("input", help="Path to input video file")
    parser.add_argument("output", help="Path to output (trimmed) video file")
    parser.add_argument("start_frame", type=int, help="Start frame (0-based)")
    parser.add_argument("end_frame", type=int, help="End frame (0-based, inclusive)")

    args = parser.parse_args()

    if not os.path.isfile(args.input):
        raise FileNotFoundError(f"Input file not found: {args.input}")

    trim_video_by_frames(args.input, args.output, args.start_frame, args.end_frame)


if __name__ == "__main__":
    main()







