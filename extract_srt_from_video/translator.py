import os
import re
import json
import requests
from typing import Optional


class SubtitleTranslator:
    """
    Bộ dịch phụ đề phim chuyên dụng tích hợp mô hình ngôn ngữ lớn Qwen (qua Ollama),
    kèm cơ chế fallback thông minh (Google/MyMemory) và bộ nhớ cache.
    """

    def __init__(
        self,
        ollama_url: str = "http://127.0.0.1:11434",
        model_name: str = "qwen2.5:3b-instruct",
        context_hint: str = "phim cổ trang, kiếm hiệp, hành động",
    ):
        self.ollama_url = os.environ.get("OLLAMA_HOST", ollama_url).rstrip("/")
        self.model_name = os.environ.get("QWEN_MODEL", model_name)
        self.context_hint = context_hint
        self._cache: dict[str, str] = {}
        self._is_ollama_available: Optional[bool] = None

    def check_ollama(self) -> bool:
        """Kiểm tra xem Ollama có đang hoạt động và có model Qwen không."""
        if self._is_ollama_available is not None:
            return self._is_ollama_available

        try:
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                # Kiểm tra nếu model có sẵn hoặc ít nhất có 1 model qwen
                has_model = any(self.model_name in m or "qwen" in m.lower() for m in models)
                if has_model:
                    self._is_ollama_available = True
                    return True
        except Exception:
            pass

        self._is_ollama_available = False
        return False

    def translate(self, text: str) -> str:
        """Dịch một câu từ tiếng Trung sang tiếng Việt bằng Qwen, fallback nếu cần."""
        text = text.strip()
        if not text:
            return ""

        if text in self._cache:
            return self._cache[text]

        translated = ""

        # 1. Thử dịch bằng Qwen qua Ollama nếu sẵn sàng
        if self.check_ollama():
            translated = self._translate_with_qwen(text)

        # 2. Nếu Qwen không khả dụng hoặc lỗi, fallback sang MyMemory / Google
        if not translated:
            translated = self._translate_with_fallback(text)

        self._cache[text] = translated
        return translated

    def _translate_with_qwen(self, text: str) -> str:
        """Dịch bằng mô hình Qwen với prompt chuyên sâu cho phụ đề phim."""
        prompt = (
            f"Bạn là chuyên gia biên dịch phụ đề phim tiếng Trung sang tiếng Việt.\n"
            f"Bối cảnh: {self.context_hint}.\n"
            f"Yêu cầu:\n"
            f"- Dịch câu thoại tiếng Trung sau sang tiếng Việt chuẩn ngữ nghĩa, tự nhiên, đúng ngữ cảnh nhân vật.\n"
            f"- Câu dịch ngắn gọn, súc tích để người xem dễ đọc trên màn hình.\n"
            f"- TUYỆT ĐỐI CHỈ XUẤT DUY NHẤT CÂU DỊCH TIẾNG VIỆT, KHÔNG kèm ngoặc kép, giải thích hay phiên âm.\n\n"
            f"Câu tiếng Trung: {text}"
        )

        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "top_p": 0.8,
                },
            }
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=15,
            )
            if resp.status_code == 200:
                result = resp.json().get("response", "").strip()
                # Loại bỏ dấu ngoặc kép thừa hoặc tag nếu có
                result = re.sub(r'^["“](.*)["”]$', r"\1", result).strip()
                if result:
                    return result
        except Exception:
            pass

        return ""

    def _translate_with_fallback(self, text: str) -> str:
        """Fallback dịch máy khi không có Qwen."""
        try:
            from deep_translator import MyMemoryTranslator
            res = MyMemoryTranslator(source="zh-CN", target="vi-VN").translate(text)
            if res and not res.startswith("MYMEMORY WARNING"):
                return res.strip()
        except Exception:
            pass

        try:
            from deep_translator import GoogleTranslator
            res = GoogleTranslator(source="zh-CN", target="vi").translate(text)
            if res:
                return res.strip()
        except Exception:
            pass

        return text
