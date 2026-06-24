# AI School — Hệ thống nhận diện khuôn mặt & Quản lý vi phạm học sinh

Dự án nghiên cứu khoa học kỹ thuật lớp 11A1.  
Ứng dụng AI nhận diện khuôn mặt và biển số xe để quản lý vi phạm nội quy học sinh THPT.

---

## Công nghệ sử dụng

| Thành phần | Công nghệ |
|---|---|
| Backend API | FastAPI + Uvicorn |
| Cơ sở dữ liệu | SQLite + SQLAlchemy |
| Nhận diện khuôn mặt | InsightFace (buffalo_l) + FAISS |
| Nhận diện biển số xe | EasyOCR |
| Xác thực | JWT + bcrypt |
| Chatbot AI | Groq API (llama-3.3-70b) |
| Frontend | HTML / CSS / JavaScript thuần |

---

## Yêu cầu hệ thống

- Python 3.10 trở lên
- pip (trình quản lý gói Python)
- Webcam (để nhận diện khuôn mặt trực tiếp)
- Kết nối internet (để tải model InsightFace lần đầu và dùng Groq API)

---

## Cài đặt

### Bước 1 — Cài đặt thư viện Python

```bash
pip install -r requirements.txt
```

### Bước 2 — Cấu hình file môi trường

Sao chép file mẫu và điền thông tin thực:

```bash
cp .env.example .env
```

Mở file `.env` và điền:

```
JWT_SECRET_KEY=your_secret_key_here          # Đặt chuỗi bí mật bất kỳ, tối thiểu 32 ký tự
GROQ_API_KEY=your_groq_api_key_here          # Lấy miễn phí tại https://console.groq.com
CTX_ID=-1                                    # -1 = CPU, 0 = GPU (nếu có NVIDIA GPU)
```

### Bước 3 — Chuẩn bị ảnh khuôn mặt học sinh

Tạo cấu trúc thư mục `resources/known_faces/` như sau:

```
resources/
└── known_faces/
    └── 11A1/
        ├── Nguyen_Van_A/
        │   ├── 1.jpg
        │   ├── 2.jpg
        │   └── 3.jpg
        └── Tran_Thi_B/
            ├── 1.jpg
            └── 2.jpg
```

> Mỗi học sinh cần ít nhất 3–5 ảnh chụp từ các góc độ khác nhau để đạt độ chính xác cao.  
> Face label trong hệ thống sẽ là `Nguyen_Van_A_11A1` (tên_lớp).

### Bước 4 — Tạo tài khoản admin lần đầu

```bash
python create_admin.py --username admin --password your_password
```

Tạo thêm tài khoản giáo viên (nếu cần):

```bash
python create_admin.py --username teacher1 --password your_password --role teacher
```

### Bước 5 — Khởi động server

```bash
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Bước 6 — Mở giao diện

Dùng VS Code với extension **Live Server**, mở file `frontend/index.html`.  
Hoặc dùng bất kỳ web server tĩnh nào (cổng 5500 hoặc 5501).

---

## Phân quyền người dùng

| Vai trò | Trang truy cập được |
|---|---|
| `admin` | Tất cả trang |
| `teacher` | Dashboard, Nhận diện, Học sinh, Chatbot |
| `security` | Chỉ trang Quét (scan.html) |

---

## Cấu trúc thư mục

```
├── backend/
│   ├── main.py           # API FastAPI chính
│   ├── auth.py           # JWT + bcrypt
│   ├── database/
│   │   ├── db.py         # Kết nối SQLite
│   │   └── models.py     # ORM models
│   └── schemas/
│       └── student.py    # Pydantic schemas
├── core/
│   ├── AdvancedFaceRecognitionSystem.py  # Pipeline nhận diện
│   ├── FaceDatabase.py   # Lưu trữ embeddings
│   └── FaissIndex.py     # Tìm kiếm vector nhanh
├── frontend/
│   ├── index.html        # Trang nhận diện chính
│   ├── dashboard.html    # Thống kê vi phạm
│   ├── students.html     # Quản lý học sinh
│   ├── scan.html         # Quét nhanh (mobile)
│   ├── chatbot.html      # Chatbot AI
│   └── login.html        # Đăng nhập
├── resources/
│   └── known_faces/      # Ảnh học sinh (không nộp kèm)
├── create_admin.py       # Script tạo tài khoản
├── requirements.txt
└── .env.example
```

---

## Lưu ý khi chạy lần đầu

- Lần đầu khởi động, InsightFace sẽ tự tải model `buffalo_l` (~200MB). Cần internet.
- File `face_database.pkl` và `school.db` sẽ tự được tạo khi chạy server.
- Không commit file `.env`, `*.pkl`, `*.db`, và thư mục `resources/` lên git.