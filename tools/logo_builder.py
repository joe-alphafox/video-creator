import os
import math
from PIL import Image, ImageDraw

def build_circular_avatar_logo(
    portrait_path: str = "munger-nobg.png",
    output_path: str = "logo_avatar.png",
    target_diameter: int = 120,
    head_cx: int = 415,
    head_cy: int = 365
) -> str:
    """
    Crops person's head into a circular badge with double metallic outer rings.
    Places the circle centered in a canvas large enough to prevent cropping when rotated at any angle.
    """
    if not os.path.exists(portrait_path):
        raise FileNotFoundError(f"Portrait not found: {portrait_path}")

    im = Image.open(portrait_path).convert("RGBA")
    
    # Crop head
    r = 155
    size = r * 2
    box = (head_cx - r, head_cy - r, head_cx + r, head_cy + r)
    crop_img = im.crop(box)

    # Base circular disk
    badge = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    badge_draw = ImageDraw.Draw(badge)
    badge_draw.ellipse((0, 0, size, size), fill=(24, 28, 36, 240))

    # Circular mask for head
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((4, 4, size - 4, size - 4), fill=255)
    badge.paste(crop_img, (0, 0), mask=mask)

    # Double sleek border rings
    draw = ImageDraw.Draw(badge)
    draw.ellipse((1, 1, size - 2, size - 2), outline=(255, 255, 255, 220), width=4)
    draw.ellipse((6, 6, size - 7, size - 7), outline=(210, 215, 225, 120), width=2)

    # Resize badge to target_diameter
    badge_scaled = badge.resize((target_diameter, target_diameter), Image.Resampling.LANCZOS)

    # Safe square canvas for rotation (diagonal = target_diameter * sqrt(2))
    canvas_size = int(math.ceil(target_diameter * math.sqrt(2))) + 4
    safe_canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    offset = (canvas_size - target_diameter) // 2
    safe_canvas.paste(badge_scaled, (offset, offset))

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    safe_canvas.save(output_path, "PNG")
    print(f"[LogoBuilder] Created rotating circular avatar logo -> {output_path} (diameter: {target_diameter}px, canvas: {canvas_size}px)")
    return output_path

if __name__ == "__main__":
    build_circular_avatar_logo()
