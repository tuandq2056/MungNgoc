"""
qwen_translate
--------------
Module dịch phụ đề .zh.srt sang tiếng Việt bằng Qwen qua Ollama (chạy local hoặc trên Google Colab).
Mỗi tập gửi một request kèm glossary để giữ tên nhân vật nhất quán. Độc lập với các module còn lại.
"""

from .translate import translate_lines, translate_srt, load_glossary

__all__ = ["translate_lines", "translate_srt", "load_glossary"]
