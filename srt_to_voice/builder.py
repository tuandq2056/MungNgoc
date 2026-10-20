import subprocess
from pathlib import Path
import numpy as np


SAMPLE_RATE = 24000  # Tần số mẫu chuẩn của Edge-TTS


def decode_audio_to_pcm(audio_path: str | Path, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Giải mã file audio bất kỳ sang mảng PCM int16 bằng ffmpeg."""
    cmd = [
        "ffmpeg",
        "-nostdin",
        "-threads", "0",
        "-i", str(audio_path),
        "-vn",
        "-f", "s16le",
        "-acodec", "pcm_s16le",
        "-ac", "1",
        "-ar", str(sample_rate),
        "-",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        return np.array([], dtype=np.int16)
    return np.frombuffer(stdout, dtype=np.int16)


def build_timeline_audio(
    clips: list[tuple[float, Path]],
    total_duration_sec: float,
    output_file: str | Path,
    sample_rate: int = SAMPLE_RATE,
) -> Path:
    """
    Ghép các đoạn thoại vào đúng mốc thời gian (start_sec) trên toàn bộ trục thời gian.
    Các khoảng giữa các câu thoại tự động là khoảng lặng (silence).
    
    Args:
        clips: Danh sách tuple (start_sec, audio_file_path).
        total_duration_sec: Tổng thời lượng của video/timeline.
        output_file: Đường dẫn file kết quả (.mp3 hoặc .wav).
        sample_rate: Tần số mẫu (24000Hz).
    """
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Đảm bảo tổng độ dài tối thiểu đủ chứa clip cuối cùng
    max_end_sec = total_duration_sec
    for start_sec, clip_path in clips:
        # Nếu chưa biết thời lượng, ước lượng
        max_end_sec = max(max_end_sec, start_sec + 5.0)

    total_samples = int(np.ceil(max_end_sec * sample_rate))
    timeline = np.zeros(total_samples, dtype=np.int32)

    for start_sec, clip_path in clips:
        clip_pcm = decode_audio_to_pcm(clip_path, sample_rate)
        if len(clip_pcm) == 0:
            continue

        start_idx = int(round(start_sec * sample_rate))
        end_idx = start_idx + len(clip_pcm)

        # Mở rộng buffer nếu cần
        if end_idx > len(timeline):
            padding = np.zeros(end_idx - len(timeline), dtype=np.int32)
            timeline = np.concatenate([timeline, padding])

        timeline[start_idx:end_idx] += clip_pcm.astype(np.int32)

    # Clipping chống vỡ âm thanh
    timeline = np.clip(timeline, -32768, 32767).astype(np.int16)

    # Xuất ra file âm thanh qua ffmpeg
    is_mp3 = output_file.suffix.lower() == ".mp3"
    codec = ["-c:a", "libmp3lame", "-b:a", "192k"] if is_mp3 else ["-c:a", "pcm_s16le"]

    encode_cmd = [
        "ffmpeg",
        "-y",
        "-nostdin",
        "-f", "s16le",
        "-ac", "1",
        "-ar", str(sample_rate),
        "-i", "-",
        *codec,
        str(output_file),
    ]

    proc = subprocess.Popen(encode_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate(input=timeline.tobytes())

    return output_file
