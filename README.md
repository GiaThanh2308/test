---
title: KHKT Face Recognition
emoji: 🎓
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# KHKT — AI School (nhận diện khuôn mặt)
Dự án của lớp 11A1: nhận diện khuôn mặt học sinh, ghi nhận vi phạm, thống kê và chatbot hỏi đáp.

## Chạy trên máy
```bash
pip install -r requirements.txt
copy .env.example .env          # rồi điền JWT_SECRET_KEY (và GROQ_API_KEY nếu dùng chatbot)
python create_admin.py --username admin --role admin
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
Mở http://127.0.0.1:8000 (server phục vụ luôn giao diện).

## Dữ liệu khuôn mặt
Đặt ảnh theo cấu trúc `resources/known_faces/<khối>/<lớp>/<Họ tên>/*.jpg`
(ví dụ `khoi 10/10A1/Nguyen Van A/1.jpg`). Khi server khởi động, hồ sơ học sinh được tạo tự động.
Thêm học sinh mới khi server đang chạy: trang **Học sinh → Đồng bộ lại** (vừa học khuôn mặt mới vừa tạo hồ sơ).

## Tài khoản
| Vai trò | Quyền |
|---|---|
| `admin`, `teacher` | Tất cả trang |
| `student` | Chỉ trang Nhận diện (xem họ tên + lớp), không ghi vi phạm |

Tạo tài khoản: `python create_admin.py --username hs01 --password MatKhau123 --role student`

## Chế độ camera trên máy tính (tuỳ chọn)
`python main.py` — mở cửa sổ OpenCV để thử nhận diện nhanh, không cần server.
