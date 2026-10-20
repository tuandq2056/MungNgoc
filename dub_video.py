#!/usr/bin/env python3
"""
Script lồng tiếng từ file âm thanh (.mp3) vào video gốc trong thư mục sample,
xuất ra thư mục output với âm lượng nền giảm < 3dB theo yêu cầu.
"""

import sys
import argparse
from pathlib import Path

# Thêm thư mục gốc vào sys.path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from srt_to_voice.dubber import dub_video


def main():
    parser = argparse.ArgumentParser(
        description="Lồng tiếng file .mp3 vào video gốc và xuất ra thư mục output."
    )
    parser.add_argument(
        "--video",
        type=str,
        default=str(current_dir / "sample" / "sample.mp4"),
        help="Đường dẫn file video gốc (mặc định: sample/sample.mp4)."
    )
    parser.add_argument(
        "--voice",
        type=str,
        default=str(current_dir / "sample" / "srt" / "sample_voice_nu.mp3"),
        help="Đường dẫn file voice .mp3 (mặc định: sample/srt/sample_voice_nu.mp3)."
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=str(current_dir / "output" / "sample_dubbed.mp4"),
        help="Đường dẫn file video xuất ra (mặc định: output/sample_dubbed.mp4)."
    )
    parser.add_argument(
        "--bg-volume",
        type=str,
        default="-3dB",
        help="Mức giảm âm lượng nền gốc (mặc định: -3dB)."
    )
    parser.add_argument(
        "--voice-volume",
        type=str,
        default="0dB",
        help="Mức âm lượng của giọng lồng tiếng (mặc định: 0dB)."
    )

    args = parser.parse_args()

    result = dub_video(
        video_path=args.video,
        voice_audio_path=args.voice,
        output_path=args.output,
        bg_volume_db=args.bg_volume,
        voice_volume_db=args.voice_volume,
    )
    print(f"\n[Thành công] Video hoàn chỉnh: {result}")


if __name__ == "__main__":
    main()
