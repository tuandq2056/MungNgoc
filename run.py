#!/usr/bin/env python3
"""
Script 1-Click: Chạy trọn gói Pipeline liên kết 3 module cho toàn bộ video trong sample/
"""

import sys
from pathlib import Path

current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from pipeline import run_pipeline

if __name__ == "__main__":
    sample_dir = current_dir / "sample"
    output_dir = current_dir / "output"
    
    run_pipeline(
        input_target=sample_dir,
        output_dir=output_dir,
        voice="nu_chuan",
        bg_volume="-3dB"
    )
