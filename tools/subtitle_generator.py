import os
import re
from typing import List, Dict

def clean_text(text: str) -> str:
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[\xa0\u2000-\u200b\u3000]', ' ', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

def split_text_to_subtitles(text: str, max_chars_per_line: int = 22, min_chars_per_line: int = 4) -> List[str]:
    """
    Splits text into concise subtitle lines based on punctuation and length constraints.
    """
    text = clean_text(text)
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    
    subtitles = []
    
    for p in paragraphs:
        # Split primarily by sentence terminators
        sentences = re.split(r'([。！？!?\n]+)', p)
        for i in range(0, len(sentences), 2):
            sent = sentences[i].strip()
            punct = sentences[i+1].strip() if i+1 < len(sentences) else ''
            full_sent = sent + punct
            if not full_sent:
                continue
                
            if len(full_sent) <= max_chars_per_line:
                subtitles.append(full_sent)
            else:
                # Sub-split by comma, semicolon, colon
                clauses = re.split(r'([，,；;：:、]+)', full_sent)
                current = ""
                for j in range(0, len(clauses), 2):
                    clause_text = clauses[j].strip()
                    clause_punct = clauses[j+1].strip() if j+1 < len(clauses) else ''
                    part = clause_text + clause_punct
                    if not part:
                        continue
                    if len(current) + len(part) <= max_chars_per_line:
                        current += part
                    else:
                        if current:
                            subtitles.append(current)
                        current = part
                if current:
                    subtitles.append(current)
                    
    # Merge tiny subtitles with next or previous if too short
    merged = []
    for sub in subtitles:
        sub = sub.strip()
        if not sub:
            continue
        if len(sub) < min_chars_per_line and merged and len(merged[-1]) + len(sub) <= max_chars_per_line:
            merged[-1] += sub
        else:
            merged.append(sub)
            
    return merged

def format_ass_time(seconds: float) -> str:
    """Formats float seconds into ASS time format: H:MM:SS.cs"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{hrs}:{mins:02d}:{secs:02d}.{cs:02d}"

def format_srt_time(seconds: float) -> str:
    """Formats float seconds into SRT time format: HH:MM:SS,mmm"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms >= 1000:
        ms = 999
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"

def calculate_time_allocations(subtitles: List[str], total_duration: float) -> List[Dict]:
    """
    Distributes total_duration across subtitles based on character count and punctuation weight.
    """
    weights = []
    for sub in subtitles:
        # Base weight on visible characters (excluding punctuations)
        char_count = len(re.sub(r'[^\w\u4e00-\u9fa5]', '', sub))
        if char_count == 0:
            char_count = max(1, len(sub))
            
        weight = float(char_count)
        if sub.endswith(('。', '！', '？', '!', '?')):
            weight += 1.8  # Longer pause at sentence end
        elif sub.endswith(('，', ',', '；', ';', '、')):
            weight += 0.9  # Moderate pause at clause break
            
        weights.append(weight)
        
    total_weight = sum(weights) if weights else 1.0
    
    allocations = []
    current_time = 0.0
    
    for i, sub in enumerate(subtitles):
        dur = (weights[i] / total_weight) * total_duration
        start_time = current_time
        end_time = current_time + dur
        
        # Add a tiny gap (e.g. 0.04s) between subtitles for clean transition
        gap = min(0.05, dur * 0.08)
        actual_end = max(start_time + 0.3, end_time - gap)
        
        allocations.append({
            "index": i + 1,
            "text": sub,
            "start": start_time,
            "end": actual_end,
            "duration": dur
        })
        current_time = end_time
        
    return allocations

def generate_ass_subtitles(
    allocations: List[Dict],
    output_ass_path: str,
    video_width: int = 1792,
    video_height: int = 1008,
    font_name: str = "PingFang SC, Source Han Sans CN, Microsoft YaHei, sans-serif",
    font_size: int = 62,
    primary_color: str = "&H00FFFFFF",      # Pure White (AABBGGRR)
    outline_color: str = "&H00141414",      # Dark Charcoal Outline
    shadow_color: str = "&H80000000",       # Semi-transparent Black Shadow
    fade_duration_ms: int = 120,            # Fade in/out animation
    vertical_margin: int = 0                # Center aligned by default (Alignment=5)
) -> str:
    """
    Generates an ASS subtitle file with smooth fade transitions and modern typography.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_ass_path)), exist_ok=True)
    
    # ASS Style configuration
    # Alignment: 5 = Center of the screen
    style_line = (
        f"Style: CenterStyle,{font_name},{font_size},{primary_color},&H000000FF,{outline_color},{shadow_color},"
        f"-1,0,0,0,100,100,0,0,1,3.2,1.8,5,30,30,{vertical_margin},1"
    )
    
    content = f"""[Script Info]
Title: Dynamic Centered Subtitles
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{style_line}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    for item in allocations:
        start_str = format_ass_time(item["start"])
        end_str = format_ass_time(item["end"])
        raw_text = item["text"]
        
        # Add smooth fade in and fade out tags
        effect_tag = f"{{\\fad({fade_duration_ms},{fade_duration_ms})}}"
        dialogue = f"Dialogue: 0,{start_str},{end_str},CenterStyle,,0,0,0,,{effect_tag}{raw_text}\n"
        content += dialogue
        
    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    return output_ass_path

def generate_srt_subtitles(allocations: List[Dict], output_srt_path: str) -> str:
    """Generates standard SRT subtitles."""
    os.makedirs(os.path.dirname(os.path.abspath(output_srt_path)), exist_ok=True)
    lines = []
    for item in allocations:
        lines.append(str(item["index"]))
        lines.append(f"{format_srt_time(item['start'])} --> {format_srt_time(item['end'])}")
        lines.append(item["text"])
        lines.append("")
    with open(output_srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return output_srt_path
