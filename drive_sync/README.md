# drive_sync – contract giữa máy nhà và Colab

Hai bên **chỉ trao đổi file** qua một thư mục Google Drive (mặc định `gdrive:MungNgoc`, đổi bằng biến `DRIVE_REMOTE`).
Bên nào ghi thì bên đó sở hữu; không bên nào sửa file của bên kia.

```
MungNgoc/
├── code/
│   ├── qwen_translate/        ← máy nhà đẩy (python3 -m drive_sync push-code)
│   └── glossary.txt
├── inbox/
│   └── tapN.srt               ← máy nhà ghi: phụ đề tiếng Trung (đầu ra extractor -m zh)
├── outbox/
│   ├── tapN.vi.srt            ← Colab ghi: bản dịch tiếng Việt
│   └── tapN.fail.txt          ← Colab ghi nếu dịch lỗi (nội dung = lý do)
└── status/
    └── worker.json            ← Colab cập nhật ~mỗi 20s: {"time": epoch, "model": ..., "busy": "tapN"|null}
```

Quy tắc:
- `tapN.vi.srt` có **cùng số cue và cùng dòng thời gian** với `inbox/tapN.srt`; câu không dịch được thì để trống.
- Colab ghi vào `tapN.vi.srt.tmp` rồi đổi tên; máy nhà bỏ qua mọi file `.tmp`/`.part`.
- Colab bỏ qua tập đã có `.vi.srt` hoặc `.fail.txt` trong outbox. Muốn dịch lại: `python3 -m drive_sync push <file> --retranslate`.
- Hai bên đều có thể dừng giữa chừng rồi chạy lại; toàn bộ trạng thái nằm trong các file trên.

## Thiết lập một lần (máy nhà)

```bash
sudo dnf install rclone
rclone config            # n) New remote → tên: gdrive → Storage: drive → làm theo hướng dẫn đăng nhập
python3 -m drive_sync push-code
```
