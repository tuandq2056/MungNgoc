#!/usr/bin/env python3
"""
Script 1-Click: Chạy trọn gói End-to-End cho toàn bộ video trong thư mục sample/
Tự động: Bóc tách tiếng Trung -> Dịch Qwen -> Tạo Voice tiếng Việt -> Hòa âm video (-3dB) vào output/
"""

import sys
from pathlib import Path

current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from auto_dub import run_pipeline

if __name__ == "__main__":
    sample_dir = current_dir / "sample"
    output_dir = current_dir / "output"
    
    # Chạy pipeline với giọng Nữ chuẩn (nu_chuan) hoặc Nam thuyết minh (nam_thuyet_minh)
    results = run_pipeline(
        input_target=sample_dir,
        output_dir=output_dir,
        voice="nu_chuan",
        bg_volume="-3dB"
    )
