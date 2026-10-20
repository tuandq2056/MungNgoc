"""
video_dubber
------------
Module chuyên trách hòa âm và lồng tiếng file audio (.mp3 / .wav) vào video gốc,
tự động điều chỉnh âm lượng nền (mặc định -3dB) bằng FFmpeg stream copy.
"""

from .mixer import dub_video

__all__ = ["dub_video"]
__version__ = "1.0.0"
