import subprocess
from pathlib import Path


def get_audio_duration(audio_path: str | Path) -> float:
    """Lấy thời lượng âm thanh (tính bằng giây) bằng ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode == 0:
        try:
            return float(result.stdout.strip())
        except ValueError:
            pass
    return 0.0


def build_atempo_filter(speed_factor: float) -> str:
    """
    Xây dựng chuỗi filter atempo cho FFmpeg.
    Lưu ý: Bộ lọc atempo của FFmpeg chỉ nhận giá trị trong khoảng [0.5, 2.0].
    Nếu tốc độ > 2.0 hoặc < 0.5, ta ghép nhiều bộ lọc atempo liên tiếp.
    """
    factors = []
    current = speed_factor

    while current > 2.0:
        factors.append("atempo=2.0")
        current /= 2.0

    while current < 0.5:
        factors.append("atempo=0.5")
        current /= 0.5

    factors.append(f"atempo={current:.3f}")
    return ",".join(factors)


def adjust_audio_speed(
    input_path: str | Path,
    output_path: str | Path,
    target_duration: float,
    max_speedup: float = 1.45,
) -> tuple[Path, float]:
    """
    Điều chỉnh tốc độ âm thanh để vừa vặn với target_duration nếu bị dài hơn.
    
    Args:
        input_path: File âm thanh gốc vừa sinh ra.
        output_path: File âm thanh sau khi chỉnh tốc độ.
        target_duration: Thời lượng mong muốn tối đa.
        max_speedup: Giới hạn tăng tốc tối đa (mặc định 1.45x để giọng đọc không bị quá nhanh/ngọng).
        
    Returns:
        (output_path, new_duration)
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    original_duration = get_audio_duration(input_path)
    if original_duration <= 0 or target_duration <= 0:
        return input_path, original_duration

    # Nếu thời lượng đã vừa vặn hoặc chỉ lệch nhẹ (< 0.15s), giữ nguyên
    if original_duration <= target_duration + 0.15:
        return input_path, original_duration

    # Tính toán hệ số tăng tốc
    speed_factor = original_duration / target_duration
    # Giới hạn tốc độ đọc tối đa để đảm bảo người nghe nghe rõ
    speed_factor = min(speed_factor, max_speedup)

    filter_str = build_atempo_filter(speed_factor)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-nostdin",
        "-i", str(input_path),
        "-filter:a", filter_str,
        str(output_path),
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode == 0:
        new_duration = get_audio_duration(output_path)
        return output_path, new_duration

    # Nếu lỗi, fallback về file gốc
    return input_path, original_duration
