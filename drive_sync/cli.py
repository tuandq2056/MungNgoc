#!/usr/bin/env python3
"""
CLI độc lập trao đổi file với Google Drive (qua rclone) theo contract của dự án.
    python3 -m drive_sync push-code                 # đẩy qwen_translate/ + glossary.txt
    python3 -m drive_sync push work/zh              # đẩy các .srt tiếng Trung (file hoặc thư mục)
    python3 -m drive_sync pull work/vi              # tải mọi bản dịch đã có
    python3 -m drive_sync status                    # xem outbox và worker Colab
"""

import argparse
import sys
import time
from pathlib import Path

from . import drive

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(prog="drive_sync", description="Trao đổi file với Google Drive qua rclone.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("push-code", help="Đẩy qwen_translate/ và glossary.txt lên Drive")
    p_push = sub.add_parser("push", help="Đẩy phụ đề tiếng Trung lên inbox/")
    p_push.add_argument("path", help="File .srt hoặc thư mục chứa các file đó")
    p_push.add_argument("--retranslate", action="store_true", help="Xóa bản dịch cũ trên Drive để Colab dịch lại")
    p_pull = sub.add_parser("pull", help="Tải bản dịch từ outbox/ về máy")
    p_pull.add_argument("dest", help="Thư mục lưu")
    sub.add_parser("status", help="Xem outbox và trạng thái worker Colab")
    args = parser.parse_args()

    try:
        if args.cmd == "push-code":
            drive.push_code(PROJECT_ROOT)
            print("Đã đẩy code + glossary lên", drive.remote())
        elif args.cmd == "push":
            target = Path(args.path)
            files = sorted(p for p in target.glob("*.srt") if not p.name.endswith(".vi.srt")) if target.is_dir() else [target]
            for f in files:
                if args.retranslate:
                    drive.clear_result(f.name.removesuffix(".srt").removesuffix(".zh"))
                drive.push_srt(f)
                print("  ↑", f.name)
        elif args.cmd == "pull":
            for name in sorted(n for n in drive.list_outbox() if n.endswith(".vi.srt")):
                print("  ↓", drive.pull(name, Path(args.dest)).name)
        elif args.cmd == "status":
            names = sorted(drive.list_outbox())
            print("outbox:", ", ".join(names) or "(trống)")
            st = drive.worker_status()
            if st:
                print(f"worker: thấy lần cuối {time.time() - st.get('time', 0):.0f}s trước | model {st.get('model')} | đang dịch: {st.get('busy') or '-'}")
            else:
                print("worker: chưa thấy (chạy notebook colab/translate_worker.ipynb)")
    except drive.DriveError as e:
        print(f"Lỗi: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
