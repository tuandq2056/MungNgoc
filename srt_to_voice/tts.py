import asyncio
import os
import time
from pathlib import Path
from xml.sax.saxutils import escape

import edge_tts
import requests

from .aligner import get_audio_duration
from .voices import VoiceProfile

MAX_ATTEMPTS = 6
BACKOFF_SEC = (1, 2, 4, 8, 15)


class TTSError(RuntimeError):
    """TTS không sinh được âm thanh hợp lệ sau mọi lần thử."""


class NonRetryableTTSError(TTSError):
    """Lỗi cố định (key sai, voice sai...): thử lại vô ích nên dừng ngay."""


class RetryingTTS:
    """Lớp cơ sở: engine TTS chỉ cần cài `generate_speech`; phần thử lại và kiểm tra file dùng chung."""

    def generate_speech(self, text: str, output_path: str | Path) -> Path:
        raise NotImplementedError

    def generate_speech_with_retry(self, text: str, output_path: str | Path) -> Path:
        """
        Sinh giọng đọc, thử lại khi engine lỗi tạm thời (rớt kết nối, bị giới hạn request, "No audio was received"...).
        Chỉ trả về khi file mp3 giải mã được và có thời lượng > 0; ngược lại ném TTSError.
        """
        output_path = Path(output_path)
        last_err: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                self.generate_speech(text, output_path)
                if output_path.exists() and get_audio_duration(output_path) > 0:
                    return output_path
                last_err = RuntimeError("file âm thanh rỗng hoặc không giải mã được")
            except NonRetryableTTSError:
                output_path.unlink(missing_ok=True)
                raise
            except Exception as e:  # edge_tts.exceptions.*, lỗi mạng, timeout...
                last_err = e
            output_path.unlink(missing_ok=True)
            if attempt < MAX_ATTEMPTS:
                wait = BACKOFF_SEC[attempt - 1]
                print(f"    [!] Lần {attempt}/{MAX_ATTEMPTS} lỗi ({last_err}); thử lại sau {wait}s...")
                time.sleep(wait)
        raise TTSError(f"Không sinh được giọng cho câu: {text!r} ({last_err})")


class EdgeTTSGenerator(RetryingTTS):
    """Bộ tạo giọng đọc tiếng Việt sử dụng Edge-TTS."""

    def __init__(self, profile: VoiceProfile):
        self.profile = profile

    async def generate_speech_async(self, text: str, output_path: str | Path) -> Path:
        """Sinh giọng đọc từ văn bản và lưu ra file mp3."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        communicate = edge_tts.Communicate(
            text=text,
            voice=self.profile.edge_voice,
            pitch=self.profile.pitch,
            rate=self.profile.rate,
            volume=self.profile.volume,
        )
        await communicate.save(str(output_path))
        return output_path

    def generate_speech(self, text: str, output_path: str | Path) -> Path:
        """Wrapper đồng bộ cho generate_speech_async."""
        return asyncio.run(self.generate_speech_async(text, output_path))


class AzureTTSGenerator(RetryingTTS):
    """
    Bộ tạo giọng đọc dùng Azure AI Speech (REST API chính thức). Dùng chung tên giọng với Edge-TTS
    (vd vi-VN-HoaiMyNeural) nên giọng giữ nguyên, nhưng ổn định hơn.
    Cần biến môi trường AZURE_SPEECH_KEY và AZURE_SPEECH_REGION (vd southeastasia).
    """

    OUTPUT_FORMAT = "audio-24khz-48kbitrate-mono-mp3"

    def __init__(self, profile: VoiceProfile, key: str, region: str):
        self.profile = profile
        self.key = key
        self.url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"

    def _build_ssml(self, text: str) -> str:
        p = self.profile
        attrs = "".join(
            f' {name}="{value}"'
            for name, value, default in (("pitch", p.pitch, "+0Hz"), ("rate", p.rate, "+0%"), ("volume", p.volume, "+0%"))
            if value != default
        )
        body = escape(text)
        if attrs:
            body = f"<prosody{attrs}>{body}</prosody>"
        return (
            "<speak version='1.0' xml:lang='vi-VN'>"
            f"<voice xml:lang='vi-VN' name='{p.edge_voice}'>{body}</voice>"
            "</speak>"
        )

    def generate_speech(self, text: str, output_path: str | Path) -> Path:
        """Gửi SSML tới Azure và lưu mp3. 400/401/403 là lỗi cố định (key/voice/region sai) nên không thử lại."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        resp = requests.post(
            self.url,
            headers={
                "Ocp-Apim-Subscription-Key": self.key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": self.OUTPUT_FORMAT,
                "User-Agent": "mungngoc-dubber",
            },
            data=self._build_ssml(text).encode("utf-8"),
            timeout=60,
        )
        if resp.status_code in (400, 401, 403):
            raise NonRetryableTTSError(f"Azure Speech từ chối ({resp.status_code}): {resp.text[:200]}")
        if resp.status_code != 200:
            raise RuntimeError(f"Azure Speech lỗi {resp.status_code}: {resp.text[:200]}")
        output_path.write_bytes(resp.content)
        return output_path


def make_tts(profile: VoiceProfile) -> RetryingTTS:
    """Chọn engine: có AZURE_SPEECH_KEY và AZURE_SPEECH_REGION thì dùng Azure, không thì dùng Edge-TTS."""
    try:
        from extract_srt_from_video.translator import load_dotenv
        load_dotenv()
    except ImportError:  # srt_to_voice dùng độc lập, không có module bên cạnh
        pass

    key = os.environ.get("AZURE_SPEECH_KEY", "").strip()
    region = os.environ.get("AZURE_SPEECH_REGION", "").strip()
    if key and region and key != "your-key-here":
        print(f"[srt_to_voice] Engine: Azure Speech ({region}), giọng {profile.edge_voice}")
        return AzureTTSGenerator(profile, key, region)

    print("[srt_to_voice] Engine: Edge-TTS (chưa đặt AZURE_SPEECH_KEY / AZURE_SPEECH_REGION; Edge-TTS hay bị từ chối ngẫu nhiên một số câu)")
    return EdgeTTSGenerator(profile)
