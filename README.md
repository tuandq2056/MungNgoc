# 🎬 Extract SRT from Video (extract_srt_from_video)

> **Module bóc tách và dịch phụ đề video tiếng Trung sang file `.srt` chuẩn ngữ nghĩa.**  
> Kết hợp công nghệ nhận diện giọng nói **SenseVoice-Small** (Alibaba), phân đoạn câu **Silero-VAD** và dịch thuật ngữ nghĩa mượt mà bằng **Qwen LLM**.

---

## ✨ Điểm nổi bật

1. **Nhận diện tiếng Trung cực chuẩn**: Sử dụng **SenseVoice-Small** qua runtime ONNX tối ưu, tốc độ giải mã siêu thanh (~70ms cho 10s audio) mà không cần cài đặt PyTorch/CUDA cồng kềnh.
2. **Mốc thời gian (Timestamps) khớp từng mili-giây**: Sử dụng **Silero-VAD** để loại bỏ hoàn toàn các đoạn im lặng/nhạc nền, chỉ bắt đúng đoạn có lời thoại.
3. **Dịch chuẩn ngữ nghĩa bằng Qwen**: Tự động kết nối với mô hình **Qwen** (qua Ollama) với System Prompt chuyên sâu về phụ đề phim ảnh, giải quyết triệt để lỗi dịch máy thô cứng.
4. **Hỗ trợ 4 chế độ phụ đề**:
   - `bilingual`: Phụ đề song ngữ (Dòng 1: Tiếng Trung, Dòng 2: Tiếng Việt).
   - `zh`: Chỉ xuất phụ đề tiếng Trung gốc.
   - `vi`: Chỉ xuất phụ đề tiếng Việt.
   - `all`: Xuất cùng lúc cả 3 file phụ đề (`.srt`, `.zh.srt`, `.vi.srt`).
5. **Đóng gói chuẩn chỉnh**: Sẵn sàng chạy bằng virtual environment (`venv`), cài đặt thư viện (`pip`), hoặc đóng gói bằng **Docker / Docker Compose** để đẩy lên GitHub.

---

## 🚀 Cài đặt & Sử dụng

### Cách 1: Sử dụng Virtual Environment (Khuyên dùng)

1. **Khởi tạo và kích hoạt môi trường ảo:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Cài đặt các gói phụ thuộc:**
   ```bash
   pip install -r requirements.txt
   # Hoặc cài đặt module ở chế độ editable:
   pip install -e .
   ```

3. **Chạy xử lý video:**
   ```bash
   # Xử lý tất cả video trong thư mục sample/
   python3 -m extract_srt_from_video ./sample -m all

   # Hoặc sử dụng lệnh CLI sau khi install -e .:
   extract-srt ./sample/sample.mp4 -m bilingual
   ```

---

### Cách 2: Chạy nhanh qua script `run.py`

```bash
source venv/bin/activate
python3 run.py
```
File phụ đề sẽ được tự động lưu vào thư mục `sample/srt/`.

---

### Cách 3: Chạy bằng Docker & Docker Compose

Nếu không muốn cài đặt bất kỳ thư viện Python nào lên máy chủ/máy cá nhân:

```bash
# Build và chạy với Docker Compose
docker compose up --build
```
Container sẽ tự động kết nối với Ollama chạy trên máy host để dịch phụ đề.

---

## 🛠️ Cấu hình mô hình dịch (Qwen / Fallback)

Module tự động kiểm tra xem máy có đang chạy **Ollama** với mô hình Qwen hay không (mặc định tại `http://localhost:11434` với model `qwen2.5:3b-instruct` hoặc `qwen2.5:1.5b`).

- **Nếu có Ollama & Qwen**: Tự động dùng Qwen để dịch nghĩa mượt mà, đúng văn phong phim cổ trang / hiện đại.
- **Nếu không có Ollama**: Tự động fallback sang Google / MyMemory Translate hoặc xuất phụ đề tiếng Trung gốc mà không làm crash chương trình.

---

## 📂 Cấu trúc Repository

```text
├── extract_srt_from_video/    # Mã nguồn chính của module
│   ├── __init__.py            # Export các hàm: extract_srt, process_video, process_folder
│   ├── config.py              # Cấu hình đường dẫn, URL mô hình
│   ├── models.py              # Tự động tải SenseVoice & Silero-VAD ONNX
│   ├── audio.py               # Trích xuất âm thanh qua ffmpeg stream
│   ├── vad.py                 # Silero-VAD cắt đoạn thoại
│   ├── asr.py                 # SenseVoice nhận diện tiếng Trung
│   ├── translator.py          # Qwen LLM translator + Fallback
│   ├── srt.py                 # Xuất file .srt chuẩn
│   ├── pipeline.py            # Quy trình xử lý tự động
│   └── cli.py                 # Giao diện dòng lệnh
├── sample/                    # Thư mục chứa video mẫu
│   ├── sample.mp4
│   └── srt/                   # Kết quả phụ đề xuất ra
├── Dockerfile                 # Đóng gói Docker
├── docker-compose.yml         # Chạy container nhanh
├── pyproject.toml             # Chuẩn cấu hình build package Python
├── requirements.txt           # Danh sách thư viện cần thiết
├── .gitignore                 # Loại trừ file rác, cache, venv
├── run.py                     # Script chạy test nhanh
└── README.md                  # Hướng dẫn sử dụng
```

---

## 📜 Giấy phép
Mã nguồn phát hành theo giấy phép MIT.
