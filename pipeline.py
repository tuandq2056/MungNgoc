#!/usr/bin/env python3
"""
Pipeline Orchestrator
=====================
Điều phối liên kết 3 module độc lập theo luồng khép kín:
1. extract_srt_from_video: Bóc tách tiếng Trung (SenseVoice) & Dịch Qwen ra .srt
2. srt_to_voice: Tạo âm thanh lồng tiếng tiếng Việt khớp timeline từ file .srt
3. video_dubber: Hòa âm file voice vào video gốc với âm lượng nền -3dB
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Import trực tiếp từ 3 module chuyên biệt
from extract_srt_from_video import process_video
from extract_srt_from_video.config import SUPPORTED_VIDEO_EXTENSIONS
from srt_to_voice import generate_voice_from_srt, list_available_voices
from video_dubber import dub_video


def process_video_pipeline(
    video_path: Path,
    output_dir: Path,
    voice: str = "nu_chuan",
    bg_volume: str = "-3dB",
    max_speedup: float = 1.45,
) -> Path:
    """Xử lý quy trình lồng tiếng hoàn chỉnh cho 1 video."""
    video_path = video_path.resolve()
    print(f"\n{'='*60}")
    print(f"🎬 [PIPELINE] BẮT ĐẦU XỬ LÝ VIDEO: {video_path.name}")
    print(f"{'='*60}")

    # BƯỚC 1: Module extract_srt_from_video
    print("\n👉 [BƯỚC 1/3] Gọi module [extract_srt_from_video] (SenseVoice + Qwen)...")
    srt_dir = video_path.parent / "srt"
    main_srt = process_video(
        video_path=video_path,
        output_dir=srt_dir,
        mode="all",
    )
    vi_srt = srt_dir / f"{video_path.stem}.vi.srt"
    if not vi_srt.exists():
        vi_srt = main_srt

    # BƯỚC 2: Module srt_to_voice
    print(f"\n👉 [BƯỚC 2/3] Gọi module [srt_to_voice] ({voice} - Edge-TTS)...")
    voice_audio_path = srt_dir / f"{video_path.stem}_voice_{voice}.mp3"
    generate_voice_from_srt(
        srt_path=vi_srt,
        output_audio=voice_audio_path,
        voice=voice,
        max_speedup=max_speedup,
    )

    # BƯỚC 3: Module video_dubber
    print(f"\n👉 [BƯỚC 3/3] Gọi module [video_dubber] (FFmpeg amix {bg_volume})...")
    output_dir.mkdir(parents=True, exist_ok=True)
    dubbed_video_path = output_dir / f"{video_path.stem}_dubbed.mp4"
    final_video = dub_video(
        video_path=video_path,
        voice_audio_path=voice_audio_path,
        output_path=dubbed_video_path,
        bg_volume_db=bg_volume,
        voice_volume_db="0dB",
    )

    print(f"\n✨ [HOÀN TẤT] Video lồng tiếng: {final_video}")
    return final_video


def run_pipeline(
    input_target: str | Path,
    output_dir: Optional[str | Path] = None,
    voice: str = "nu_chuan",
    bg_volume: str = "-3dB",
    max_speedup: float = 1.45,
) -> list[Path]:
    target = Path(input_target).resolve()
    if not target.exists():
        raise FileNotFoundError(f"Không tìm thấy: {target}")

    if output_dir is None:
        out_dir = current_dir / "output"
    else:
        out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    if target.is_file():
        res = process_video_pipeline(target, out_dir, voice, bg_volume, max_speedup)
        results.append(res)
    elif target.is_dir():
        videos = [
            f for f in target.iterdir()
            if f.is_file() and f.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS
        ]
        videos.sort()
        print(f"[pipeline] Tìm thấy {len(videos)} video cần lồng tiếng trong: {target}")
        for v in videos:
            res = process_video_pipeline(v, out_dir, voice, bg_volume, max_speedup)
            results.append(res)

    return results


def main():
    parser = argparse.ArgumentParser(
        prog="pipeline",
        description="Pipeline liên kết 3 module: extract_srt_from_video -> srt_to_voice -> video_dubber."
    )
    parser.add_argument("input", type=str, nargs="?", default="sample", help="File video hoặc thư mục (mặc định: ./sample)")
    parser.add_argument("-o", "--output-dir", type=str, default="output", help="Thư mục xuất video (mặc định: ./output)")
    parser.add_argument("-v", "--voice", type=str, default="nu_chuan", help="Giọng đọc (mặc định: nu_chuan)")
    parser.add_argument("--bg-volume", type=str, default="-3dB", help="Mức giảm âm lượng nền (mặc định: -3dB)")
    parser.add_argument("--max-speedup", type=float, default=1.45, help="Tỷ lệ tăng tốc tối đa (mặc định: 1.45x)")
    parser.add_argument("--list-voices", action="store_true", help="Xem danh sách giọng đọc")

    args = parser.parse_args()

    if args.list_voices:
        print("\n=== DANH SÁCH GIỌNG ĐỌC CÓ SẴN ===")
        for v in list_available_voices():
            print(f" • {v['key']:<16} | {v['gender']:<6} | {v['description']}")
        sys.exit(0)

    try:
        results = run_pipeline(
            input_target=args.input,
            output_dir=args.output_dir,
            voice=args.voice,
            bg_volume=args.bg_volume,
            max_speedup=args.max_speedup,
        )
        print(f"\n[Hoàn tất] Đã xử lý xong {len(results)} video.")
    except Exception as e:
        print(f"\nLỗi: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
