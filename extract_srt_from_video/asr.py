import re
from pathlib import Path
import numpy as np
import sherpa_onnx
from .config import SAMPLE_RATE


def clean_sensevoice_text(text: str) -> str:
    """Loại bỏ các tag điều khiển / cảm xúc như <|zh|>, <|NEUTRAL|>, v.v."""
    text = re.sub(r"<\|[^>]+\|>", "", text)
    # Loại bỏ khoảng trắng thừa giữa các ký tự chữ Hán
    text = re.sub(r"\s+", " ", text).strip()
    return text


class SenseVoiceASR:
    """Wrapper cho mô hình SenseVoice-Small ONNX offline recognizer."""

    def __init__(
        self,
        model_path: str | Path,
        tokens_path: str | Path,
        num_threads: int = 4,
        provider: str = "cpu",
        language: str = "zh",
        use_itn: bool = True,
    ):
        self.sample_rate = SAMPLE_RATE
        self.language = language

        self.recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=str(model_path),
            tokens=str(tokens_path),
            num_threads=num_threads,
            provider=provider,
            language=language,
            use_itn=use_itn,
        )

    def transcribe_segment(self, samples: np.ndarray) -> str:
        """Nhận diện lời thoại từ một đoạn âm thanh mẫu (16kHz float32)."""
        if len(samples) == 0:
            return ""

        stream = self.recognizer.create_stream()
        stream.accept_waveform(self.sample_rate, samples)
        self.recognizer.decode_stream(stream)
        raw_text = stream.result.text
        return clean_sensevoice_text(raw_text)
