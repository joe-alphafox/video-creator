import os
import shutil
from typing import List, Dict
from PIL import Image, ImageDraw, ImageFont

def get_best_chinese_font(font_size: int):
    candidates = [
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Supplemental/Songti.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, font_size)
            except Exception:
                continue
    return ImageFont.load_default()

def wrap_text_two_lines(text: str, max_chars_per_line: int = 11) -> List[str]:
    """
    Wraps text into at most two balanced lines.
    Prefers splitting at punctuation marks near the center.
    """
    text = text.strip()
    if len(text) <= max_chars_per_line:
        return [text]
        
    mid = len(text) // 2
    best_split = -1
    min_dist = 999
    
    # Check for punctuation near center
    for i, ch in enumerate(text):
        if ch in '，,；;、 ':
            dist = abs(i + 1 - mid)
            if dist < min_dist:
                min_dist = dist
                best_split = i + 1
                
    if best_split != -1 and 3 <= best_split <= len(text) - 3:
        line1 = text[:best_split].strip()
        line2 = text[best_split:].strip()
        return [line1, line2]
        
    # Split directly at middle if no punctuation found
    line1 = text[:mid].strip()
    line2 = text[mid:].strip()
    return [line1, line2]

def render_slides(
    template_path: str,
    allocations: List[Dict],
    output_dir: str,
    font_size: int = 48,
    x_ratio: float = 0.32,
    y_ratio: float = 0.45,
    max_chars_single_line: int = 11,
    card_bg_rgba=(220, 225, 230, 135),
    card_border_rgba=(0, 0, 0, 255),
    border_width: int = 2,
    text_color=(255, 255, 255, 255),
    text_stroke_color=(0, 0, 0, 255),
    text_stroke_width: int = 2,
    pad_x: int = 24,
    pad_y: int = 26,
    line_gap: int = 14,
    radius: int = 16
) -> List[str]:
    """
    Renders high-resolution lossless PNG slides with compact 70% width cards.
    Long subtitles automatically split into two balanced lines.
    Preserves 100% of the template outside the subtitle card area.
    """
    os.makedirs(output_dir, exist_ok=True)
    base_img = Image.open(template_path).convert("RGBA")
    w, h = base_img.size
    
    font = get_best_chinese_font(font_size)
    center_x = int(w * x_ratio)
    center_y = int(h * y_ratio)

    image_paths = []
    
    for item in allocations:
        idx = item["index"]
        raw_text = item["text"]
        out_file = os.path.join(output_dir, f"slide_{idx:04d}.png")
        
        # Split text into 1 or 2 lines
        lines = wrap_text_two_lines(raw_text, max_chars_single_line)
        
        # Measure line dimensions
        line_bboxes = [font.getbbox(line) for line in lines]
        line_widths = [b[2] - b[0] for b in line_bboxes]
        line_heights = [b[3] - b[1] for b in line_bboxes]
        
        max_line_w = max(line_widths)
        total_text_h = sum(line_heights) + line_gap * (len(lines) - 1)
        
        # Calculate compact card bounding box (70% of previous width)
        card_left = center_x - max_line_w // 2 - pad_x
        card_top = center_y - total_text_h // 2 - pad_y
        card_right = center_x + max_line_w // 2 + pad_x
        card_bottom = center_y + total_text_h // 2 + pad_y
        
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # 1. Light gray translucent background with black border
        draw.rounded_rectangle(
            [card_left, card_top, card_right, card_bottom],
            radius=radius,
            fill=card_bg_rgba,
            outline=card_border_rgba,
            width=border_width
        )
        
        # 2. Render each line centered horizontally inside the card
        curr_y = center_y - total_text_h // 2
        for j, line in enumerate(lines):
            lw = line_widths[j]
            lh = line_heights[j]
            b = line_bboxes[j]
            lx = center_x - lw // 2 - b[0]
            ly = curr_y - b[1]
            
            draw.text(
                (lx, ly),
                line,
                font=font,
                fill=text_color,
                stroke_width=text_stroke_width,
                stroke_fill=text_stroke_color
            )
            curr_y += lh + line_gap
            
        # Composite: outside card area is 100% untouched template
        final_img = Image.alpha_composite(base_img, overlay)
        final_img.convert("RGB").save(out_file, "PNG")
        image_paths.append(out_file)
        
    return image_paths
