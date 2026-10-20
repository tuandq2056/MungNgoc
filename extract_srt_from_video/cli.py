import argparse
import sys
from pathlib import Path
from .pipeline import extract_srt


def main():
    parser = argparse.ArgumentParser(
        prog="extract_srt_from_video",
        description="Bóc tách phụ đề tiếng Trung từ video sang file .srt sử dụng SenseVoice-Small và Silero-VAD."
    )
    parser.add_argument(
        "input",
        type=str,
        help="Đường dẫn file video hoặc thư mục chứa các video cần xử lý."
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=str,
        default=None,
        help="Thư mục lưu file .srt (mặc định lưu vào thư mục 'srt' bên trong thư mục chứa video)."
    )
    parser.add_argument(
        "-m", "--mode",
        type=str,
        choices=["bilingual", "zh", "vi", "all"],
        default="all",
        help="Chế độ phụ đề: 'all' (xuất cả 3 file: song ngữ, tiếng Trung, tiếng Việt - mặc định), 'bilingual' (song ngữ), 'zh' (tiếng Trung), 'vi' (tiếng Việt)."
    )
    parser.add_argument(
        "-t", "--threads",
        type=int,
        default=4,
        help="Số luồng CPU cho việc giải mã SenseVoice (mặc định 4)."
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Lỗi: Đường dẫn '{input_path}' không tồn tại.", file=sys.stderr)
        sys.exit(1)

    try:
        results = extract_srt(
            target=input_path,
            output_dir=args.output_dir,
            mode=args.mode,
            num_threads=args.threads,
        )
        print(f"\n[Xong] Đã hoàn thành xử lý {len(results)} file video.")
    except Exception as e:
        print(f"\nLỗi trong quá trình xử lý: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
