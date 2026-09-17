#!/usr/bin/env python3
import os
import sys
import argparse
import time
import shutil

from tools.template_builder import build_background_template
from tools.logo_builder import build_circular_avatar_logo
from tools.subtitle_generator import (
    split_text_to_subtitles,
    calculate_time_allocations,
    generate_ass_subtitles,
    generate_srt_subtitles
)
from tools.slide_renderer import render_slides
from tools.video_renderer import (
    get_audio_duration,
    render_slides_concat_video,
    find_binary
)

def main():
    parser = argparse.ArgumentParser(
        description="Video Creator: Generates talking-head presentation video with dynamic subtitles."
    )
    parser.add_argument("--bg", default="bg.jpg", help="Path to background image")
    parser.add_argument("--overlay", default="munger-nobg.png", help="Path to overlay portrait PNG")
    parser.add_argument("--audio", default="翻身不需要运气_音色2_Qwen3-TTS_28分21秒.mp3", help="Path to audio file")
    parser.add_argument("--text", default="翻身不需要运气.txt", help="Path to subtitle script text file")
    parser.add_argument("--duration", type=float, default=None, help="Target duration in seconds (e.g. 30 for sample)")
    parser.add_argument("--output", default=None, help="Output video file path (e.g. output_sample_30s.mp4)")
    parser.add_argument("--font_size", type=int, default=48, help="Subtitle font size (default: 48)")
    parser.add_argument("--max_chars", type=int, default=16, help="Max characters per subtitle line (default: 16)")
    parser.add_argument("--overlay_height", type=int, default=900, help="Portrait height in template (default: 900)")
    parser.add_argument("--no_logo", action="store_true", help="Disable rotating logo in top-left")
    parser.add_argument("--logo_period", type=float, default=10.0, help="Rotation period for logo in seconds (default: 10.0)")
    parser.add_argument("--tv_range", action="store_true", help="Encode conventional limited 16-235 video range instead of passing the template's full 0-255 tone through unchanged")
    parser.add_argument("--rebuild_template", action="store_true", help="Force rebuild background template")
    args = parser.parse_args()

    # Step 0: Validate paths
    for req_file in [args.bg, args.overlay, args.audio, args.text]:
        if not os.path.exists(req_file):
            print(f"[Error] Required file not found: {req_file}")
            sys.exit(1)

    ffmpeg_bin = find_binary("ffmpeg")
    ffprobe_bin = find_binary("ffprobe")
    print("=" * 65)
    print("  AlphaFox Video Creator - Production Pipeline")
    print(f"  FFmpeg Binary : {ffmpeg_bin}")
    print(f"  FFprobe Binary: {ffprobe_bin}")
    print("=" * 65)

    # Step 1: Background Template
    template_path = "template.png"
    if not os.path.exists(template_path) or args.rebuild_template:
        print("\n>>> Step 1: Building Background Template...")
        build_background_template(
            bg_path=args.bg,
            overlay_path=args.overlay,
            output_path=template_path,
            target_width=1792,
            target_height=1008,
            overlay_target_height=args.overlay_height
        )
    else:
        print(f"\n>>> Step 1: Reusing existing template: {template_path}")

    # Step 1.5: Rotating Circular Logo
    logo_path = "logo_avatar.png"
    if not args.no_logo:
        if not os.path.exists(logo_path) or args.rebuild_template:
            print("\n>>> Step 1.5: Building Rotating Circular Logo...")
            build_circular_avatar_logo(
                portrait_path=args.overlay,
                output_path=logo_path,
                target_diameter=120
            )
        else:
            print(f"\n>>> Step 1.5: Reusing existing rotating logo: {logo_path}")

    # Step 2: Audio duration
    print("\n>>> Step 2: Analyzing Audio Track...")
    total_audio_sec = get_audio_duration(args.audio, ffprobe_bin=ffprobe_bin)
    print(f"Total audio duration: {total_audio_sec:.2f}s ({total_audio_sec/60:.2f} minutes)")

    is_sample = args.duration is not None and args.duration > 0
    target_duration = args.duration if is_sample else total_audio_sec
    print(f"Rendering mode: {'SAMPLE (' + str(target_duration) + 's)' if is_sample else 'FULL VIDEO'}")

    # Step 3: Subtitles generation
    print("\n>>> Step 3: Generating Subtitle Allocations...")
    with open(args.text, "r", encoding="utf-8") as f:
        full_text = f.read()

    # Split into lines
    all_subtitles = split_text_to_subtitles(full_text, max_chars_per_line=args.max_chars)
    print(f"Total subtitle lines in script: {len(all_subtitles)}")

    full_allocations = calculate_time_allocations(all_subtitles, total_audio_sec)

    if is_sample:
        target_allocations = []
        for item in full_allocations:
            if item["start"] < target_duration:
                capped = dict(item)
                if capped["end"] > target_duration:
                    capped["end"] = target_duration
                    capped["duration"] = target_duration - capped["start"]
                target_allocations.append(capped)
        tag = f"sample_{int(target_duration)}s"
    else:
        target_allocations = full_allocations
        tag = "full"

    # Export SRT for user convenience
    srt_path = f"subtitles_{tag}.srt"
    generate_srt_subtitles(target_allocations, srt_path)
    print(f"Subtitles exported: {srt_path} ({len(target_allocations)} lines)")

    # Step 4: Render subtitle slide frames
    print(f"\n>>> Step 4: Rendering {len(target_allocations)} Subtitle Slide Frames...")
    frames_dir = os.path.join("build", f"frames_{tag}")
    slide_paths = render_slides(
        template_path=template_path,
        allocations=target_allocations,
        output_dir=frames_dir,
        font_size=args.font_size
    )
    print(f"Frames rendered to: {frames_dir}")

    # Step 5: Video Rendering
    print("\n>>> Step 5: Assembling Video with FFmpeg & Hardware Acceleration...")
    default_output = f"output_{tag}.mp4"
    output_mp4 = args.output or default_output

    t0 = time.time()
    render_slides_concat_video(
        allocations=target_allocations,
        slide_image_paths=slide_paths,
        audio_path=args.audio,
        output_mp4_path=output_mp4,
        target_duration=target_duration if is_sample else None,
        spinning_logo_path=None if args.no_logo else logo_path,
        logo_pos_x=45,
        logo_pos_y=45,
        rotate_period_sec=args.logo_period,
        ffmpeg_bin=ffmpeg_bin,
        full_range=not args.tv_range
    )
    t_cost = time.time() - t0

    print("\n" + "=" * 65)
    print("  Video Rendering Completed Successfully!")
    print(f"  Output Video : {output_mp4}")
    print(f"  Subtitles SRT: {srt_path}")
    print(f"  Render Time  : {t_cost:.2f}s (Speed: {target_duration/t_cost:.2f}x real-time)")
    print("=" * 65)

if __name__ == "__main__":
    main()
