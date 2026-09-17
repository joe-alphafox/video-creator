#!/usr/bin/env python3
import sys
import argparse
from tools.cover_builder import build_cover

def preprocess_args(argv):
    """
    Handles option values starting with dashes (e.g. --author --查理芒格)
    so argparse does not misinterpret them as unknown flags.
    """
    known_flags = {"--help", "-h", "--title", "--author", "--portrait", "--output", "--color", "--single_line", "--font_normal", "--font_large", "--author_size", "--portrait_ratio", "--aspect", "--width", "--height"}
    new_argv = []
    skip = False
    for i in range(len(argv)):
        if skip:
            skip = False
            continue
        curr = argv[i]
        if curr in {"--author", "--title"} and i + 1 < len(argv):
            nxt = argv[i+1]
            if nxt.startswith("-") and nxt not in known_flags:
                new_argv.append(f"{curr}={nxt}")
                skip = True
                continue
        new_argv.append(curr)
    return new_argv

def main():
    sys.argv = preprocess_args(sys.argv)
    parser = argparse.ArgumentParser(
        description="Generate high-production YouTube/Podcast cover thumbnail based on dark poster aesthetic."
    )
    parser.add_argument("--title", default="“**翻身**\n不需要**运气**”", help="Cover title text with markdown **bold** syntax (use \\n for line breaks)")
    parser.add_argument("--author", default="--查理芒格", help="Author attribution text (default: --查理芒格)")
    parser.add_argument("--portrait", default="munger-nobg.png", help="Path to portrait PNG (default: munger-nobg.png)")
    parser.add_argument("--output", default="cover.png", help="Output cover image path (default: cover.png)")
    parser.add_argument("--color", action="store_true", help="Keep portrait in original color (default is high-contrast black & white)")
    parser.add_argument("--single_line", action="store_true", help="Force title on a single line instead of 2 lines")
    parser.add_argument("--font_normal", type=int, default=115, help="Normal text font size (default: 115)")
    parser.add_argument("--font_large", type=int, default=165, help="Highlighted yellow bold text font size (default: 165)")
    parser.add_argument("--author_size", type=int, default=65, help="Author text font size (default: 65)")
    parser.add_argument("--portrait_ratio", type=float, default=0.40, help="Portrait width ratio of canvas (default: 0.40)")
    parser.add_argument("--aspect", default="4:3", help='Canvas aspect ratio like "4:3", "16:9", "1:1", "3:4" (default: "4:3")')
    parser.add_argument("--width", type=int, default=None, help="Explicit canvas width (must be used together with --height)")
    parser.add_argument("--height", type=int, default=None, help="Explicit canvas height (must be used together with --width)")
    args = parser.parse_args()

    title_input = args.title
    # Handle escaped \n if passed from shell
    title_input = title_input.replace("\\n", "\n")

    if args.single_line:
        title_input = title_input.replace("\n", "")
    elif "\n" not in title_input:
        # If no newline provided and not forced single line, check if we should auto-split into 2 lines
        # e.g. "“**翻身**不需要**运气**”" -> "“**翻身**\n不需要**运气**”"
        import re
        bold_matches = list(re.finditer(r"\*\*.*?\*\*", title_input))
        if len(bold_matches) >= 2:
            split_pos = bold_matches[0].end()
            title_input = title_input[:split_pos] + "\n" + title_input[split_pos:].lstrip()

    output_path = build_cover(
        title=title_input,
        author=args.author,
        portrait_path=args.portrait,
        output_path=args.output,
        width=args.width,
        height=args.height,
        aspect=args.aspect,
        grayscale_portrait=not args.color,
        font_normal_size=args.font_normal,
        font_large_size=args.font_large,
        author_size=args.author_size,
        portrait_width_ratio=args.portrait_ratio
    )
    print(f"Cover ready: {output_path}")

if __name__ == "__main__":
    main()
