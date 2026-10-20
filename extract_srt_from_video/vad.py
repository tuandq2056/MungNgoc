from pathlib import Path
from dataclasses import dataclass
import numpy as np
import sherpa_onnx
from .config import SAMPLE_RATE


@dataclass
class SpeechSegment:
    start_sec: float
    end_sec: float
    samples: np.ndarray


class VoiceActivitySegmenter:
    """Sử dụng Silero VAD trong sherpa-onnx để phân đoạn các đoạn có tiếng người nói."""

    def __init__(
        self,
        vad_model_path: str | Path,
        sample_rate: int = SAMPLE_RATE,
        threshold: float = 0.5,
        min_silence_duration: float = 0.4,
        min_speech_duration: float = 0.25,
        max_speech_duration: float = 12.0,
    ):
        self.sample_rate = sample_rate
        self.max_speech_duration = max_speech_duration

        config = sherpa_onnx.VadModelConfig()
        config.silero_vad.model = str(vad_model_path)
        config.silero_vad.threshold = threshold
        config.silero_vad.min_silence_duration = min_silence_duration
        config.silero_vad.min_speech_duration = min_speech_duration
        config.silero_vad.max_speech_duration = max_speech_duration
        config.sample_rate = sample_rate

        self.window_size = config.silero_vad.window_size
        self.vad = sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=60)

    def segment(self, samples: np.ndarray) -> list[SpeechSegment]:
        """
        Nhận mảng âm thanh float32 và trả về danh sách các đoạn có giọng nói kèm start/end.
        """
        self.vad.reset()
        window_size = self.window_size
        total_samples = len(samples)

        # Đưa từng frame window_size vào VAD
        for i in range(0, total_samples, window_size):
            chunk = samples[i:i + window_size]
            if len(chunk) < window_size:
                chunk = np.pad(chunk, (0, window_size - len(chunk)))
            self.vad.accept_waveform(chunk)

        self.vad.flush()

        segments: list[SpeechSegment] = []
        while not self.vad.empty():
            seg = self.vad.front
            start_sec = seg.start / self.sample_rate
            duration_sec = len(seg.samples) / self.sample_rate
            end_sec = start_sec + duration_sec
            
            # Chỉ lấy các đoạn có mẫu hợp lệ
            if len(seg.samples) > 0:
                segments.append(
                    SpeechSegment(
                        start_sec=start_sec,
                        end_sec=end_sec,
                        samples=np.array(seg.samples, dtype=np.float32),
                    )
                )
            self.vad.pop()

        return segments
