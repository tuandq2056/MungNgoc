"""
Dịch cả tập phụ đề tiếng Trung (.zh.srt) sang tiếng Việt bằng Qwen qua Ollama (vd. chạy trên Google Colab).
Mỗi tập gửi trong MỘT request kèm glossary, nên model thấy toàn bộ ngữ cảnh và giữ tên nhân vật nhất quán.
Module độc lập: không import gì từ extract_srt_from_video.
"""

import json
import os
import re
from pathlib import Path
from typing import Callable, Optional

import requests

DEFAULT_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen2.5:14b-instruct"
NUM_CTX = 8192
ATTEMPTS = 3
CONNECT_TIMEOUT_SEC = 15
READ_TIMEOUT_SEC = 300  # chờ tối đa giữa hai gói dữ liệu stream; GPU yếu sinh chậm nhưng vẫn phải có gói đều đặn
MAX_FAILED_RATIO = 0.2

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_SPEAKABLE_RE = re.compile(r"\w")
_REFUSAL_RE = re.compile(r"bạn chưa cung cấp|vui lòng cung cấp|as an ai|i cannot translate|i'm sorry, but", re.IGNORECASE)
_TIMESTAMP_RE = re.compile(r"^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$")

_SCHEMA = {
    "type": "object",
    "properties": {
        "translations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "integer"}, "vi": {"type": "string"}},
                "required": ["id", "vi"],
            },
        }
    },
    "required": ["translations"],
}


class QwenTranslateError(RuntimeError):
    pass


def load_dotenv(path: Optional[Path] = None) -> None:
    """Nạp KEY=VALUE từ .env ở thư mục gốc project; biến môi trường đã có giá trị thì giữ nguyên."""
    path = path or Path(__file__).resolve().parent.parent / ".env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.removeprefix("export ").partition("=")
        key, value = key.strip(), value.strip()
        if value[:1] in ('"', "'") and value.count(value[0]) >= 2:
            value = value[1:value.index(value[0], 1)]
        else:
            value = re.split(r"\s+#", value, maxsplit=1)[0].strip()
        if key and not os.environ.get(key):
            os.environ[key] = value


def load_glossary(path: Optional[Path] = None) -> str:
    """
    Đọc glossary.txt thành đoạn văn đưa vào prompt; không có file thì trả chuỗi rỗng.
    Dòng `Hán [| biến thể ASR ...] = Việt` -> "- Hán (nhận diện có thể ghi sai: ...) -> Việt"; dòng `@...` giữ nguyên làm quy ước.
    """
    path = path or Path(os.environ.get("GLOSSARY_FILE") or Path(__file__).resolve().parent.parent / "glossary.txt")
    if not path.is_file():
        return ""
    terms, rules = [], []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("@"):
            rules.append(f"- {line[1:].strip()}")
        elif "=" in line:
            src, _, vi = line.partition("=")
            names = [n.strip() for n in src.split("|") if n.strip()]
            if names and vi.strip():
                alt = f" (nhận diện giọng nói có thể ghi sai thành: {', '.join(names[1:])})" if len(names) > 1 else ""
                terms.append(f"- {names[0]}{alt} -> {vi.strip()}")
    parts = []
    if terms:
        parts.append("Bảng thuật ngữ BẮT BUỘC dùng đúng:\n" + "\n".join(terms))
    if rules:
        parts.append("Quy ước:\n" + "\n".join(rules))
    return "\n".join(parts)


def is_speakable(text: str) -> bool:
    return bool(_SPEAKABLE_RE.search(text))


def is_valid_translation(vi: str) -> bool:
    vi = vi.strip()
    return bool(vi) and not _CJK_RE.search(vi) and not _REFUSAL_RE.search(vi)


def source_stem(path: Path) -> str:
    """tap1.srt / tap1.zh.srt -> tap1"""
    name = path.name
    for suffix in (".zh.srt", ".srt"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return path.stem


def parse_srt(path: Path) -> list[tuple[str, str, str]]:
    """Trả về [(số thứ tự, dòng thời gian, nội dung)] theo đúng file."""
    cues = []
    for block in path.read_text(encoding="utf-8-sig").strip().split("\n\n"):
        lines = block.split("\n")
        if len(lines) >= 2 and _TIMESTAMP_RE.match(lines[1].strip()):
            cues.append((lines[0].strip(), lines[1].strip(), "\n".join(lines[2:]).strip()))
    return cues


def check_server(host: str, model: str) -> None:
    """Báo lỗi rõ ràng nếu không nối được Ollama hoặc chưa có model."""
    try:
        resp = requests.get(f"{host}/api/tags", timeout=CONNECT_TIMEOUT_SEC)
        resp.raise_for_status()
    except Exception as e:
        raise QwenTranslateError(f"Không nối được Ollama tại {host}: {e}") from e
    names = [m.get("name", "") for m in resp.json().get("models", [])]
    if not any(n == model or n.split(":")[0] == model for n in names):
        raise QwenTranslateError(f"Ollama tại {host} chưa có model '{model}' (đang có: {', '.join(names) or 'không có'}).")


def _build_messages(items: list[dict], glossary: str, context_hint: str) -> list[dict]:
    system = (
        "Bạn là chuyên gia biên dịch phụ đề phim tiếng Trung sang tiếng Việt.\n"
        f"Bối cảnh: {context_hint}.\n"
        "Bạn nhận một mảng JSON các câu thoại theo đúng thứ tự trong cùng một tập phim "
        "(câu có thể ngắn hoặc lủng củng do nhận diện giọng nói tự động; hãy dùng các câu xung quanh để hiểu ngữ cảnh).\n"
        "Yêu cầu:\n"
        "- Trả về JSON {\"translations\": [{\"id\": ..., \"vi\": ...}]} với MỖI id đầu vào đúng một bản dịch.\n"
        "- Bản dịch tiếng Việt tự nhiên, ngắn gọn, đúng văn phong nhân vật. Không giải thích, không xin lỗi, không giữ chữ Hán.\n"
        "- Giữ tên nhân vật và cách xưng hô nhất quán trong toàn bộ tập."
    )
    if glossary:
        system += "\n\n" + glossary
    user = json.dumps(items, ensure_ascii=False)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _chat_stream(host: str, model: str, messages: list[dict], on_progress: Optional[Callable[[int], None]]) -> str:
    """Gọi /api/chat dạng stream (giữ kết nối sống qua tunnel) và trả về toàn bộ nội dung."""
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "format": _SCHEMA,
        "options": {"temperature": 0.2, "top_p": 0.8, "num_ctx": NUM_CTX},
    }
    acc = ""
    with requests.post(f"{host}/api/chat", json=payload, stream=True, timeout=(CONNECT_TIMEOUT_SEC, READ_TIMEOUT_SEC)) as resp:
        if resp.status_code != 200:
            raise QwenTranslateError(f"Ollama trả lỗi {resp.status_code}: {resp.text[:200]}")
        for raw in resp.iter_lines():
            if not raw:
                continue
            chunk = json.loads(raw)
            if chunk.get("error"):
                raise QwenTranslateError(f"Ollama báo lỗi: {chunk['error']}")
            acc += chunk.get("message", {}).get("content", "")
            if on_progress:
                on_progress(acc.count('"vi"'))
            if chunk.get("done"):
                break
    return acc


def translate_lines(
    lines: list[str],
    host: str,
    model: str,
    glossary: str = "",
    context_hint: str = "phim cổ trang, tiên hiệp, hài hước",
    on_progress: Optional[Callable[[int], None]] = None,
) -> list[str]:
    """
    Dịch danh sách câu thoại trong một request (id giữ đúng thứ tự, nên không bao giờ lệch dòng).
    Câu model bỏ sót hoặc dịch hỏng được gửi lại ở lần sau; câu vẫn hỏng sau cùng trả về chuỗi rỗng.
    """
    results = [""] * len(lines)
    todo = [i for i, t in enumerate(lines) if is_speakable(t)]
    last_error: Optional[Exception] = None

    for attempt in range(1, ATTEMPTS + 1):
        if not todo:
            break
        items = [{"id": i + 1, "zh": lines[i]} for i in todo]
        done_before = len(lines) - len(todo)
        progress = (lambda n, base=done_before: on_progress(base + n)) if on_progress else None
        try:
            raw = _chat_stream(host, model, _build_messages(items, glossary, context_hint), progress)
            returned = {int(t["id"]): str(t["vi"]).strip() for t in json.loads(raw).get("translations", [])}
        except (requests.RequestException, json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            last_error = e
            continue
        for i in todo:
            vi = returned.get(i + 1, "")
            if is_valid_translation(vi):
                results[i] = vi
        todo = [i for i in todo if not results[i]]

    failed = [i for i in todo]
    if failed and len(failed) / max(1, sum(is_speakable(t) for t in lines)) > MAX_FAILED_RATIO:
        raise QwenTranslateError(
            f"{len(failed)} câu không dịch được sau {ATTEMPTS} lần thử" + (f" (lỗi cuối: {last_error})" if last_error else "")
        )
    return results


def translate_srt(
    zh_srt: Path,
    host: str,
    model: str,
    glossary: str = "",
    out_dir: Optional[Path] = None,
    on_progress: Optional[Callable[[int], None]] = None,
) -> tuple[Path, list[str]]:
    """
    Dịch một file phụ đề tiếng Trung (`<tên>.srt`, đầu ra của extractor ở chế độ zh) thành `<tên>.vi.srt` (chỉ tiếng Việt).
    Trả về (vi_srt, danh sách câu gốc không dịch được).
    """
    zh_srt = Path(zh_srt)
    out_dir = Path(out_dir) if out_dir else zh_srt.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    cues = parse_srt(zh_srt)
    vi_texts = translate_lines([c[2] for c in cues], host, model, glossary, on_progress=on_progress)

    vi_path = out_dir / f"{source_stem(zh_srt)}.vi.srt"
    vi_path.write_text("\n\n".join(f"{n}\n{ts}\n{vi}" for (n, ts, _), vi in zip(cues, vi_texts)) + "\n", encoding="utf-8")
    failed = [zh for (_, _, zh), vi in zip(cues, vi_texts) if is_speakable(zh) and not vi]
    return vi_path, failed
