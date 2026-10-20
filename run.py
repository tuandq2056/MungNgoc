#!/usr/bin/env python3
"""
Script chạy mẫu nhanh cho thư mục sample.
Tự động quét các video trong /home/tuanlala/.gemini/antigravity/scratch/mungngoc/sample
và xuất phụ đề vào /home/tuanlala/.gemini/antigravity/scratch/mungngoc/sample/srt
"""

import sys
from pathlib import Path

# Thêm thư mục hiện tại vào sys.path để import module extract_srt_from_video
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from extract_srt_from_video import process_folder

if __name__ == "__main__":
    sample_dir = current_dir / "sample"
    srt_dir = sample_dir / "srt"
    
    print(f"Bắt đầu xử lý video trong: {sample_dir}")
    print(f"Thư mục lưu phụ đề .srt: {srt_dir}")
    
    # mode='all': tạo sample.srt (song ngữ), sample.zh.srt (tiếng Trung), sample.vi.srt (tiếng Việt)
    results = process_folder(
        folder_path=sample_dir,
        output_dir=srt_dir,
        mode="all"
    )
    
    print("\nDanh sách file .srt đã tạo:")
    for res in results:
        print(f" -> {res}")
