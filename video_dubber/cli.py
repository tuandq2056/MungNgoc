import argparse
import sys
from pathlib import Path
from .mixer import dub_video


def main():
    parser = argparse.ArgumentParser(
        prog="video_dubber",
        description="Lồng tiếng file .mp3 vào video gốc và xuất ra thư mục output (âm lượng nền -3dB)."
    )
    parser.add_argument("--video", type=str, required=True, help="Đường dẫn video gốc")
    parser.add_argument("--voice", type=str, required=True, help="Đường dẫn file voice .mp3")
    parser.add_argument("-o", "--output", type=str, default=None, help="Đường dẫn video xuất ra")
    parser.add_argument("--bg-volume", type=str, default="-3dB", help="Mức giảm âm lượng nền (mặc định: -3dB)")
    parser.add_argument("--voice-volume", type=str, default="0dB", help="Mức âm lượng voice (mặc định: 0dB)")

    args = parser.parse_args()

    try:
        out = dub_video(
            video_path=args.video,
            voice_audio_path=args.voice,
            output_path=args.output,
            bg_volume_db=args.bg_volume,
            voice_volume_db=args.voice_volume,
        )
        print(f"\n[Xong] Video hoàn chỉnh: {out}")
    except Exception as e:
        print(f"\nLỗi: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
