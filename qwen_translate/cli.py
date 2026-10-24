#!/usr/bin/env python3
"""
CLI độc lập: dịch phụ đề tiếng Trung (.srt) sang tiếng Việt (.vi.srt) bằng Qwen (Ollama / Colab), mỗi tập một request kèm glossary.
    python3 -m extract_srt_from_video ./sample -m zh -o ./work/zh     # bước 1: chỉ bóc tách tiếng Trung
    python3 -m qwen_translate ./work/zh                               # bước 2: dịch cả thư mục
    python3 -m qwen_translate ./work/zh/tap1.srt --force              # dịch lại một tập
"""

import argparse
import os
import sys
from pathlib import Path

from .translate import (
    DEFAULT_HOST, DEFAULT_MODEL, QwenTranslateError,
    check_server, load_dotenv, load_glossary, source_stem, translate_srt,
)

try:
    from tqdm import tqdm
except ImportError:  # chưa cài tqdm thì vẫn chạy, chỉ không có thanh tiến độ
    tqdm = None


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="qwen_translate", description="Dịch .srt tiếng Trung -> .vi.srt bằng Qwen qua Ollama (cả tập một lần).")
    parser.add_argument("input", help="File .srt tiếng Trung hoặc thư mục chứa các file đó")
    parser.add_argument("--host", default=os.environ.get("OLLAMA_HOST", DEFAULT_HOST), help="Địa chỉ Ollama (mặc định: $OLLAMA_HOST hoặc localhost)")
    parser.add_argument("--model", default=os.environ.get("QWEN_MODEL", DEFAULT_MODEL), help=f"Tên model (mặc định: {DEFAULT_MODEL})")
    parser.add_argument("--glossary", default=None, help="File glossary (mặc định: glossary.txt ở thư mục gốc)")
    parser.add_argument("-o", "--output-dir", default=None, help="Thư mục xuất (mặc định: cạnh file nguồn)")
    parser.add_argument("--force", action="store_true", help="Dịch lại cả những tập đã có .vi.srt (mặc định bỏ qua để không ghi đè)")
    args = parser.parse_args()

    host = args.host.rstrip("/")
    target = Path(args.input)
    if target.is_dir():
        # Lấy mọi .srt tiếng Trung; bỏ các bản dịch .vi.srt đã có trong cùng thư mục
        files = sorted((p for p in target.glob("*.srt") if not p.name.endswith(".vi.srt")), key=lambda p: (len(p.name), p.name))
    else:
        files = [target]
    if not files or not all(f.is_file() for f in files):
        print(f"Không tìm thấy file phụ đề tiếng Trung (.srt) nào ở: {target}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.output_dir) if args.output_dir else None
    glossary = load_glossary(Path(args.glossary) if args.glossary else None)
    print(f"[qwen_translate] {host} | model {args.model} | glossary: {'có' if glossary else 'KHÔNG CÓ'}", file=sys.stderr)

    try:
        check_server(host, args.model)
    except QwenTranslateError as e:
        print(f"Lỗi: {e}", file=sys.stderr)
        sys.exit(1)

    failures: list[tuple[str, str]] = []
    done = 0
    outer = tqdm(files, unit="tập", file=sys.stderr) if tqdm else files
    for zh in outer:
        stem = source_stem(zh)
        vi_path = (out_dir or zh.parent) / f"{stem}.vi.srt"
        if vi_path.exists() and not args.force:
            if tqdm:
                tqdm.write(f"  - {stem}: bỏ qua (đã có {vi_path.name}, dùng --force để dịch lại)", file=sys.stderr)
            continue
        if tqdm:
            outer.set_description(stem)
        total = sum(1 for _ in zh.read_text(encoding="utf-8-sig").split("\n\n"))
        inner = tqdm(total=total, desc="  câu", unit="câu", leave=False, file=sys.stderr) if tqdm else None
        last = [0]

        def on_progress(n: int) -> None:
            if inner and n > last[0]:
                inner.update(min(n, total) - last[0])
                last[0] = min(n, total)

        try:
            _, failed = translate_srt(zh, args.host.rstrip("/"), args.model, glossary, out_dir, on_progress)
            done += 1
            msg = f"  ✔ {stem}" + (f" ({len(failed)} câu không dịch được)" if failed else "")
            print(msg, file=sys.stderr) if not tqdm else tqdm.write(msg, file=sys.stderr)
        except Exception as e:
            failures.append((stem, str(e)))
            msg = f"  ✘ {stem}: {e}"
            print(msg, file=sys.stderr) if not tqdm else tqdm.write(msg, file=sys.stderr)
        finally:
            if inner:
                inner.close()

    print(f"\n[qwen_translate] Xong {done}/{len(files)} tập.", file=sys.stderr)
    if failures:
        for stem, err in failures:
            print(f"  ✘ {stem}: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
