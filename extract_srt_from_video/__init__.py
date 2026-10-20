"""
extract_srt_from_video
----------------------
Module bóc tách và tạo file phụ đề (.srt) từ video sử dụng mô hình SenseVoice-Small và Silero-VAD.
Hỗ trợ phụ đề tiếng Trung gốc, dịch tiếng Việt hoặc song ngữ (bilingual).
"""

from .pipeline import process_video, process_folder, extract_srt

__all__ = ["process_video", "process_folder", "extract_srt"]
__version__ = "1.0.0"
