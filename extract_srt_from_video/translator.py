import os
import re
import json
import time
import requests
from pathlib import Path
from typing import Optional

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_BATCH_SIZE = 40
GEMINI_ATTEMPTS = 3
GEMINI_RATE_LIMIT_WAIT_SEC = (10, 30)  # chờ giữa các lần thử khi bị 429
GEMINI_NO_RETRY_STATUS = (400, 401, 403, 404)  # key/model sai hoặc không có quyền: thử lại vô ích
GEMINI_BLOCK_FINISH_REASONS = ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "RECITATION")
PLACEHOLDER_KEYS = ("your-key-here",)

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_SPEAKABLE_RE = re.compile(r"\w")  # có chữ/số (kể cả chữ Hán); chỉ dấu câu thì không có gì để dịch
# Model nhỏ đôi khi "chat lại" thay vì dịch (vd: "Xin lỗi, bạn chưa cung cấp câu tiếng Trung...").
# Chỉ bắt các cụm đặc trưng của câu từ chối, tránh nhầm với lời thoại thật như "Tôi không thể giúp anh".
_REFUSAL_RE = re.compile(
    r"bạn chưa cung cấp|vui lòng cung cấp|cung cấp câu|as an ai|i cannot translate|i'm sorry, but",
    re.IGNORECASE,
)
# Bản dịch dài bất thường so với câu gốc gần như chắc chắn là model nói chuyện thay vì dịch
_MAX_LEN_RATIO = 10
_MAX_LEN_SLACK = 20


class TranslationError(RuntimeError):
    """Quá nhiều câu thoại không dịch được, tiếp tục sẽ ra video thiếu tiếng."""


def load_dotenv(path: Optional[Path] = None) -> None:
    """
    Nạp các dòng KEY=VALUE từ file .env ở thư mục gốc project (hỗ trợ `export`, dấu nháy, chú thích cuối dòng, BOM).
    Biến môi trường đã có giá trị thì được ưu tiên; biến đặt rỗng thì lấy giá trị từ .env.
    """
    path = path or Path(__file__).resolve().parent.parent / ".env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if value[:1] in ('"', "'") and value.count(value[0]) >= 2:
            value = value[1:value.index(value[0], 1)]
        else:
            value = re.split(r"\s+#", value, maxsplit=1)[0].strip()
        if key and not os.environ.get(key):
            os.environ[key] = value


def is_speakable(text: str) -> bool:
    """Câu có chữ hoặc số để dịch/đọc (không phải chỉ toàn dấu câu như "。" hay "...")."""
    return bool(_SPEAKABLE_RE.search(text))


def is_valid_translation(vi_text: str, source: Optional[str] = None) -> bool:
    """
    Bản dịch hợp lệ: không rỗng, không còn chữ Hán, không phải câu từ chối/giải thích của model
    và (nếu biết câu gốc) không dài bất thường so với câu gốc.
    """
    vi_text = vi_text.strip()
    if not vi_text or _CJK_RE.search(vi_text) or _REFUSAL_RE.search(vi_text):
        return False
    if source is not None and len(vi_text) > _MAX_LEN_RATIO * len(source.strip()) + _MAX_LEN_SLACK:
        return False
    return True


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
        load_dotenv()
        self.ollama_url = os.environ.get("OLLAMA_HOST", ollama_url).rstrip("/")
        self.model_name = os.environ.get("QWEN_MODEL", model_name)
        self.context_hint = context_hint
        self.gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if self.gemini_key in PLACEHOLDER_KEYS:
            self.gemini_key = ""
        self.gemini_model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
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
        if not text or not is_speakable(text):
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

        if not is_valid_translation(translated, text):
            return ""

        self._cache[text] = translated
        return translated

    def translate_many(self, texts: list[str]) -> list[str]:
        """
        Dịch cả danh sách câu thoại. Ưu tiên Gemini (gửi theo lô để model thấy ngữ cảnh và ít request),
        câu nào Gemini không dịch được hợp lệ thì rơi về chuỗi Qwen -> MyMemory -> Google.
        Câu không dịch được trả về chuỗi rỗng (không bao giờ trả lại tiếng Trung gốc).
        """
        results = [""] * len(texts)
        pending = [i for i, t in enumerate(texts) if is_speakable(t)]
        for i in list(pending):
            if texts[i].strip() in self._cache:
                results[i] = self._cache[texts[i].strip()]
                pending.remove(i)

        if self.gemini_key:
            for start in range(0, len(pending), GEMINI_BATCH_SIZE):
                idxs = pending[start:start + GEMINI_BATCH_SIZE]
                translated = self._translate_batch_with_gemini([texts[i] for i in idxs])
                for i, vi in zip(idxs, translated):
                    if is_valid_translation(vi, texts[i]):
                        results[i] = vi.strip()
                        self._cache[texts[i].strip()] = results[i]
        else:
            print("[translator] Chưa đặt GEMINI_API_KEY, dùng Qwen/MyMemory/Google để dịch.")

        for i in pending:
            if not results[i]:
                results[i] = self.translate(texts[i])
        return results

    def _translate_batch_with_gemini(self, lines: list[str]) -> list[str]:
        """Dịch một lô câu qua Gemini API; trả về danh sách rỗng nếu lỗi (để rơi về dự phòng)."""
        prompt = (
            "Bạn là chuyên gia biên dịch phụ đề phim tiếng Trung sang tiếng Việt.\n"
            f"Bối cảnh: {self.context_hint}.\n"
            "Dưới đây là mảng JSON các câu thoại tiếng Trung theo đúng thứ tự trong phim "
            "(câu có thể rất ngắn hoặc lủng củng do nhận diện giọng nói tự động; hãy dùng các câu xung quanh để hiểu ngữ cảnh).\n"
            "Yêu cầu:\n"
            "- Trả về mảng JSON các chuỗi tiếng Việt, ĐÚNG số phần tử và ĐÚNG thứ tự như đầu vào.\n"
            "- Mỗi phần tử là bản dịch tự nhiên, ngắn gọn của câu tương ứng. Tuyệt đối không giải thích, không xin lỗi, "
            "không giữ lại chữ Hán; nếu câu chỉ là âm thanh hay quá ngắn thì dịch sát nghĩa nhất có thể.\n\n"
            f"{json.dumps(lines, ensure_ascii=False)}"
        )
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
                "responseSchema": {"type": "ARRAY", "items": {"type": "STRING"}},
            },
        }
        url = GEMINI_URL.format(model=self.gemini_model)
        headers = {"x-goog-api-key": self.gemini_key, "Content-Type": "application/json"}

        for attempt in range(1, GEMINI_ATTEMPTS + 1):
            wait = 2 ** attempt
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=60)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates")
                    if not candidates:
                        # Không có kết quả (thường do bộ lọc an toàn chặn cả lô): thử lại vô ích, để dự phòng xử lý từng câu
                        print(f"[translator] Gemini không trả kết quả ({data.get('promptFeedback')}), chuyển sang dự phòng.")
                        return []
                    if candidates[0].get("finishReason") in GEMINI_BLOCK_FINISH_REASONS:
                        print(f"[translator] Gemini dừng do {candidates[0]['finishReason']}, chuyển sang dự phòng.")
                        return []
                    parts = candidates[0].get("content", {}).get("parts", [])
                    out = json.loads("".join(p.get("text", "") for p in parts))
                    if isinstance(out, list) and len(out) == len(lines):
                        return [str(x) for x in out]
                    got = len(out) if isinstance(out, list) else "không phải mảng"
                    print(f"[translator] Gemini trả sai số câu ({got}/{len(lines)}), thử lại...")
                elif resp.status_code in GEMINI_NO_RETRY_STATUS:
                    print(f"[translator] Gemini từ chối ({resp.status_code}): {resp.text[:200]}")
                    return []
                else:
                    if resp.status_code == 429:
                        wait = GEMINI_RATE_LIMIT_WAIT_SEC[min(attempt - 1, len(GEMINI_RATE_LIMIT_WAIT_SEC) - 1)]
                    print(f"[translator] Gemini lỗi {resp.status_code}, thử lại sau {wait}s...")
            except Exception as e:
                print(f"[translator] Gemini lỗi ({e}), thử lại...")
            if attempt < GEMINI_ATTEMPTS:
                time.sleep(wait)
        return []

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
                if is_valid_translation(result, text):
                    return result
        except Exception:
            pass

        return ""

    def _translate_with_fallback(self, text: str) -> str:
        """Fallback dịch máy khi không có Qwen."""
        try:
            from deep_translator import MyMemoryTranslator
            res = MyMemoryTranslator(source="zh-CN", target="vi-VN").translate(text)
            if res and not res.startswith("MYMEMORY WARNING") and is_valid_translation(res, text):
                return res.strip()
        except Exception:
            pass

        try:
            from deep_translator import GoogleTranslator
            res = GoogleTranslator(source="zh-CN", target="vi").translate(text)
            if res and is_valid_translation(res, text):
                return res.strip()
        except Exception:
            pass

        return ""
