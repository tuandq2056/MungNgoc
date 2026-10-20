import asyncio
from pathlib import Path
import edge_tts
from .voices import VoiceProfile, get_voice_profile


class EdgeTTSGenerator:
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
