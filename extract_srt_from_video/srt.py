from dataclasses import dataclass
from pathlib import Path


@dataclass
class SrtEntry:
    index: int
    start_sec: float
    end_sec: float
    text: str


def format_timestamp(seconds: float) -> str:
    """Chuyển đổi giây dạng float thành định dạng thời gian chuẩn SRT: HH:MM:SS,mmm."""
    if seconds < 0:
        seconds = 0.0

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))

    if millis >= 1000:
        secs += 1
        millis = 0
    if secs >= 60:
        minutes += 1
        secs = 0
    if minutes >= 60:
        hours += 1
        minutes = 0

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt_file(entries: list[SrtEntry], output_file: str | Path):
    """Ghi danh sách SrtEntry ra file .srt theo định dạng chuẩn."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for entry in entries:
            start_str = format_timestamp(entry.start_sec)
            end_str = format_timestamp(entry.end_sec)
            f.write(f"{entry.index}\n")
            f.write(f"{start_str} --> {end_str}\n")
            f.write(f"{entry.text}\n\n")
