import os
import re
import argparse
from typing import List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps

DEFAULT_FONT_CANDIDATES = [
    ("/System/Library/Fonts/Supplemental/Songti.ttc", 0),  # Songti SC Black on macOS
    ("/System/Library/Fonts/Supplemental/Songti.ttc", 1),  # Songti SC Bold
    ("/System/Library/Fonts/PingFang.ttc", 2),             # PingFang Bold fallback
    ("/System/Library/Fonts/STHeiti Medium.ttc", 0),
]

COLOR_WHITE = (255, 255, 255)
COLOR_YELLOW = (252, 226, 26)  # Bright poster yellow matching reference image

def get_best_font(custom_font_path: Optional[str] = None):
    if custom_font_path and os.path.exists(custom_font_path):
        return custom_font_path, 0
    for path, idx in DEFAULT_FONT_CANDIDATES:
        if os.path.exists(path):
            return path, idx
    return None, 0

def parse_markdown_tokens(text: str) -> List[Tuple[str, bool]]:
    """
    Parses a string with markdown bold syntax into a list of (text_chunk, is_bold).
    e.g. '“**翻身**不需要**运气**”' -> [('“', False), ('翻身', True), ('不需要', False), ('运气', True), ('”', False)]
    """
    tokens = []
    pattern = re.compile(r"(\*\*.*?\*\*)")
    parts = pattern.split(text)
    for p in parts:
        if not p:
            continue
        if p.startswith("**") and p.endswith("**") and len(p) >= 4:
            tokens.append((p[2:-2], True))
        else:
            tokens.append((p, False))
    return tokens

def ensure_title_quotes(text: str) -> str:
    """
    Ensures that the entire title is wrapped in Chinese double quotes “ and ”.
    """
    stripped = text.strip()
    if not stripped.startswith("“") and not stripped.startswith('"'):
        stripped = "“" + stripped
    elif stripped.startswith('"'):
        stripped = "“" + stripped[1:]

    if not stripped.endswith("”") and not stripped.endswith('"'):
        stripped = stripped + "”"
    elif stripped.endswith('"'):
        stripped = stripped[:-1] + "”"

    return stripped

def process_portrait(
    portrait_path: str,
    target_width: int,
    grayscale: bool = True,
    contrast_factor: float = 1.35,
    brightness_factor: float = 1.05
) -> Image.Image:
    """
    Loads portrait, crops to non-transparent bbox, optionally converts to high-contrast B&W,
    and resizes to target width while maintaining aspect ratio.
    """
    if not os.path.exists(portrait_path):
        raise FileNotFoundError(f"Portrait not found: {portrait_path}")

    img = Image.open(portrait_path).convert("RGBA")
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    if grayscale:
        r, g, b, a = img.split()
        rgb = Image.merge("RGB", (r, g, b))
        gray = ImageOps.grayscale(rgb)
        enh = ImageEnhance.Contrast(gray).enhance(contrast_factor)
        enh = ImageEnhance.Brightness(enh).enhance(brightness_factor)
        img = Image.merge("RGBA", (enh, enh, enh, a))

    scale = target_width / img.width
    target_height = int(img.height * scale)
    return img.resize((target_width, target_height), Image.Resampling.LANCZOS)

def build_cover(
    title: str = "“**翻身**\n不需要**运气**”",
    author: str = "--查理芒格",
    portrait_path: str = "munger-nobg.png",
    output_path: str = "cover.png",
    width: int = 1792,
    height: int = 1008,
    portrait_width_ratio: float = 0.40,
    grayscale_portrait: bool = True,
    font_normal_size: int = 115,
    font_large_size: int = 165,
    author_size: int = 65,
    left_margin: int = 180,
    line_spacing: int = 45,
    author_gap: int = 60,
    font_path: Optional[str] = None
) -> str:
    """
    Renders high-production video cover based on minimalist dark poster aesthetic.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 255))

    # 1. Place portrait on right side
    target_pw = int(width * portrait_width_ratio)
    portrait_img = process_portrait(
        portrait_path=portrait_path,
        target_width=target_pw,
        grayscale=grayscale_portrait
    )
    px = width - portrait_img.width + 10
    py = height - portrait_img.height
    canvas.alpha_composite(portrait_img, (px, py))

    # 2. Prepare typography
    f_path, f_idx = get_best_font(font_path)
    if not f_path:
        raise RuntimeError("No suitable Chinese font found on system.")

    f_norm = ImageFont.truetype(f_path, font_normal_size, index=f_idx)
    f_large = ImageFont.truetype(f_path, font_large_size, index=f_idx)
    f_auth = ImageFont.truetype(f_path, author_size, index=f_idx)

    # 3. Format title lines
    raw_title = ensure_title_quotes(title)
    # Split by newline if present
    if "\n" in raw_title:
        lines = [line.strip() for line in raw_title.split("\n") if line.strip()]
    else:
        # If single line without newline, check if auto-wrapping looks better
        # or keep single line
        lines = [raw_title]

    # Format author line (standardize Chinese em-dash if user entered --)
    formatted_author = author.strip()
    if formatted_author.startswith("--"):
        formatted_author = "——" + formatted_author[2:].lstrip()
    elif not formatted_author.startswith("——") and not formatted_author.startswith("-"):
        formatted_author = "——" + formatted_author

    # 4. Measure lines
    large_ascent, large_descent = f_large.getmetrics()
    line_blocks = []
    total_title_h = 0

    for l_str in lines:
        tokens = parse_markdown_tokens(l_str)
        items = []
        line_w = 0
        for text_chunk, is_bold in tokens:
            f = f_large if is_bold else f_norm
            bbox = f.getbbox(text_chunk)
            tw = bbox[2] - bbox[0]
            items.append({
                "text": text_chunk,
                "is_bold": is_bold,
                "font": f,
                "width": tw
            })
            line_w += tw
        line_h = large_ascent + large_descent
        line_blocks.append({"items": items, "width": line_w, "height": line_h})
        total_title_h += line_h

    total_title_h += line_spacing * (len(lines) - 1)

    auth_bbox = f_auth.getbbox(formatted_author)
    auth_h = auth_bbox[3] - auth_bbox[1]
    overall_h = total_title_h + author_gap + auth_h

    # Vertically center the entire text block on canvas
    start_y = (height - overall_h) // 2

    # 5. Draw text with baseline alignment
    draw = ImageDraw.Draw(canvas)
    curr_y = start_y

    for l_block in line_blocks:
        curr_x = left_margin
        baseline_y = curr_y + large_ascent

        for item in l_block["items"]:
            f = item["font"]
            is_bold = item["is_bold"]
            color = COLOR_YELLOW if is_bold else COLOR_WHITE
            ascent, descent = f.getmetrics()

            # Align bottom baselines
            ty = baseline_y - ascent
            draw.text((curr_x, ty), item["text"], font=f, fill=color)
            curr_x += item["width"]

        curr_y += l_block["height"] + line_spacing

    # Draw Author
    curr_y += author_gap - line_spacing
    draw.text((left_margin, curr_y), formatted_author, font=f_auth, fill=COLOR_WHITE)

    canvas.save(output_path, "PNG")
    print(f"[CoverBuilder] Cover saved successfully -> {output_path}")
    return output_path

if __name__ == "__main__":
    import sys
    known_flags = {"--help", "-h", "--title", "--author", "--portrait", "--output", "--color", "--single_line"}
    new_argv = []
    skip = False
    for i in range(len(sys.argv)):
        if skip:
            skip = False
            continue
        curr = sys.argv[i]
        if curr in {"--author", "--title"} and i + 1 < len(sys.argv):
            nxt = sys.argv[i+1]
            if nxt.startswith("-") and nxt not in known_flags:
                new_argv.append(f"{curr}={nxt}")
                skip = True
                continue
        new_argv.append(curr)
    sys.argv = new_argv

    parser = argparse.ArgumentParser(description="Generate YouTube/Podcast video cover.")
    parser.add_argument("--title", default="“**翻身**\n不需要**运气**”", help="Cover title with markdown **bold** syntax")
    parser.add_argument("--author", default="--查理芒格", help="Author attribution text")
    parser.add_argument("--portrait", default="munger-nobg.png", help="Path to character portrait PNG")
    parser.add_argument("--output", default="cover.png", help="Output path for cover image")
    parser.add_argument("--color", action="store_true", help="Keep portrait original color (default is high-contrast B&W)")
    parser.add_argument("--single_line", action="store_true", help="Force title on single line")
    args = parser.parse_args()

    title_input = args.title
    if args.single_line:
        title_input = title_input.replace("\n", "")

    build_cover(
        title=title_input,
        author=args.author,
        portrait_path=args.portrait,
        output_path=args.output,
        grayscale_portrait=not args.color
    )
