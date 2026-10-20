import argparse
import sys
from pathlib import Path
from .pipeline import generate_voice_from_srt
from .voices import list_available_voices


def main():
    parser = argparse.ArgumentParser(
        prog="srt_to_voice",
        description="Tạo file âm thanh lồng tiếng tiếng Việt khớp chuẩn mốc thời gian từ file .srt."
    )
    parser.add_argument(
        "input",
        type=str,
        nargs="?",
        help="Đường dẫn file .srt tiếng Việt cần tạo voice."
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Đường dẫn file âm thanh xuất ra (.mp3 hoặc .wav)."
    )
    parser.add_argument(
        "-v", "--voice",
        type=str,
        default="nu_chuan",
        help="Tên preset giọng đọc (nu_chuan, nam_thuyet_minh, nu_tre, nam_co_trang... Mặc định: nu_chuan)."
    )
    parser.add_argument(
        "-s", "--max-speedup",
        type=float,
        default=1.45,
        help="Tỷ lệ tăng tốc tối đa khi câu đọc dài hơn mốc thời gian (mặc định: 1.45x)."
    )
    parser.add_argument(
        "--save-segments",
        action="store_true",
        help="Lưu các file âm thanh đơn lẻ của từng câu thoại."
    )
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="Liệt kê danh sách tất cả các giọng đọc tiếng Việt có sẵn."
    )

    args = parser.parse_args()

    if args.list_voices:
        print("\n=== DANH SÁCH GIỌNG ĐỌC TIẾNG VIỆT CÓ SẴN ===")
        voices = list_available_voices()
        for v in voices:
            print(f" • Mã giọng: {v['key']:<16} | Giới tính: {v['gender']:<6} | {v['description']}")
        print("\nCách dùng: srt-to-voice input.srt -v <mã_giọng>")
        sys.exit(0)

    if not args.input:
        parser.print_help()
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Lỗi: Không tìm thấy file '{input_path}'", file=sys.stderr)
        sys.exit(1)

    try:
        out_file = generate_voice_from_srt(
            srt_path=input_path,
            output_audio=args.output,
            voice=args.voice,
            max_speedup=args.max_speedup,
            save_segments=args.save_segments,
        )
        print(f"\n[Xong] Hoàn tất tạo lồng tiếng: {out_file}")
    except Exception as e:
        print(f"\nLỗi trong quá trình xử lý: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
