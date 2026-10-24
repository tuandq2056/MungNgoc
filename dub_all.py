#!/usr/bin/env python3
"""
Điều phối cho máy nhà (file riêng, không thay run.py / pipeline.py):
    extractor (chỉ tiếng Trung) -> đẩy lên Google Drive -> Colab dịch -> tải .vi.srt về -> đọc giọng -> ghép video.
Toàn bộ trạng thái nằm trong file nên dừng (Ctrl+C) rồi chạy lại sẽ tiếp tục đúng chỗ.

    python3 dub_all.py                 # xử lý mọi video trong sample/
    python3 dub_all.py sample/tap3.mp4 # một video
Chi tiết từng bước ghi vào logs/dub_all.log (xem trực tiếp: tail -f logs/dub_all.log); màn hình chỉ hiện thanh tiến độ.
"""

import argparse
import contextlib
import sys
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tqdm import tqdm

from drive_sync import drive
from qwen_translate.translate import is_speakable, load_dotenv, parse_srt

MAX_BLANK_RATIO = 0.2
TTS_ATTEMPTS = 3
WORKER_STALE_SEC = 300


def log(msg: str) -> None:
    tqdm.write(msg, file=sys.stderr)


@contextlib.contextmanager
def quiet(log_path: Path):
    """Đưa print của các module (extract/TTS/ffmpeg) vào file log, màn hình chỉ còn thanh tiến độ."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8", buffering=1) as f, contextlib.redirect_stdout(f):
        yield


def check_translation(zh_path: Path, vi_path: Path) -> Optional[str]:
    """Kiểm tra bản dịch tải về theo contract; trả về mô tả lỗi hoặc None nếu hợp lệ."""
    zh, vi = parse_srt(zh_path), parse_srt(vi_path)
    if len(zh) != len(vi):
        return f"số cue lệch ({len(vi)} dịch / {len(zh)} gốc)"
    if any(a[1] != b[1] for a, b in zip(zh, vi)):
        return "dòng thời gian không khớp với bản gốc"
    speakable = [i for i, c in enumerate(zh) if is_speakable(c[2])]
    blank = [i for i in speakable if not vi[i][2].strip()]
    if speakable and len(blank) / len(speakable) > MAX_BLANK_RATIO:
        return f"{len(blank)}/{len(speakable)} câu trống (quá ngưỡng {MAX_BLANK_RATIO:.0%})"
    return None


class Runner:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.work = Path(args.work)
        self.out_dir = Path(args.output)
        self.zh_dir, self.vi_dir, self.voice_dir = self.work / "zh", self.work / "vi", self.work / "voice"
        self.log_path = ROOT / "logs" / "dub_all.log"
        self.models: Optional[tuple] = None
        self.waiting: dict[str, Path] = {}  # stem -> video, đang chờ Colab dịch
        self.failures: list[tuple[str, str]] = []
        self.done = 0
        self.bar: Optional[tqdm] = None
        self.worker_warned = False

    # ---- các bước ----
    def extract_zh(self, video: Path) -> Path:
        zh_path = self.zh_dir / f"{video.stem}.srt"
        if zh_path.exists():
            return zh_path
        with quiet(self.log_path):
            from extract_srt_from_video import process_video
            from extract_srt_from_video.asr import SenseVoiceASR
            from extract_srt_from_video.models import ensure_models
            from extract_srt_from_video.vad import VoiceActivitySegmenter

            if self.models is None:
                model_onnx, tokens_txt, vad_onnx = ensure_models()
                self.models = (VoiceActivitySegmenter(vad_onnx), SenseVoiceASR(model_onnx, tokens_txt, num_threads=4))
            segmenter, asr = self.models
            process_video(video, output_dir=self.zh_dir, mode="zh", segmenter=segmenter, asr=asr)
        return zh_path

    def dub(self, video: Path, vi_path: Path) -> None:
        from srt_to_voice import generate_voice_from_srt
        from video_dubber import dub_video

        voice_path = self.voice_dir / f"{video.stem}.mp3"
        self.voice_dir.mkdir(parents=True, exist_ok=True)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        with quiet(self.log_path):
            for attempt in range(1, TTS_ATTEMPTS + 1):
                try:
                    generate_voice_from_srt(srt_path=vi_path, output_audio=voice_path, voice=self.args.voice, max_speedup=1.45)
                    break
                except Exception as e:
                    print(f"[dub_all] lỗi TTS {video.stem} lần {attempt}/{TTS_ATTEMPTS}: {e}")
                    if attempt == TTS_ATTEMPTS:
                        raise
            dub_video(
                video_path=video, voice_audio_path=voice_path, output_path=self.out_dir / f"{video.stem}.mp4",
                bg_volume_db=self.args.bg_volume, voice_volume_db="0dB",
            )

    def finish(self, stem: str, video: Path, vi_path: Path) -> None:
        """Kiểm tra bản dịch rồi đọc giọng + ghép video cho một tập."""
        self.bar.set_description(f"{stem}: đọc giọng + ghép video")
        try:
            problem = check_translation(self.zh_dir / f"{stem}.srt", vi_path)
            if problem:
                raise RuntimeError(f"bản dịch không đạt contract: {problem}")
            self.dub(video, vi_path)
            self.done += 1
            log(f"  ✔ {stem}")
        except Exception as e:
            self.failures.append((stem, str(e)))
            log(f"  ✘ {stem}: {e}")
        self.bar.update(1)

    def poll(self) -> None:
        """Xem outbox trên Drive: tập nào dịch xong thì tải về và làm tiếp, tập nào lỗi thì ghi nhận."""
        if not self.waiting:
            return
        names = drive.list_outbox()
        for stem, video in list(self.waiting.items()):
            if f"{stem}.vi.srt" in names:
                del self.waiting[stem]
                self.bar.set_description(f"{stem}: tải bản dịch")
                self.finish(stem, video, drive.pull(f"{stem}.vi.srt", self.vi_dir))
            elif f"{stem}.fail.txt" in names:
                del self.waiting[stem]
                reason = (drive.read_text(f"outbox/{stem}.fail.txt") or "").strip() or "không rõ lý do"
                self.failures.append((stem, f"Colab dịch lỗi: {reason}"))
                log(f"  ✘ {stem}: Colab dịch lỗi: {reason}")
                self.bar.update(1)

    def queue_for_translation(self, stem: str, video: Path, zh_path: Path) -> None:
        names = drive.list_outbox()
        if self.args.retranslate:
            drive.clear_result(stem)
        elif f"{stem}.fail.txt" in names and f"{stem}.vi.srt" not in names:
            drive.clear_result(stem)  # lỗi của lần chạy trước: thử lại một lần
        if self.args.retranslate or f"{stem}.vi.srt" not in names:
            drive.push_srt(zh_path)
        self.waiting[stem] = video

    def worker_note(self) -> str:
        st = drive.worker_status()
        if not st:
            return "chưa thấy worker Colab"
        age = time.time() - st.get("time", 0)
        if age > WORKER_STALE_SEC and not self.worker_warned:
            self.worker_warned = True
            log(f"  ! Worker Colab không phản hồi {age:.0f}s: kiểm tra notebook colab/translate_worker.ipynb còn chạy không.")
        return f"worker {age:.0f}s trước" + (f", đang dịch {st['busy']}" if st.get("busy") else "")

    # ---- luồng chính ----
    def run(self, videos: list[Path]) -> int:
        todo = [v for v in videos if not (self.out_dir / f"{v.stem}.mp4").exists()]
        skipped = len(videos) - len(todo)
        if skipped:
            log(f"[dub_all] Bỏ qua {skipped} video đã có trong {self.out_dir.name}/")
        if not todo:
            return 0

        if not self.args.skip_push_code:
            drive.push_code(ROOT)
        self.bar = tqdm(total=len(todo), unit="tập", file=sys.stderr, dynamic_ncols=True)

        for video in todo:
            stem = video.stem
            local_vi = self.vi_dir / f"{stem}.vi.srt"
            if local_vi.exists() and not self.args.retranslate:
                self.finish(stem, video, local_vi)
            else:
                self.bar.set_description(f"{stem}: tách tiếng Trung")
                zh_path = self.extract_zh(video)
                self.queue_for_translation(stem, video, zh_path)
            self.poll()  # tập nào Colab dịch xong trong lúc đang tách thì làm luôn

        while self.waiting:
            self.bar.set_description("chờ Colab dịch")
            self.bar.set_postfix_str(f"{len(self.waiting)} tập | {self.worker_note()}")
            time.sleep(self.args.poll)
            self.poll()

        self.bar.close()
        log(f"\n[dub_all] Xong {self.done}/{len(todo)} tập. Chi tiết: {self.log_path}")
        for stem, err in self.failures:
            log(f"  ✘ {stem}: {err}")
        return 1 if self.failures else 0


def main() -> None:
    load_dotenv()  # nạp .env (khóa Azure Speech...) cho bước đọc giọng
    parser = argparse.ArgumentParser(prog="dub_all", description="Tách tiếng Trung -> Colab dịch qua Drive -> đọc giọng -> ghép video.")
    parser.add_argument("input", nargs="?", default="sample", help="File video hoặc thư mục (mặc định: sample)")
    parser.add_argument("--work", default="work", help="Thư mục làm việc: zh/ vi/ voice/ (mặc định: work)")
    parser.add_argument("-o", "--output", default="output", help="Thư mục xuất video (mặc định: output)")
    parser.add_argument("-v", "--voice", default="nu_chuan", help="Giọng đọc (mặc định: nu_chuan)")
    parser.add_argument("--bg-volume", default="-3dB", help="Mức giảm âm lượng nền (mặc định: -3dB)")
    parser.add_argument("--poll", type=int, default=30, help="Giây giữa các lần kiểm tra Drive (mặc định: 30)")
    parser.add_argument("--retranslate", action="store_true", help="Dịch lại các tập chưa có video, bỏ bản dịch cũ")
    parser.add_argument("--skip-push-code", action="store_true", help="Không đẩy lại qwen_translate/ và glossary.txt lên Drive")
    args = parser.parse_args()

    target = Path(args.input)
    if target.is_dir():
        from extract_srt_from_video.config import SUPPORTED_VIDEO_EXTENSIONS
        videos = sorted(f for f in target.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS)
    elif target.is_file():
        videos = [target]
    else:
        print(f"Không tìm thấy: {target}", file=sys.stderr)
        sys.exit(1)

    try:
        sys.exit(Runner(args).run(videos))
    except drive.DriveError as e:
        print(f"Lỗi Drive: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nĐã dừng. Chạy lại cùng lệnh sẽ tiếp tục từ chỗ đang dở.", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
