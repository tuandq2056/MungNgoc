#!/usr/bin/env python3
"""
End-to-End Dubbing Pipeline
===========================
Quy trình tự động hóa toàn diện từ A - Z:
1. Nạp video từ thư mục sample (hoặc file video bất kỳ).
2. Bóc tách tiếng Trung (SenseVoice) & Dịch ngữ nghĩa sang tiếng Việt (Qwen).
3. Sinh giọng đọc lồng tiếng tiếng Việt khớp timeline (Edge-TTS).
4. Hòa âm lồng tiếng vào video gốc với âm lượng nền -3dB và xuất ra thư mục output.
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

# Đảm bảo import được các module nội bộ
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from extract_srt_from_video import process_video
from extract_srt_from_video.config import SUPPORTED_VIDEO_EXTENSIONS
from srt_to_voice import generate_voice_from_srt, list_available_voices
from srt_to_voice.dubber import dub_video


def process_single_video_e2e(
    video_path: Path,
    output_dir: Path,
    voice: str = "nu_chuan",
    bg_volume: str = "-3dB",
    max_speedup: float = 1.45,
) -> Path:
    """Xử lý end-to-end cho 1 video đơn lẻ."""
    video_path = video_path.resolve()
    print(f"\n{'='*60}")
    print(f"🎬 BẮT ĐẦU QUY TRÌNH END-TO-END CHO VIDEO: {video_path.name}")
    print(f"{'='*60}")

    # Bước 1: Bóc tách âm thanh & dịch phụ đề
    print("\n👉 [BƯỚC 1/3] Bóc tách tiếng Trung (SenseVoice) & Dịch sang tiếng Việt (Qwen)...")
    srt_dir = video_path.parent / "srt"
    main_srt = process_video(
        video_path=video_path,
        output_dir=srt_dir,
        mode="all"
    )
    
    # Tìm file phụ đề tiếng Việt để tạo voice
    vi_srt = srt_dir / f"{video_path.stem}.vi.srt"
    if not vi_srt.exists():
        vi_srt = main_srt  # Fallback nếu dùng mode khác

    # Bước 2: Tạo voice lồng tiếng khớp mốc thời gian
    print(f"\n👉 [BƯỚC 2/3] Sinh giọng đọc tiếng Việt ({voice}) khớp trục thời gian...")
    voice_audio_path = srt_dir / f"{video_path.stem}_voice_{voice}.mp3"
    generate_voice_from_srt(
        srt_path=vi_srt,
        output_audio=voice_audio_path,
        voice=voice,
        max_speedup=max_speedup,
    )

    # Bước 3: Hòa âm vào video gốc (-3dB nền)
    print(f"\n👉 [BƯỚC 3/3] Hòa âm lồng tiếng vào video gốc (âm lượng nền {bg_volume})...")
    output_dir.mkdir(parents=True, exist_ok=True)
    dubbed_video_path = output_dir / f"{video_path.stem}_dubbed.mp4"
    
    final_video = dub_video(
        video_path=video_path,
        voice_audio_path=voice_audio_path,
        output_path=dubbed_video_path,
        bg_volume_db=bg_volume,
        voice_volume_db="0dB",
    )

    print(f"\n✨ [HOÀN TẤT] Video lồng tiếng hoàn chỉnh: {final_video}")
    return final_video


def run_pipeline(
    input_target: str | Path,
    output_dir: Optional[str | Path] = None,
    voice: str = "nu_chuan",
    bg_volume: str = "-3dB",
    max_speedup: float = 1.45,
) -> list[Path]:
    """
    Chạy pipeline end-to-end cho 1 file video hoặc quét toàn bộ video trong thư mục.
    """
    target = Path(input_target).resolve()
    if not target.exists():
        raise FileNotFoundError(f"Không tìm thấy đường dẫn: {target}")

    if output_dir is None:
        out_dir = current_dir / "output"
    else:
        out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    results: list[Path] = []

    if target.is_file():
        res = process_single_video_e2e(
            video_path=target,
            output_dir=out_dir,
            voice=voice,
            bg_volume=bg_volume,
            max_speedup=max_speedup,
        )
        results.append(res)
    elif target.is_dir():
        video_files = [
            f for f in target.iterdir()
            if f.is_file() and f.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS
        ]
        video_files.sort()

        if not video_files:
            print(f"[pipeline] Không tìm thấy file video nào trong: {target}")
            return []

        print(f"[pipeline] Tìm thấy {len(video_files)} video cần xử lý trong: {target}")
        for vf in video_files:
            res = process_single_video_e2e(
                video_path=vf,
                output_dir=out_dir,
                voice=voice,
                bg_volume=bg_volume,
                max_speedup=max_speedup,
            )
            results.append(res)

    return results


def main():
    parser = argparse.ArgumentParser(
        prog="auto_dub",
        description="Pipeline End-to-End: Nạp video tiếng Trung -> Xuất video lồng tiếng tiếng Việt hoàn chỉnh."
    )
    parser.add_argument(
        "input",
        type=str,
        nargs="?",
        default=str(current_dir / "sample"),
        help="Đường dẫn file video hoặc thư mục chứa video (mặc định: ./sample)."
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=str,
        default=str(current_dir / "output"),
        help="Thư mục xuất video lồng tiếng (mặc định: ./output)."
    )
    parser.add_argument(
        "-v", "--voice",
        type=str,
        default="nu_chuan",
        help="Preset giọng đọc (nu_chuan, nam_thuyet_minh, nu_tre, nam_co_trang... Mặc định: nu_chuan)."
    )
    parser.add_argument(
        "--bg-volume",
        type=str,
        default="-3dB",
        help="Mức giảm âm lượng nền gốc (mặc định: -3dB)."
    )
    parser.add_argument(
        "--max-speedup",
        type=float,
        default=1.45,
        help="Tỷ lệ tăng tốc tối đa nếu câu đọc dài hơn cảnh phim (mặc định: 1.45x)."
    )
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="Liệt kê danh sách các giọng đọc có sẵn."
    )

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
        print(f"\n{'='*60}")
        print(f"🎉 TỔNG KẾT: Đã hoàn tất lồng tiếng cho {len(results)} video!")
        print(f"{'='*60}")
        for r in results:
            print(f" 👉 {r}")
    except Exception as e:
        print(f"\n❌ Lỗi pipeline: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
