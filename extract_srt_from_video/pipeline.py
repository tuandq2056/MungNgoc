import os
from pathlib import Path
from typing import Optional

from .audio import extract_audio_from_video
from .config import SUPPORTED_VIDEO_EXTENSIONS
from .models import ensure_models
from .vad import VoiceActivitySegmenter, SpeechSegment
from .asr import SenseVoiceASR
from .translator import SubtitleTranslator
from .srt import SrtEntry, write_srt_file


def process_video(
    video_path: str | Path,
    output_dir: Optional[str | Path] = None,
    mode: str = "bilingual",
    num_threads: int = 4,
    segmenter: Optional[VoiceActivitySegmenter] = None,
    asr: Optional[SenseVoiceASR] = None,
    translator: Optional[SubtitleTranslator] = None,
) -> Path:
    """
    Xử lý một file video đơn lẻ: bóc tách lời thoại tiếng Trung và tạo file .srt.

    Args:
        video_path: Đường dẫn tới file video.
        output_dir: Thư mục lưu file srt. Nếu None, sẽ lưu vào folder 'srt' cùng cấp với video.
        mode: 
            - 'bilingual': Phụ đề song ngữ (Dòng 1: Tiếng Trung, Dòng 2: Tiếng Việt).
            - 'zh': Chỉ phụ đề tiếng Trung gốc.
            - 'vi': Chỉ phụ đề tiếng Việt.
            - 'all': Tạo cả 3 file (.srt song ngữ, .zh.srt tiếng Trung, .vi.srt tiếng Việt).
        num_threads: Số luồng CPU cho SenseVoice.
        segmenter: VoiceActivitySegmenter dùng lại (tránh khởi tạo lại nhiều lần khi xử lý hàng loạt).
        asr: SenseVoiceASR dùng lại.
        translator: SubtitleTranslator dùng lại.

    Returns:
        Đường dẫn tới file .srt chính được tạo ra.
    """
    video_path = Path(video_path).resolve()
    if not video_path.exists():
        raise FileNotFoundError(f"Không tìm thấy video: {video_path}")

    # Xác định thư mục đầu ra
    if output_dir is None:
        out_folder = video_path.parent / "srt"
    else:
        out_folder = Path(output_dir).resolve()
    out_folder.mkdir(parents=True, exist_ok=True)

    print(f"\n[pipeline] === Đang xử lý video: {video_path.name} ===")

    # 1. Đảm bảo model đã sẵn sàng
    if asr is None or segmenter is None:
        model_onnx, tokens_txt, vad_onnx = ensure_models()
        if segmenter is None:
            segmenter = VoiceActivitySegmenter(vad_onnx)
        if asr is None:
            asr = SenseVoiceASR(model_onnx, tokens_txt, num_threads=num_threads)

    if translator is None and mode in ("bilingual", "vi", "all"):
        translator = SubtitleTranslator()

    # 2. Trích xuất âm thanh 16kHz mono float32
    print("[pipeline] 1/4. Trích xuất âm thanh bằng ffmpeg...")
    samples, sample_rate = extract_audio_from_video(video_path)
    duration_sec = len(samples) / sample_rate
    print(f"[pipeline]    Độ dài âm thanh: {duration_sec:.2f} giây.")

    # 3. Phân đoạn giọng nói bằng VAD
    print("[pipeline] 2/4. Phân đoạn tiếng nói bằng Silero-VAD...")
    segments = segmenter.segment(samples)
    print(f"[pipeline]    Phát hiện {len(segments)} đoạn có giọng nói.")

    if not segments:
        print("[pipeline] Cảnh báo: Không phát hiện đoạn thoại nào trong video.")
        # Tạo file srt rỗng hợp lệ
        empty_srt = out_folder / f"{video_path.stem}.srt"
        write_srt_file([], empty_srt)
        return empty_srt

    # 4. Nhận diện giọng nói với SenseVoice và dịch thuật
    print(f"[pipeline] 3/4. Nhận diện bằng SenseVoice-Small & xử lý chế độ [{mode}]...")
    entries_bilingual: list[SrtEntry] = []
    entries_zh: list[SrtEntry] = []
    entries_vi: list[SrtEntry] = []

    valid_idx = 1
    for i, seg in enumerate(segments, 1):
        zh_text = asr.transcribe_segment(seg.samples)
        if not zh_text:
            continue

        print(f"  [{seg.start_sec:.2f}s -> {seg.end_sec:.2f}s] ZH: {zh_text}")

        vi_text = ""
        if translator and mode in ("bilingual", "vi", "all"):
            vi_text = translator.translate(zh_text)
            print(f"  {' ' * len(f'[{seg.start_sec:.2f}s -> {seg.end_sec:.2f}s]')} VI: {vi_text}")

        # Chuẩn bị nội dung theo mode
        if mode in ("bilingual", "all"):
            bi_text = f"{zh_text}\n{vi_text}" if vi_text else zh_text
            entries_bilingual.append(SrtEntry(index=valid_idx, start_sec=seg.start_sec, end_sec=seg.end_sec, text=bi_text))

        if mode in ("zh", "all"):
            entries_zh.append(SrtEntry(index=valid_idx, start_sec=seg.start_sec, end_sec=seg.end_sec, text=zh_text))

        if mode in ("vi", "all"):
            entries_vi.append(SrtEntry(index=valid_idx, start_sec=seg.start_sec, end_sec=seg.end_sec, text=vi_text or zh_text))

        valid_idx += 1

    # 5. Ghi file .srt
    print("[pipeline] 4/4. Xuất file phụ đề .srt vào thư mục srt...")
    main_file = out_folder / f"{video_path.stem}.srt"

    if mode == "bilingual":
        write_srt_file(entries_bilingual, main_file)
    elif mode == "zh":
        write_srt_file(entries_zh, main_file)
    elif mode == "vi":
        write_srt_file(entries_vi, main_file)
    elif mode == "all":
        write_srt_file(entries_bilingual, main_file)
        write_srt_file(entries_zh, out_folder / f"{video_path.stem}.zh.srt")
        write_srt_file(entries_vi, out_folder / f"{video_path.stem}.vi.srt")

    print(f"[pipeline] [V] Đã tạo thành công file: {main_file}")
    return main_file


def process_folder(
    folder_path: str | Path,
    output_dir: Optional[str | Path] = None,
    mode: str = "bilingual",
    num_threads: int = 4,
) -> list[Path]:
    """
    Quét và xử lý tất cả các file video trong một thư mục.
    """
    folder_path = Path(folder_path).resolve()
    if not folder_path.exists() or not folder_path.is_dir():
        raise NotADirectoryError(f"Thư mục không tồn tại: {folder_path}")

    # Tìm các file video
    video_files = [
        f for f in folder_path.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS
    ]
    video_files.sort()

    if not video_files:
        print(f"[pipeline] Không tìm thấy file video nào trong: {folder_path}")
        return []

    print(f"[pipeline] Tìm thấy {len(video_files)} video cần xử lý trong: {folder_path}")

    # Khởi tạo mô hình dùng chung 1 lần để tối ưu tốc độ
    model_onnx, tokens_txt, vad_onnx = ensure_models()
    segmenter = VoiceActivitySegmenter(vad_onnx)
    asr = SenseVoiceASR(model_onnx, tokens_txt, num_threads=num_threads)
    translator = SubtitleTranslator() if mode in ("bilingual", "vi", "all") else None

    results: list[Path] = []
    for video_file in video_files:
        srt_path = process_video(
            video_path=video_file,
            output_dir=output_dir,
            mode=mode,
            num_threads=num_threads,
            segmenter=segmenter,
            asr=asr,
            translator=translator,
        )
        results.append(srt_path)

    return results


def extract_srt(
    target: str | Path,
    output_dir: Optional[str | Path] = None,
    mode: str = "bilingual",
    num_threads: int = 4,
) -> list[Path]:
    """Hàm giao diện tổng quát nhận vào đường dẫn file video hoặc thư mục."""
    target_path = Path(target).resolve()
    if target_path.is_dir():
        return process_folder(target_path, output_dir=output_dir, mode=mode, num_threads=num_threads)
    elif target_path.is_file():
        return [process_video(target_path, output_dir=output_dir, mode=mode, num_threads=num_threads)]
    else:
        raise FileNotFoundError(f"Đường dẫn không tồn tại: {target}")
