import os
import tarfile
import urllib.request
from pathlib import Path
from .config import (
    MODEL_DIR,
    SENSEVOICE_MODEL_DIR,
    SENSEVOICE_MODEL_FILE,
    SENSEVOICE_TOKENS_FILE,
    SILERO_VAD_FILE,
    SENSEVOICE_ARCHIVE_URL,
    SILERO_VAD_URL,
)


def _download_file(url: str, dest_path: Path):
    """Tải file từ URL về dest_path kèm thanh tiến trình đơn giản."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_suffix(".tmp")
    print(f"[download] Bắt đầu tải: {url} -> {dest_path.name}")

    def reporthook(count, block_size, total_size):
        if total_size > 0:
            percent = int(count * block_size * 100 / total_size)
            downloaded_mb = (count * block_size) / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            print(f"\r[download] {percent}% ({downloaded_mb:.1f}MB/{total_mb:.1f}MB)", end="", flush=True)

    urllib.request.urlretrieve(url, str(temp_path), reporthook=reporthook)
    print("\n[download] Hoàn tất.")
    temp_path.rename(dest_path)


def ensure_models() -> tuple[Path, Path, Path]:
    """
    Kiểm tra và đảm bảo các model SenseVoice và Silero VAD đã sẵn sàng.
    Trả về (model_onnx_path, tokens_path, vad_onnx_path).
    """
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Kiểm tra Silero VAD
    if not SILERO_VAD_FILE.exists():
        print(f"[models] Không tìm thấy Silero VAD tại {SILERO_VAD_FILE}. Đang tải...")
        _download_file(SILERO_VAD_URL, SILERO_VAD_FILE)

    # 2. Kiểm tra SenseVoice
    if not (SENSEVOICE_MODEL_FILE.exists() and SENSEVOICE_TOKENS_FILE.exists()):
        print(f"[models] Không tìm thấy SenseVoice-Small tại {SENSEVOICE_MODEL_DIR}. Đang tải...")
        archive_path = MODEL_DIR / "sense_voice.tar.bz2"
        _download_file(SENSEVOICE_ARCHIVE_URL, archive_path)
        print("[models] Đang giải nén bộ trọng số SenseVoice-Small...")
        with tarfile.open(archive_path, "r:bz2") as tar:
            tar.extractall(path=MODEL_DIR)
        if archive_path.exists():
            archive_path.unlink()
        print("[models] Giải nén thành công.")

    return SENSEVOICE_MODEL_FILE, SENSEVOICE_TOKENS_FILE, SILERO_VAD_FILE
