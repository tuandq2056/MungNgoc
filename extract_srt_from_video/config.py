import os
from pathlib import Path

# Thư mục gốc chứa model cache
DEFAULT_CACHE_DIR = Path(os.environ.get("EXTRACT_SRT_CACHE_DIR", Path.home() / ".cache" / "extract_srt_from_video"))
MODEL_DIR = DEFAULT_CACHE_DIR / "models"

# Đường dẫn model SenseVoice-Small ONNX
SENSEVOICE_MODEL_DIR = MODEL_DIR / "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17"
SENSEVOICE_MODEL_FILE = SENSEVOICE_MODEL_DIR / "model.int8.onnx"
SENSEVOICE_TOKENS_FILE = SENSEVOICE_MODEL_DIR / "tokens.txt"

# Đường dẫn model Silero VAD
SILERO_VAD_FILE = MODEL_DIR / "silero_vad.onnx"

# URL tải model từ release chính thức của sherpa-onnx
SENSEVOICE_ARCHIVE_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
    "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17.tar.bz2"
)
SILERO_VAD_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx"
)

# Cấu hình âm thanh
SAMPLE_RATE = 16000

# Các định dạng video được hỗ trợ
SUPPORTED_VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".flv", ".webm", ".ts", ".m4v", ".wmv"
}
