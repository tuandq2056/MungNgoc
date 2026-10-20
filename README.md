# 🎬 Video Subtitle & Voice Dubbing Toolkit

> Bộ công cụ bóc tách phụ đề tiếng Trung, dịch thuật ngữ nghĩa bằng **Qwen LLM** và tạo giọng đọc lồng tiếng tiếng Việt đa dạng khớp chuẩn mốc thời gian.

---

## 📦 Các Module trong dự án

Dự án gồm 2 module độc lập nhưng phối hợp hoàn hảo với nhau:

1. **`extract_srt_from_video`**:
   - Trích xuất âm thanh từ video bằng `ffmpeg`.
   - Phân đoạn giọng nói chuẩn xác bằng **Silero-VAD**.
   - Nhận diện lời thoại tiếng Trung siêu nhanh bằng **SenseVoice-Small** (ONNX).
   - Dịch thuật ngữ nghĩa mượt mà, đúng văn phong phim bằng **Qwen 2.5** (Ollama).
   - Xuất file phụ đề `.srt` (song ngữ, tiếng Trung, tiếng Việt).

2. **`srt_to_voice`**:
   - Nhận file phụ đề `.srt` tiếng Việt (hoặc file song ngữ).
   - Tự động sinh giọng đọc tiếng Việt bằng **Edge-TTS Neural Voice**.
   - Hỗ trợ **nhiều preset giọng đọc phong phú**: Nữ chuẩn, Nữ trẻ, Nữ cổ trang, Nam thuyết minh, Nam kiếm hiệp...
   - **Tự động co giãn nhịp đọc (Time Alignment)**: Nếu câu đọc dài hơn thời lượng sub, tự động tăng tốc nhẹ (`atempo`) để không đè vào câu tiếp theo.
   - **Tạo trục âm thanh đồng bộ (Silence Padding)**: Chèn khoảng lặng chuẩn từng mili-giây, tạo ra 1 file âm thanh hoàn chỉnh để kéo thẳng vào Premiere, CapCut hoặc mux vào video.

---

## 🎙️ Danh Sách Các Giọng Đọc Có Sẵn (`srt_to_voice`)

Kiểm tra danh sách giọng bất cứ lúc nào bằng lệnh:
```bash
python3 -m srt_to_voice --list-voices
```

| Mã giọng (`-v`) | Giới tính | Phong cách & Mô tả |
| :--- | :---: | :--- |
| **`nu_chuan`** | Nữ | Nữ miền Bắc chuẩn, tự nhiên, ấm áp (Mặc định) |
| **`nu_tre`** | Nữ | Nữ trẻ, trong trẻo, vui tươi |
| **`nu_tram`** | Nữ | Nữ trầm, chững chạc, giàu cảm xúc |
| **`nu_co_trang`** | Nữ | Nữ phong cách cổ trang, truyền cảm, nhịp nhẹ nhàng |
| **`nam_thuyet_minh`**| Nam | Nam thuyết minh phim, trầm ấm, chuẩn phong cách VTV |
| **`nam_chuan`** | Nam | Nam miền Bắc chuẩn, rõ ràng, dứt khoát |
| **`nam_tre`** | Nam | Nam trẻ, thanh niên, hiện đại |
| **`nam_co_trang`** | Nam | Nam phong cách kiếm hiệp, kể chuyện, trầm tĩnh |

---

## 🚀 Cài Đặt & Sử Dụng

### 1. Kích hoạt Virtual Environment (`venv`):
```bash
cd /home/tuanlala/.gemini/antigravity/scratch/mungngoc
source venv/bin/activate
```

### 2. Bóc tách phụ đề từ video:
```bash
# Xử lý tất cả video trong thư mục sample/
python3 -m extract_srt_from_video ./sample -m all
```
Kết quả `.srt` được lưu vào `./sample/srt/`.

### 3. Tạo file âm thanh lồng tiếng từ file `.srt`:
```bash
# Tạo giọng Nữ chuẩn
python3 -m srt_to_voice ./sample/srt/sample.vi.srt -v nu_chuan

# Tạo giọng Nam thuyết minh phim
python3 -m srt_to_voice ./sample/srt/sample.vi.srt -v nam_thuyet_minh -o ./sample/srt/voice_nam.mp3

# Tùy chọn lưu cả các file âm thanh lẻ của từng câu:
python3 -m srt_to_voice ./sample/srt/sample.vi.srt -v nu_tre --save-segments
```

### 4. Chạy nhanh toàn bộ quy trình:
```bash
python3 run.py
```

---

## 🐳 Chạy bằng Docker
```bash
docker compose up --build
```

---

## 📜 Giấy phép
Mã nguồn phát hành theo giấy phép MIT.
