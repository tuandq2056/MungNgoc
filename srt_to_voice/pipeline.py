import tempfile
import shutil
from pathlib import Path
from typing import Optional

from .srt_parser import parse_srt_file, SubtitleItem
from .voices import get_voice_profile
from .tts import make_tts
from .aligner import adjust_audio_speed
from .builder import build_timeline_audio


def generate_voice_from_srt(
    srt_path: str | Path,
    output_audio: Optional[str | Path] = None,
    voice: str = "nu_chuan",
    max_speedup: float = 1.45,
    save_segments: bool = False,
    segments_dir: Optional[str | Path] = None,
) -> Path:
    """
    Tạo file âm thanh lồng tiếng hoàn chỉnh khớp mốc thời gian từ file .srt tiếng Việt.

    Args:
        srt_path: Đường dẫn file .srt tiếng Việt.
        output_audio: Đường dẫn file âm thanh xuất ra (.mp3 hoặc .wav).
                      Nếu None, sẽ lưu cùng thư mục với srt và có đuôi `_voice.mp3`.
        voice: Tên preset giọng đọc (nu_chuan, nam_thuyet_minh, nu_tre, nam_co_trang...).
        max_speedup: Tỷ lệ tăng tốc tối đa nếu câu đọc dài hơn mốc thời gian (mặc định 1.45x).
        save_segments: Nếu True, lưu các file âm thanh lẻ của từng câu.
        segments_dir: Thư mục lưu các câu thoại lẻ.

    Returns:
        Đường dẫn tới file âm thanh lồng tiếng hoàn chỉnh.
    """
    srt_path = Path(srt_path).resolve()
    if not srt_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file phụ đề: {srt_path}")

    # 1. Xác định file đầu ra
    if output_audio is None:
        out_file = srt_path.parent / f"{srt_path.stem}_voice.mp3"
    else:
        out_file = Path(output_audio).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # 2. Phân tích file .srt
    items = parse_srt_file(srt_path)
    if not items:
        raise ValueError(f"File phụ đề {srt_path} không có câu thoại nào hợp lệ.")

    profile = get_voice_profile(voice)
    print(f"\n[srt_to_voice] === Đang tạo voice từ: {srt_path.name} ===")
    print(f"[srt_to_voice] Giọng đọc: {profile.name} ({profile.description})")
    print(f"[srt_to_voice] Tìm thấy {len(items)} câu thoại cần sinh giọng.")

    tts_gen = make_tts(profile)

    # Tạo thư mục tạm để lưu các câu thoại đơn lẻ
    temp_dir = Path(tempfile.mkdtemp(prefix="srt_voice_"))
    clips: list[tuple[float, Path]] = []
    total_duration_sec = items[-1].end_sec + 1.0

    if save_segments:
        if segments_dir is None:
            seg_out_dir = out_file.parent / f"{out_file.stem}_segments"
        else:
            seg_out_dir = Path(segments_dir).resolve()
        seg_out_dir.mkdir(parents=True, exist_ok=True)
    else:
        seg_out_dir = None

    try:
        for item in items:
            raw_clip_path = temp_dir / f"raw_{item.index:04d}.mp3"
            aligned_clip_path = temp_dir / f"aligned_{item.index:04d}.mp3"

            # Câu chỉ có dấu câu/ký hiệu thì không có gì để đọc
            if not any(c.isalnum() for c in item.text):
                print(f"  [{item.start_sec:.2f}s -> {item.end_sec:.2f}s] Bỏ qua (không có chữ để đọc): {item.text}")
                continue

            print(f"  [{item.start_sec:.2f}s -> {item.end_sec:.2f}s] Đang đọc: {item.text}")

            # Sinh âm thanh (Azure nếu có key, không thì Edge-TTS); hết số lần thử thì ném TTSError, không xuất video thiếu tiếng
            tts_gen.generate_speech_with_retry(item.text, raw_clip_path)

            # Căn chỉnh tốc độ cho vừa khung thời gian nếu bị dài hơn
            final_clip_path, final_dur = adjust_audio_speed(
                input_path=raw_clip_path,
                output_path=aligned_clip_path,
                target_duration=item.duration_sec,
                max_speedup=max_speedup,
            )

            clips.append((item.start_sec, final_clip_path))

            # Lưu lại nếu người dùng yêu cầu các câu lẻ
            if seg_out_dir:
                dest_seg = seg_out_dir / f"seg_{item.index:04d}.mp3"
                shutil.copy2(final_clip_path, dest_seg)

        if not clips:
            raise ValueError(f"Không có câu thoại nào đọc được trong {srt_path.name}; không xuất file voice rỗng.")

        # 3. Ghép toàn bộ vào trục thời gian (chèn silence chuẩn từng mili-giây)
        print(f"[srt_to_voice] Đang tổng hợp và khớp trục thời gian vào: {out_file.name}...")
        build_timeline_audio(
            clips=clips,
            total_duration_sec=total_duration_sec,
            output_file=out_file,
        )
        print(f"[srt_to_voice] [V] Đã tạo thành công file lồng tiếng: {out_file}")

    finally:
        # Dọn dẹp thư mục tạm
        shutil.rmtree(temp_dir, ignore_errors=True)

    return out_file
