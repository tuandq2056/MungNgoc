# 🎬 Hướng Dẫn Chạy Pipeline Lồng Tiếng Video (Auto Dubbing)

> **Quy trình tự động hóa khép kín**: Nạp video tiếng Trung vào thư mục `sample/` $\rightarrow$ Nhận video lồng tiếng tiếng Việt hoàn chỉnh tại `output/`.

---

## ⚡ 1. Chuẩn Bị Môi Trường (Chạy 1 lần đầu)

Mở terminal tại thư mục dự án và kích hoạt môi trường ảo:

```bash
cd /home/tuanlala/.gemini/antigravity/scratch/mungngoc
source venv/bin/activate
```

*(Nếu cài trên máy mới hoàn toàn, chỉ cần chạy: `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`)*

> [!NOTE]
> Để bản dịch đạt chất lượng ngữ nghĩa mượt mà như phim, đảm bảo **Ollama** đang chạy mô hình Qwen (`qwen2.5:3b-instruct` hoặc `qwen2.5:1.5b`). Nếu không có Ollama, hệ thống tự động chuyển sang dịch máy dự phòng.

---

## 🚀 2. Cách Chạy Nhanh Nhất (1-Click Run)

1. Copy file video của bạn (định dạng `.mp4`, `.mkv`, `.mov`...) bỏ vào thư mục `sample/`.
2. Chạy lệnh:
   ```bash
   python3 run.py
   ```
3. Lấy video đã được lồng tiếng hoàn chỉnh trong thư mục `output/` (ví dụ: `output/sample_dubbed.mp4`).

---

## 🎛️ 3. Cách Chạy Tùy Biến Nâng Cao (`auto_dub.py`)

Chạy lệnh `auto_dub.py` để tùy chọn giọng đọc, mức âm lượng nền hoặc đường dẫn file:

```bash
# 1. Chạy tất cả video trong sample/ với giọng Nam thuyết minh:
python3 auto_dub.py ./sample -v nam_thuyet_minh

# 2. Chạy 1 file video cụ thể với giọng Nữ cổ trang:
python3 auto_dub.py ./sample/sample.mp4 -v nu_co_trang -o ./output/video_co_trang.mp4

# 3. Điều chỉnh âm lượng nền gốc giảm sâu hơn (ví dụ giảm -6dB thay vì -3dB):
python3 auto_dub.py ./sample/sample.mp4 --bg-volume -6dB

# 4. Xem danh sách toàn bộ các giọng đọc có sẵn:
python3 auto_dub.py --list-voices
```

---

## 🎙️ 4. Bảng Các Giọng Đọc Có Sẵn

Chọn giọng bằng tham số `-v <mã_giọng>`:

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

## 🔧 5. Cách Chạy Từng Bước Riêng Lẻ (Nếu cần)

Nếu không muốn chạy trọn gói mà chỉ muốn chạy riêng lẻ từng khâu:

### Bước 1: Chỉ bóc tách âm thanh & dịch phụ đề (.srt)
```bash
python3 -m extract_srt_from_video ./sample -m all
```
*Kết quả xuất ra tại `sample/srt/`: file `.zh.srt` (tiếng Trung), `.vi.srt` (tiếng Việt), `.srt` (song ngữ).*

### Bước 2: Chỉ tạo file âm thanh lồng tiếng từ file .srt
```bash
python3 -m srt_to_voice ./sample/srt/sample.vi.srt -v nam_thuyet_minh
```
*Kết quả xuất ra tại `sample/srt/sample_voice_nam_thuyet_minh.mp3` (khớp 100% trục thời gian).*

### Bước 3: Chỉ lồng tiếng file .mp3 vào video gốc
```bash
python3 dub_video.py \
  --video sample/sample.mp4 \
  --voice sample/srt/sample_voice_nu_chuan.mp3 \
  -o output/sample_dubbed.mp4 \
  --bg-volume -3dB
```

---

## 🐳 6. Cách Chạy Bằng Docker

Không cần cài đặt thư viện vào máy, chỉ cần chạy:

```bash
docker compose up --build
```
Video sau khi lồng tiếng sẽ tự động xuất ra thư mục `output/` trên máy của bạn.
