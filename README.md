# 🎬 Hệ Thống Bóc Tách, Dịch Thuật & Lồng Tiếng Video (Multi-Module Pipeline)

> **Kiến trúc đa module độc lập**: Dự án được chia thành 3 module chuyên biệt, mỗi module có thư mục riêng, quản lý độc lập và có thể chạy riêng lẻ hoặc phối hợp nhịp nhàng qua Pipeline điều phối.

---

## 🏗️ 1. Cấu Trúc 3 Module Độc Lập

```text
├── extract_srt_from_video/    # MODULE 1: Bóc tách tiếng Trung (SenseVoice) & Dịch ngữ nghĩa (Qwen)
│   ├── asr.py                 # Nhận diện âm thanh SenseVoice-Small ONNX
│   ├── vad.py                 # Cắt đoạn giọng nói Silero-VAD
│   ├── translator.py          # Dịch ngữ cảnh bằng Qwen LLM + Fallback
│   ├── audio.py               # Trích xuất âm thanh từ video bằng ffmpeg
│   ├── srt.py                 # Xuất file .srt chuẩn (song ngữ, zh, vi)
│   └── cli.py                 # CLI độc lập: python3 -m extract_srt_from_video
│
├── srt_to_voice/              # MODULE 2: Sinh giọng đọc lồng tiếng từ file .srt tiếng Việt
│   ├── tts.py                 # Engine Edge-TTS tiếng Việt
│   ├── voices.py              # Đa dạng giọng đọc (Nữ chuẩn, Nam thuyết minh, Cổ trang...)
│   ├── aligner.py             # Tự động co giãn thời gian (Time Alignment)
│   ├── builder.py             # Ghép trục thời gian chèn silence chuẩn từng mili-giây
│   └── cli.py                 # CLI độc lập: python3 -m srt_to_voice
│
├── video_dubber/              # MODULE 3: Hòa âm giọng đọc vào video gốc (-3dB nền)
│   ├── mixer.py               # FFmpeg audio mixing (-3dB âm thanh nền, giữ nguyên 100% video)
│   └── cli.py                 # CLI độc lập: python3 -m video_dubber
│
├── pipeline.py                # BỘ ĐIỀU PHỐI (Orchestrator kết nối tuần tự 3 module trên)
├── run.py                     # Script 1-Click tiện lợi: python3 run.py
├── sample/                    # Thư mục nạp video mẫu
├── output/                    # Thư mục xuất video hoàn chỉnh sau khi lồng tiếng
├── pyproject.toml             # Cấu hình gói Python cho cả 3 module
├── requirements.txt           # Danh sách thư viện cần thiết
├── Dockerfile & compose       # Đóng gói container Docker
└── README.md
```

---

## ⚡ 2. Chuẩn Bị Môi Trường (Chạy 1 lần đầu)

Kích hoạt môi trường ảo `venv`:

```bash
cd /home/tuanlala/.gemini/antigravity/scratch/mungngoc
source venv/bin/activate
```

*(Nếu cài trên máy mới: `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`)*

> [!NOTE]
> Đảm bảo **Ollama** đang chạy mô hình Qwen (`qwen2.5:3b-instruct` hoặc `qwen2.5:1.5b`) để bản dịch đạt chất lượng ngữ nghĩa mượt mà nhất. Nếu không có Ollama, hệ thống tự động fallback sang dịch máy.

---

## 🚀 3. Cách Chạy Trọn Gói Pipeline (End-to-End)

### Cách nhanh nhất (1-Click Run):
1. Ném file video cần xử lý vào thư mục `sample/`.
2. Chạy:
   ```bash
   python3 run.py
   ```
3. Lấy video lồng tiếng hoàn chỉnh trong thư mục `output/`.

### Chạy tùy biến qua `pipeline.py`:
```bash
# Đổi giọng Nam thuyết minh:
python3 pipeline.py ./sample -v nam_thuyet_minh

# Đổi giọng Nữ cổ trang cho 1 video cụ thể:
python3 pipeline.py ./sample/sample.mp4 -v nu_co_trang -o ./output/video_dubbed.mp4

# Điều chỉnh mức âm lượng nền (ví dụ giảm -6dB):
python3 pipeline.py ./sample --bg-volume -6dB

# Xem danh sách các giọng đọc có sẵn:
python3 pipeline.py --list-voices
```

---

## 🎙️ 4. Danh Sách Các Giọng Đọc Có Sẵn

| Mã giọng (`-v`) | Giới tính | Phong cách & Mô tả |
| :--- | :---: | :--- |
| **`nu_chuan`** | Nữ | Nữ miền Bắc chuẩn, tự nhiên, ấm áp *(Mặc định)* |
| **`nu_tre`** | Nữ | Nữ trẻ, trong trẻo, vui tươi |
| **`nu_tram`** | Nữ | Nữ trầm, chững chạc, giàu cảm xúc |
| **`nu_co_trang`** | Nữ | Nữ phong cách cổ trang, nhịp nhẹ nhàng |
| **`nam_thuyet_minh`**| Nam | Nam thuyết minh phim, trầm ấm, chuẩn giọng VTV |
| **`nam_chuan`** | Nam | Nam miền Bắc chuẩn, rõ ràng, dứt khoát |
| **`nam_tre`** | Nam | Nam trẻ, thanh niên, hiện đại |
| **`nam_co_trang`** | Nam | Nam phong cách kiếm hiệp, kể chuyện, trầm tĩnh |

---

## 🔧 5. Cách Sử Dụng Độc Lập Từng Module

Mỗi module được thiết kế hoàn toàn độc lập, có thể gọi riêng lẻ:

### 🔹 Module 1: Chỉ bóc tách tiếng Trung & dịch ra `.srt`
```bash
python3 -m extract_srt_from_video ./sample -m all
```
*Kết quả xuất ra tại `sample/srt/`: `sample.zh.srt` (tiếng Trung), `sample.vi.srt` (tiếng Việt dịch bằng Qwen), `sample.srt` (song ngữ).*

### 🔹 Module 2: Chỉ tạo file audio lồng tiếng từ file `.srt`
```bash
python3 -m srt_to_voice ./sample/srt/sample.vi.srt -v nam_thuyet_minh
```
*Kết quả xuất ra file `.mp3` khớp 100% trục thời gian của phụ đề (có silence padding).*

### 🔹 Module 3: Chỉ hòa âm file voice vào video gốc
```bash
python3 -m video_dubber \
  --video sample/sample.mp4 \
  --voice sample/srt/sample_voice_nu_chuan.mp3 \
  -o output/sample_dubbed.mp4 \
  --bg-volume -3dB
```

---

## 🐳 6. Chạy Bằng Docker
```bash
docker compose up --build
```
Video sau khi lồng tiếng sẽ tự động xuất ra thư mục `output/`.
