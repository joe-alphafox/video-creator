import os
import subprocess
import shutil
from typing import List, Dict

def find_binary(name: str) -> str:
    candidates = [
        shutil.which(name),
        f"/opt/homebrew/bin/{name}",
        f"/opt/homebrew/opt/ffmpeg/bin/{name}",
        f"/usr/local/bin/{name}"
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return name

def get_audio_duration(audio_path: str, ffprobe_bin: str = None) -> float:
    """Returns duration of an audio file in seconds."""
    bin_path = ffprobe_bin or find_binary("ffprobe")
    cmd = [
        bin_path, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    return float(result.stdout.strip())

def check_videotoolbox_available(ffmpeg_bin: str) -> bool:
    try:
        res = subprocess.run([ffmpeg_bin, "-encoders"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return "h264_videotoolbox" in res.stdout
    except Exception:
        return False

def render_slides_concat_video(
    allocations: List[Dict],
    slide_image_paths: List[str],
    audio_path: str,
    output_mp4_path: str,
    target_duration: float = None,
    spinning_logo_path: str = None,
    logo_pos_x: int = 40,
    logo_pos_y: int = 40,
    rotate_period_sec: float = 10.0,
    ffmpeg_bin: str = None,
    fps: int = 30
) -> str:
    """
    Renders video with accurate BT.709 colorspace, VUI tags, and an optional rotating circular avatar logo in top-left.
    """
    bin_path = ffmpeg_bin or find_binary("ffmpeg")
    os.makedirs(os.path.dirname(os.path.abspath(output_mp4_path)), exist_ok=True)
    
    # 1. Generate ffconcat script
    concat_file = output_mp4_path + ".ffconcat.txt"
    with open(concat_file, "w", encoding="utf-8") as f:
        f.write("ffconcat version 1.0\n")
        for i, item in enumerate(allocations):
            dur = item["duration"]
            img_path = os.path.abspath(slide_image_paths[i])
            f.write(f"file '{img_path}'\n")
            f.write(f"duration {dur:.3f}\n")
        if slide_image_paths:
            last_img = os.path.abspath(slide_image_paths[-1])
            f.write(f"file '{last_img}'\n")
            
    use_videotoolbox = check_videotoolbox_available(bin_path)
    
    # 2. Build FFmpeg command
    cmd = [
        bin_path, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file
    ]
    
    has_spinning_logo = spinning_logo_path and os.path.exists(spinning_logo_path)
    if has_spinning_logo:
        cmd.extend(["-loop", "1", "-i", spinning_logo_path])
        
    cmd.extend(["-i", audio_path])
    
    if target_duration is not None and target_duration > 0:
        cmd.extend(["-ss", "0", "-t", str(target_duration)])
        
    # Construct filter_complex
    if has_spinning_logo:
        # Input 0: slides, Input 1: logo, Input 2: audio
        # Using fps={fps} on [0:v] ensures a continuous 30fps stream drives the rotation smoothly every frame
        filter_str = (
            f"[0:v]fps={fps},scale=in_range=pc:out_range=tv:in_color_matrix=bt709:out_color_matrix=bt709,format=yuv420p[base];"
            f"[1:v]format=rgba,rotate=2*PI*t/{rotate_period_sec}:c=none:ow=iw:oh=ih[spin];"
            f"[base][spin]overlay={logo_pos_x}:{logo_pos_y}:shortest=1[outv]"
        )
        cmd.extend(["-filter_complex", filter_str, "-map", "[outv]", "-map", "2:a"])
    else:
        vf_filter = f"fps={fps},scale=in_range=pc:out_range=tv:in_color_matrix=bt709:out_color_matrix=bt709,format=yuv420p"
        cmd.extend(["-vf", vf_filter, "-map", "0:v", "-map", "1:a"])
        
    cmd.extend([
        "-r", str(fps),
        "-color_range", "tv",
        "-colorspace", "bt709",
        "-color_primaries", "bt709",
        "-color_trc", "bt709",
        "-movflags", "+faststart",
        "-bsf:v", "h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1:video_full_range_flag=0"
    ])
    
    if use_videotoolbox:
        cmd.extend(["-c:v", "h264_videotoolbox", "-b:v", "4000k"])
    else:
        cmd.extend(["-c:v", "libx264", "-preset", "veryfast", "-crf", "18"])
        
    cmd.extend([
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        output_mp4_path
    ])
    
    print(f"[VideoRenderer] Rendering video -> {output_mp4_path}")
    print(f"[VideoRenderer] Encoder: {'h264_videotoolbox (Hardware)' if use_videotoolbox else 'libx264'}")
    print(f"[VideoRenderer] Color Profile: BT.709 Standard (VUI calibrated)")
    if has_spinning_logo:
        print(f"[VideoRenderer] Rotating Logo: Enabled (Period: {rotate_period_sec}s, Position: {logo_pos_x},{logo_pos_y})")
    if target_duration:
        print(f"[VideoRenderer] Target Duration: {target_duration:.2f}s")
        
    subprocess.run(cmd, check=True)
    
    if os.path.exists(concat_file):
        os.remove(concat_file)
        
    return output_mp4_path
