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
    Lồng tiếng file audio (.mp3 / .wav) vào video gốc, tự động hòa âm (amix)
    với âm lượng nền giảm theo cấu hình (mặc định -3dB).

    Args:
        video_path: Đường dẫn video gốc.
        voice_audio_path: Đường dẫn file âm thanh lồng tiếng (.mp3 hoặc .wav).
        output_path: Đường dẫn file video xuất ra (mặc định lưu vào thư mục 'output/').
        bg_volume_db: Độ giảm âm lượng của âm thanh gốc (ví dụ: -3dB, -4dB, -6dB).
        voice_volume_db: Âm lượng của file lồng tiếng (mặc định: 0dB).

    Returns:
        Đường dẫn file video hoàn chỉnh sau khi lồng tiếng.
    """
    video_path = Path(video_path).resolve()
    voice_audio_path = Path(voice_audio_path).resolve()

    if not video_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file video: {video_path}")
    if not voice_audio_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file voice: {voice_audio_path}")

    # Chuẩn hóa giá trị dB
    if not bg_volume_db.endswith("dB") and not bg_volume_db.endswith("db"):
        bg_volume_db = f"{bg_volume_db}dB"
    if not voice_volume_db.endswith("dB") and not voice_volume_db.endswith("db"):
        voice_volume_db = f"{voice_volume_db}dB"

    # Xác định đường dẫn file đầu ra
    if output_path is None:
        out_dir = video_path.parent.parent / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{video_path.stem}_dubbed.mp4"
    else:
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n[dubber] === Đang lồng tiếng vào video: {video_path.name} ===")
    print(f"[dubber] File voice: {voice_audio_path.name}")
    print(f"[dubber] Âm lượng gốc: {bg_volume_db} | Âm lượng voice: {voice_volume_db}")
    print(f"[dubber] Đầu ra: {out_file}")

    # Lệnh ffmpeg hòa âm:
    # 1. Video copy stream 0:v:0 (không encode lại hình ảnh -> tốc độ cực nhanh, giữ nguyên 100% chất lượng)
    # 2. Âm thanh gốc giảm theo bg_volume_db (ví dụ: -3dB)
    # 3. Âm thanh voice giữ nguyên hoặc tăng cường theo voice_volume_db
    # 4. amix trộn 2 luồng âm thanh theo thời lượng video gốc
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
        str(out_file),
    ]

    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Lỗi ffmpeg khi lồng tiếng: {proc.stderr}")

    print(f"[dubber] [V] Đã hoàn thành lồng tiếng video: {out_file}")
    return out_file
