"""
srt_to_voice
------------
Module chuyển đổi phụ đề (.srt) tiếng Việt thành file âm thanh lồng tiếng khớp mốc thời gian.
Hỗ trợ nhiều giọng đọc tiếng Việt đa dạng (Nam, Nữ, Cổ trang, Thuyết minh, v.v.).
"""

from .pipeline import generate_voice_from_srt
from .voices import list_available_voices, get_voice_profile

__all__ = ["generate_voice_from_srt", "list_available_voices", "get_voice_profile"]
__version__ = "1.0.0"
