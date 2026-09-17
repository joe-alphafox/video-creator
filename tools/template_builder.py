import os
import subprocess
import shutil
from PIL import Image

def find_ffmpeg_bin():
    candidates = [
        shutil.which("ffmpeg"),
        "/opt/homebrew/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return "ffmpeg"

def build_background_template(
    bg_path: str = "bg.jpg",
    overlay_path: str = "munger-nobg.png",
    output_path: str = "template.png",
    target_width: int = 1792,
    target_height: int = 1008,
    overlay_target_height: int = 900,
    margin_right: int = -30,
    margin_bottom: int = 0
) -> str:
    """
    Combines background image and transparent portrait.
    Scales portrait to overlay_target_height (slightly smaller than background height)
    and places it at the bottom-right corner.
    """
    if not os.path.exists(bg_path):
        raise FileNotFoundError(f"Background image not found: {bg_path}")
    if not os.path.exists(overlay_path):
        raise FileNotFoundError(f"Overlay image not found: {overlay_path}")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    bg = Image.open(bg_path).convert("RGBA")
    if bg.size != (target_width, target_height):
        bg = bg.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
    overlay = Image.open(overlay_path).convert("RGBA")
    
    # Scale overlay to desired height (e.g. 900, slightly less than 1008)
    scale = overlay_target_height / overlay.height
    new_w = int(overlay.width * scale)
    new_h = overlay_target_height
    overlay_scaled = overlay.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # Position at bottom-right
    pos_x = target_width - new_w - margin_right
    pos_y = target_height - new_h - margin_bottom
    
    composite = bg.copy()
    composite.alpha_composite(overlay_scaled, (pos_x, pos_y))
    
    composite.convert("RGB").save(output_path, "PNG")
    print(f"[TemplateBuilder] Generated template: {output_path} (Overlay scaled to {new_w}x{new_h})")
    return output_path

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build composite background template")
    parser.add_argument("--bg", default="bg.jpg", help="Path to background image")
    parser.add_argument("--overlay", default="munger-nobg.png", help="Path to portrait PNG")
    parser.add_argument("--output", default="template.png", help="Path to output template")
    parser.add_argument("--overlay_height", type=int, default=900, help="Target height for portrait")
    args = parser.parse_args()

    build_background_template(args.bg, args.overlay, args.output, overlay_target_height=args.overlay_height)
    print("Done!")
