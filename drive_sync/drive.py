"""
Trao đổi file với Google Drive qua rclone theo "contract" thư mục (xem README.md cùng thư mục).
Phía máy nhà dùng module này; phía Colab chỉ đọc/ghi thẳng vào Drive đã mount.
Module độc lập, chỉ cần rclone đã cài và đã `rclone config` một remote Google Drive.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

DEFAULT_REMOTE = "gdrive:MungNgoc"
IGNORED_DIRS = ("__pycache__/**", "*.pyc")


class DriveError(RuntimeError):
    pass


def remote() -> str:
    return os.environ.get("DRIVE_REMOTE", DEFAULT_REMOTE).rstrip("/")


def ensure_rclone() -> None:
    if not shutil.which("rclone"):
        raise DriveError(
            "Chưa cài rclone. Cài (vd. `sudo dnf install rclone`), rồi chạy `rclone config` tạo remote Google Drive tên 'gdrive' "
            "(hoặc đặt DRIVE_REMOTE=<remote>:<thư mục>)."
        )


def _run(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    ensure_rclone()
    proc = subprocess.run(["rclone", *args], capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise DriveError(f"rclone {' '.join(args[:2])} lỗi ({proc.returncode}): {proc.stderr.strip()[-300:]}")
    return proc


def push_code(project_root: Path) -> None:
    """Đẩy qwen_translate/ và glossary.txt lên code/ để Colab dùng đúng bản mới nhất."""
    project_root = Path(project_root)
    exclude = [x for pat in IGNORED_DIRS for x in ("--exclude", pat)]
    _run("copy", str(project_root / "qwen_translate"), f"{remote()}/code/qwen_translate", *exclude)
    glossary = project_root / "glossary.txt"
    if glossary.is_file():
        _run("copyto", str(glossary), f"{remote()}/code/glossary.txt")


def push_srt(path: Path) -> None:
    """Đẩy một file phụ đề tiếng Trung lên inbox/."""
    path = Path(path)
    _run("copyto", str(path), f"{remote()}/inbox/{path.name}")


def clear_result(stem: str) -> None:
    """Xóa kết quả cũ của một tập để dịch lại (bản dịch + file lỗi)."""
    for name in (f"{stem}.vi.srt", f"{stem}.fail.txt"):
        _run("deletefile", f"{remote()}/outbox/{name}", check=False)


def list_outbox() -> set[str]:
    """Tên các file trong outbox/ (bỏ file .tmp đang ghi dở). Outbox chưa tồn tại thì trả tập rỗng."""
    proc = _run("lsf", f"{remote()}/outbox", "--files-only", check=False)
    if proc.returncode != 0:
        return set()
    return {n.strip() for n in proc.stdout.splitlines() if n.strip() and not n.strip().endswith(".tmp")}


def pull(name: str, dest_dir: Path) -> Path:
    """Tải outbox/<name> về dest_dir (ghi tạm rồi đổi tên để không bao giờ thấy file dở)."""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    final, tmp = dest_dir / name, dest_dir / f"{name}.part"
    _run("copyto", f"{remote()}/outbox/{name}", str(tmp))
    tmp.replace(final)
    return final


def read_text(relpath: str) -> Optional[str]:
    """Đọc nội dung một file trên Drive; không có thì None."""
    proc = _run("cat", f"{remote()}/{relpath}", check=False)
    return proc.stdout if proc.returncode == 0 else None


def worker_status() -> Optional[dict]:
    """Trạng thái worker Colab ({"time": epoch, "busy": ..., "model": ...}) hoặc None nếu chưa thấy."""
    text = read_text("status/worker.json")
    try:
        return json.loads(text) if text else None
    except json.JSONDecodeError:
        return None
