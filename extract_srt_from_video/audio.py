import subprocess
import numpy as np
from pathlib import Path
from .config import SAMPLE_RATE


def extract_audio_from_video(video_path: str | Path, target_sample_rate: int = SAMPLE_RATE) -> tuple[np.ndarray, int]:
    """
    Trích xuất âm thanh từ file video sang dạng mảng numpy float32 (16kHz, mono) bằng ffmpeg.
    Không tạo file rác trung gian, đọc trực tiếp qua stdout.
    
    Args:
        video_path: Đường dẫn tới file video.
        target_sample_rate: Tần số lấy mẫu (mặc định 16000 Hz).
        
    Returns:
        (samples, sample_rate): mảng float32 chuẩn hóa trong khoảng [-1.0, 1.0] và sample rate.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file video: {video_path}")

    command = [
        "ffmpeg",
        "-nostdin",
        "-threads", "0",
        "-i", str(video_path),
        "-vn",
        "-f", "s16le",
        "-acodec", "pcm_s16le",
        "-ac", "1",
        "-ar", str(target_sample_rate),
        "-"
    ]

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout_data, stderr_data = process.communicate()

    if process.returncode != 0:
        error_msg = stderr_data.decode("utf-8", errors="replace")
        raise RuntimeError(f"Lỗi khi trích xuất audio bằng ffmpeg từ {video_path}:\n{error_msg}")

    samples = np.frombuffer(stdout_data, dtype=np.int16).astype(np.float32) / 32768.0
    return samples, target_sample_rate
