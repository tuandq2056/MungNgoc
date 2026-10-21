import os
import subprocess
from pathlib import Path
from typing import Optional


def dub_video(
    video_path: str | Path,
    voice_audio_path: str | Path,
    output_path: Optional[str | Path] = None,
    bg_volume_db: str = "-3dB",
    voice_volume_db: str = "0dB",
) -> Path:
    """
    Hòa âm và lồng tiếng file audio vào video gốc.

    Args:
        video_path: Đường dẫn video gốc.
        voice_audio_path: Đường dẫn file audio lồng tiếng.
        output_path: Đường dẫn file video xuất ra (mặc định lưu vào thư mục 'output/').
        bg_volume_db: Mức điều chỉnh âm lượng nền (ví dụ: -3dB, -4dB, -6dB).
        voice_volume_db: Âm lượng giọng đọc (mặc định: 0dB).

    Returns:
        Đường dẫn file video hoàn chỉnh sau khi lồng tiếng.
    """
    video_path = Path(video_path).resolve()
    voice_audio_path = Path(voice_audio_path).resolve()

    if not video_path.exists():
        raise FileNotFoundError(f"Không tìm thấy video: {video_path}")
    if not voice_audio_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file voice: {voice_audio_path}")

    # Chuẩn hóa format dB
    if not bg_volume_db.lower().endswith("db"):
        bg_volume_db = f"{bg_volume_db}dB"
    if not voice_volume_db.lower().endswith("db"):
        voice_volume_db = f"{voice_volume_db}dB"

    if output_path is None:
        out_dir = video_path.parent.parent / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{video_path.stem}_dubbed.mp4"
    else:
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

    tmp_file = out_file.with_name(f"{out_file.stem}.part{out_file.suffix}")

    print(f"\n[video_dubber] === Lồng tiếng video: {video_path.name} ===")
    print(f"[video_dubber] File voice: {voice_audio_path.name}")
    print(f"[video_dubber] Âm lượng nền gốc: {bg_volume_db} | Âm lượng voice: {voice_volume_db}")
    print(f"[video_dubber] Xuất video: {out_file}")

    # Lệnh hòa âm FFmpeg stream copy video
    filter_complex = (
        f"[0:a]volume={bg_volume_db}[bg];"
        f"[1:a]volume={voice_volume_db}[fg];"
        f"[bg][fg]amix=inputs=2:duration=first:dropout_transition=0:weights=1 1[aout]"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-nostdin",
        "-i", str(video_path),
        "-i", str(voice_audio_path),
        "-filter_complex", filter_complex,
        "-map", "0:v:0",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        str(tmp_file),
    ]

    # Ghi ra file tạm rồi mới đổi tên: nếu ffmpeg chết giữa chừng thì không để lại file dở dang mang tên thật
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Lỗi FFmpeg khi lồng tiếng: {res.stderr}")
        os.replace(tmp_file, out_file)
    finally:
        tmp_file.unlink(missing_ok=True)

    print(f"[video_dubber] [V] Đã hoàn thành lồng tiếng video: {out_file}")
    return out_file
