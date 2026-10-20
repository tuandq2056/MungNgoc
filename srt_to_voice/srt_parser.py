import re
from pathlib import Path
from dataclasses import dataclass


@dataclass
class SubtitleItem:
    index: int
    start_sec: float
    end_sec: float
    duration_sec: float
    text: str


def parse_timestamp_to_seconds(ts_str: str) -> float:
    """Chuyển đổi chuỗi HH:MM:SS,mmm hoặc HH:MM:SS.mmm sang số giây float."""
    ts_str = ts_str.strip().replace(",", ".")
    parts = ts_str.split(":")
    if len(parts) == 3:
        hours = float(parts[0])
        minutes = float(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    return 0.0


def is_chinese_text(text: str) -> bool:
    """Kiểm tra nếu chuỗi chủ yếu chứa ký tự chữ Hán (CJK)."""
    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", text))
    return cjk_count > 0 and (cjk_count / max(len(text), 1) > 0.4)


def extract_vietnamese_line(raw_text: str) -> str:
    """
    Nếu file srt là song ngữ (Dòng 1: Tiếng Trung, Dòng 2: Tiếng Việt),
    hàm sẽ thông minh lọc lấy dòng tiếng Việt để đọc.
    """
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    if not lines:
        return ""

    if len(lines) == 1:
        return lines[0]

    # Tìm dòng không phải tiếng Trung (chứa ký tự Latin / tiếng Việt)
    vn_lines = [line for line in lines if not is_chinese_text(line)]
    if vn_lines:
        return " ".join(vn_lines)

    # Nếu toàn tiếng Trung hoặc không phân biệt được, lấy dòng cuối cùng
    return lines[-1]


def parse_srt_file(srt_path: str | Path) -> list[SubtitleItem]:
    """
    Phân tích file .srt thành danh sách các SubtitleItem có mốc thời gian và nội dung sạch.
    """
    srt_path = Path(srt_path)
    if not srt_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file .srt: {srt_path}")

    with open(srt_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    # Tách các block subtitle bằng 2 dấu xuống dòng trở lên
    blocks = re.split(r"\n\s*\n", content.strip())
    items: list[SubtitleItem] = []

    time_pattern = re.compile(
        r"(\d{1,2}:\d{2}:\d{2}[,\.]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,\.]\d{1,3})"
    )

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 2:
            continue

        # Tìm dòng chứa mốc thời gian
        time_match = None
        time_line_idx = -1
        for i, line in enumerate(lines):
            match = time_pattern.search(line)
            if match:
                time_match = match
                time_line_idx = i
                break

        if not time_match:
            continue

        start_str, end_str = time_match.groups()
        start_sec = parse_timestamp_to_seconds(start_str)
        end_sec = parse_timestamp_to_seconds(end_str)
        duration_sec = max(0.0, end_sec - start_sec)

        # Lấy phần nội dung phía sau dòng thời gian
        text_lines = lines[time_line_idx + 1:]
        raw_text = "\n".join(text_lines)

        # Xóa các thẻ HTML (<i>, <b>, <font>...)
        clean_text = re.sub(r"<[^>]+>", "", raw_text).strip()
        
        # Trích xuất dòng tiếng Việt nếu là file song ngữ
        vn_text = extract_vietnamese_line(clean_text)

        if vn_text:
            idx = len(items) + 1
            items.append(
                SubtitleItem(
                    index=idx,
                    start_sec=start_sec,
                    end_sec=end_sec,
                    duration_sec=duration_sec,
                    text=vn_text,
                )
            )

    return items
