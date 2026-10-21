# AI School — Hệ thống ghi nhận vi phạm bằng nhận diện khuôn mặt

Hệ thống hỗ trợ đội **Cờ đỏ** ở cổng trường: quét khuôn mặt học sinh, chọn lỗi vi phạm và lưu lại. Giáo viên theo dõi thống kê, xem lại ảnh chụp và **xuất Excel** để ghi sổ thi đua.

Chạy hoàn toàn trên máy của nhà trường (local), có thể công khai ra internet qua **Cloudflare Tunnel**.

---

## Mục lục
1. [Tính năng](#1-tính-năng)
2. [Vai trò và phân quyền](#2-vai-trò-và-phân-quyền)
3. [Công nghệ](#3-công-nghệ)
4. [Cấu trúc thư mục](#4-cấu-trúc-thư-mục)
5. [Cài đặt](#5-cài-đặt)
6. [Cấu hình `.env`](#6-cấu-hình-env)
7. [Dữ liệu khuôn mặt](#7-dữ-liệu-khuôn-mặt)
8. [Tài khoản](#8-tài-khoản)
9. [Hướng dẫn sử dụng](#9-hướng-dẫn-sử-dụng)
10. [Xuất Excel](#10-xuất-excel)
11. [Ảnh chụp tự động](#11-ảnh-chụp-tự-động)
12. [Vận hành thực tế](#12-vận-hành-thực-tế)
13. [Sao lưu và khôi phục](#13-sao-lưu-và-khôi-phục)
14. [Tài liệu API](#14-tài-liệu-api)
15. [Xử lý sự cố](#15-xử-lý-sự-cố)
16. [Giới hạn đã biết](#16-giới-hạn-đã-biết)

---

## 1. Tính năng

| Nhóm | Mô tả |
|---|---|
| **Nhận diện** | InsightFace (`buffalo_l`) + FAISS. Lưu toàn bộ embedding gốc của từng người, ngưỡng cosine 0,5. |
| **Ghi vi phạm** | Quét xong cờ đỏ chọn **một hoặc nhiều** lỗi có sẵn rồi lưu. Mỗi lỗi là một bản ghi riêng, kèm ca trực đã ghi. |
| **Chống ghi trùng** | Cùng học sinh + cùng lỗi trong `DUPLICATE_WINDOW_MIN` phút (mặc định 5) sẽ bị bỏ qua. |
| **Ảnh chụp** | Mỗi lần quét thấy mặt, server tự lưu ảnh đóng dấu ngày giờ, tên, lớp, ca trực vào `data/capture/`. |
| **Dashboard** | Tổng lượt, hôm nay/tuần/tháng, biểu đồ 7 ngày, phân bố loại lỗi, top vi phạm tháng này, hoạt động gần đây. |
| **Xuất Excel** | Theo khoảng ngày, đúng kiểu sổ thi đua (sheet chi tiết + sheet nhập vi phạm có mã lỗi, số lần, điểm trừ). |
| **Quản lý học sinh** | Thêm/sửa/xoá, mã học sinh tự cấp, đồng bộ từ thư mục ảnh. |
| **Chatbot** | Tra cứu theo mã/tên đi thẳng vào cơ sở dữ liệu (không qua AI nên không bịa); câu hỏi chung dùng Groq. |
| **Tải cao** | Hàng đợi nhận diện (`INFER_WORKERS`): nhiều cờ đỏ quét cùng lúc sẽ xếp hàng thay vì làm treo máy. |
| **Dữ liệu an toàn** | SQLite chế độ WAL, script sao lưu có kiểm tra toàn vẹn, ghi file khuôn mặt qua file tạm. |

---

## 2. Vai trò và phân quyền

| Chức năng | `admin` | `teacher` | `student` (cờ đỏ) |
|---|:-:|:-:|:-:|
| Quét nhận diện | ✅ | ✅ | ✅ |
| Xem họ tên, lớp, ảnh, độ khớp | ✅ | ✅ | ✅ |
| Xem mã HS, SĐT, nhãn khuôn mặt | ✅ | ✅ | ❌ |
| **Thêm** vi phạm | ✅ | ✅ | ✅ |
| Xem danh sách vi phạm, Dashboard | ✅ | ✅ | ❌ |
| Xuất Excel, xem ảnh chụp | ✅ | ✅ | ❌ |
| Quản lý học sinh, chatbot | ✅ | ✅ | ❌ |
| Tạo tài khoản, Chuyển năm học | ✅ | ❌ | ❌ |
| Nhập danh sách Excel (sửa tên có dấu) | ✅ | ✅ | ❌ |

Nguyên tắc: **cờ đỏ chỉ được thêm, không được xem lại, sửa hay xoá số liệu.** Quyền được kiểm tra ở cả server lẫn giao diện.

**Tài khoản cờ đỏ chia theo ca** (ví dụ `ca1`, `ca2`...). Tên tài khoản được lưu vào mỗi bản ghi (`recorded_by`) và đóng dấu lên ảnh chụp, để khi có khiếu nại còn biết ca nào ghi.

---

## 3. Công nghệ

- **Backend:** Python 3.10+, FastAPI, SQLAlchemy, SQLite (WAL), JWT (python-jose) + bcrypt
- **AI:** InsightFace `buffalo_l` (ONNX, CPU), FAISS, OpenCV
- **Xuất file / ảnh:** openpyxl, Pillow
- **Frontend:** HTML/CSS/JavaScript thuần, Chart.js, Font Awesome
- **Chatbot:** Groq API (tuỳ chọn)
- **Triển khai:** `uvicorn` chạy trực tiếp trên Windows, Cloudflare Tunnel (`cloudflared`)

---

## 4. Cấu trúc thư mục

```
khkt/
├── backend/
│   ├── main.py                 # API + phục vụ giao diện (SERVER THẬT)
│   ├── auth.py                 # JWT, mật khẩu, kiểm tra quyền
│   ├── face_folders.py         # đọc known_faces, tự cấp mã học sinh
│   ├── violation_types.py      # DANH SÁCH LỖI + mã lỗi sổ thi đua
│   ├── excel_export.py         # dựng file Excel
│   ├── captures.py             # lưu ảnh chụp có đóng dấu ngày giờ
│   ├── database/               # db.py (kết nối, migration), models.py
│   └── schemas/                # schema request
├── core/                       # AdvancedFaceRecognitionSystem, FaceDatabase, FaissIndex
├── frontend/                   # index, dashboard, students, chatbot, login + js/css
├── resources/
│   ├── face_database.npz       # embedding khuôn mặt (NumPy, không dùng pickle)
│   └── known_faces/<khối>/<lớp>/<Họ tên>/*.jpg
├── data/                       # TỰ TẠO — dữ liệu chạy thật, KHÔNG nằm trong Git
│   ├── school.db
│   ├── capture/<yyyy-mm-dd>/*.jpg
│   └── backups/
├── tools/backup_db.py          # sao lưu cơ sở dữ liệu
├── create_admin.py             # tạo/đổi mật khẩu tài khoản
├── run_local_cv.py             # thử nhanh bằng camera OpenCV, KHÔNG phải server (trước đây là main.py)
├── requirements.txt
└── .env.example
```

> Thêm `data/` và `.env` vào `.gitignore`. Dữ liệu thật của học sinh không được đưa lên Git.

---

## 5. Cài đặt

### Yêu cầu
- Windows 10/11 (hoặc Linux), **Python 3.10 trở lên**
- Webcam hoặc điện thoại có camera (trình duyệt cần **HTTPS** hoặc `localhost` mới cho bật camera)
- Khi cài `insightface` trên Windows có thể cần **Microsoft C++ Build Tools**

### Các bước (Windows)
```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env
rem Mở .env, điền JWT_SECRET_KEY (chuỗi bí mật dài, ngẫu nhiên) và GROQ_API_KEY nếu dùng chatbot

python create_admin.py --username admin --role admin
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Mở trình duyệt: **http://127.0.0.1:8000** (server phục vụ luôn giao diện).

Lần đầu khởi động, model `buffalo_l` được tải về (vài trăm MB), nên cần có mạng.

### Nâng cấp từ bản cũ
1. Chạy `python tools/backup_db.py` (hoặc chép tay `school.db`) trước khi cập nhật.
2. Chép đè mã nguồn mới.
3. Khởi động lại. Server tự: chép DB cũ từ `backend/database/school.db` sang `data/school.db` (file cũ được giữ nguyên) và thêm cột mới `recorded_by`, `capture_path` vào bảng `violations`. Không mất dữ liệu.

---

## 6. Cấu hình `.env`

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `JWT_SECRET_KEY` | *(bắt buộc)* | Khoá ký đăng nhập. Server không chạy nếu để trống. |
| `GROQ_API_KEY` | | Khoá Groq cho chatbot. Trống thì chatbot AI báo lỗi (API `/chatbot/lookup` tra cứu theo mã/tên không cần khoá này). |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Mô hình Groq. |
| `ALLOWED_ORIGINS` | localhost:5500/5501 | Chỉ cần khi mở giao diện ở origin khác (Live Server). |
| `RESOURCE_DIR` | `resources` | Thư mục chứa dữ liệu khuôn mặt. |
| `FACE_DATABASE_PATH` | `resources/face_database.npz` | File embedding. Nếu `.env` cũ còn trỏ tới `.pkl`, hệ thống tự chuyển sang `.npz` cùng tên (một lần, giữ file cũ). |
| `KNOWN_FACES_DIR` | `resources/known_faces` | Thư mục ảnh học sinh. |
| `DATA_DIR` | `data` | Thư mục dữ liệu chạy thật. |
| `DB_PATH` | `data/school.db` | File cơ sở dữ liệu. |
| `CAPTURE_DIR` | `data/capture` | Nơi lưu ảnh chụp tự động. |
| `CAPTURE_FONT` | *(tự tìm)* | Font `.ttf` có tiếng Việt để đóng dấu ảnh. Windows tự dùng Arial. |
| `BACKUP_DIR` | `data/backups` | Nơi lưu bản sao lưu. Nên đặt sang ổ khác. |
| `BACKUP_KEEP` | `14` | Số bản sao lưu giữ lại. |
| `SCHOOL_WEEK1_START` | `2026-09-07` | Ngày bắt đầu **tuần 1** (thứ Hai) để đánh số TUẦN trong Excel. **Hãy sửa theo lịch trường.** |
| `TZ_OFFSET_HOURS` | `7` | Múi giờ cho thống kê "hôm nay/tuần/tháng". |
| `AUTO_SYNC_STUDENTS` | `1` | `1` = tự tạo hồ sơ học sinh từ `known_faces` khi khởi động. |
| `INFER_WORKERS` | tự chọn | Số lượt nhận diện chạy song song. Bỏ trống: 50 nếu có GPU, 2 nếu chỉ CPU. |
| `CAPTURE_KEEP_DAYS` | `60` | Tự xoá ảnh chụp cũ hơn số ngày này (chạy ngầm mỗi 24 giờ). `0` = không xoá. |
| `DUPLICATE_WINDOW_MIN` | `5` | Chặn ghi trùng (cùng học sinh + cùng lỗi) trong số phút này. |
| `ADMIN_PASSWORD` | | Mật khẩu mặc định cho `create_admin.py` (bỏ trống thì script hỏi). |

---

## 7. Dữ liệu khuôn mặt

Đặt ảnh theo cấu trúc:

```
resources/known_faces/
└── khoi 10/
    └── 10B3/
        └── Nguyen Van A/
            ├── 1.jpg
            └── 2.jpg
```

- Nhãn khuôn mặt là `Họ tên_Lớp` (ví dụ `Nguyen Van A_10B3`).
- Mỗi người nên có **3–5 ảnh** rõ mặt, nhiều góc và ánh sáng khác nhau.
- **Mã học sinh tự cấp** theo dạng `HS` + khối + lớp + số thứ tự (xếp theo tên A→Z trong lớp). Ví dụ `HS100301`.
- Học sinh mới khi server đang chạy: vào trang **Học sinh → Đồng bộ lại** (vừa học khuôn mặt mới vừa tạo hồ sơ).
- Tên lớp trong thư mục nên **trùng với danh mục lớp của sổ thi đua** (ví dụ `10B3`) để Excel khớp.

### Tên có dấu: nhập danh sách lớp từ Excel
Tên hiển thị ban đầu lấy từ tên thư mục ảnh nên không có dấu. Để sửa: trang **Học sinh → Nhập danh sách Excel**.
- File `.xlsx` cần dòng tiêu đề **Họ và tên** (hoặc **Họ đệm** + **Tên**) và cột **Lớp** (hoặc mỗi lớp một sheet, tên sheet là tên lớp). **Không cần mã học sinh.**
- Hệ thống ghép theo *tên bỏ dấu + lớp*, chỉ sửa tên hiển thị; **mã HS và nhãn khuôn mặt giữ nguyên**.
- Luôn có bước **Xem trước**. Trường hợp hai em trùng tên không dấu trong cùng lớp sẽ được báo để sửa tay, không tự đoán.
- Khi xáo lớp, tick "Cho phép đổi lớp" để cập nhật lớp theo danh sách (chỉ áp dụng khi tên đó là duy nhất trong trường).

### Chuyển năm học (admin, mỗi năm một lần)
Trang **Học sinh → Chuyển năm học** (chỉ admin thấy nút):
1. Xem trước: lớp 10→11, 11→12 (giữ nguyên chữ và số lớp, ví dụ `10B3` thành `11B3`), lớp 12 ra trường.
2. Gõ đúng năm học mới (ví dụ `2027-2028`) để xác nhận.
3. Hệ thống tự sao lưu DB vào `data/backups/before_rollover_*.db`, rồi đổi lớp trong một giao dịch. Không thể chạy lại cho cùng năm học.

Học sinh ra trường được **ẩn** khỏi nhận diện, danh sách, chatbot và thống kê; **lịch sử vi phạm vẫn giữ** và vẫn xuất được qua Excel. Mã HS giữ nguyên khi lên lớp.
Sau khi chuyển: thêm ảnh khối 10 mới vào `known_faces` rồi bấm **Đồng bộ lại**. Nếu khối mới có học sinh trùng tên không dấu **và** trùng tên lớp với học sinh cũ (ví dụ `Nguyen Van A` ở `10B3`), nhãn khuôn mặt sẽ trùng; hãy đặt tên thư mục khác đi (ví dụ `Nguyen Van A 2`).

---

## 8. Tài khoản

```bat
rem Quản trị
python create_admin.py --username admin --role admin

rem Giáo viên
python create_admin.py --username gv_an --password MatKhau123 --role teacher

rem Cờ đỏ theo ca
python create_admin.py --username ca1 --password MatKhau123 --role student
python create_admin.py --username ca2 --password MatKhau123 --role student
```

- Chạy lại với cùng `--username` sẽ **đổi mật khẩu và vai trò**.
- Admin cũng có thể tạo tài khoản qua API `POST /create-user`.
- Mật khẩu tối thiểu 6 ký tự; đăng nhập có hiệu lực 8 giờ.

---

## 9. Hướng dẫn sử dụng

### Cờ đỏ ở cổng (tài khoản `student`)
1. Đăng nhập, vào trang **Nhận diện**, bấm **Bật camera**.
2. Đưa mặt học sinh vào khung, bấm nút chụp. Hệ thống quét và hiện họ tên, lớp, ảnh, độ khớp.
3. **Chọn một hoặc nhiều lỗi** (bấm lại để bỏ chọn), có thể thêm ghi chú, rồi bấm **Lưu vi phạm**.
4. Nếu báo "đã ghi lỗi này vừa rồi" nghĩa là lỗi đó đã được ghi trong vài phút trước, không cần ghi lại.
5. Nhận diện sai hoặc "chưa có hồ sơ" thì báo giáo viên, **không** ghi bừa.

Có thể dùng nút **Chọn ảnh** để nhận diện từ ảnh có sẵn.

### Giáo viên (`teacher`, `admin`)
- **Dashboard:** xem thống kê; chọn khoảng ngày rồi bấm **Xuất Excel**.
- **Học sinh:** thêm/sửa/xoá, đồng bộ từ thư mục ảnh.
- **Chatbot:** hỏi theo mã (`HS100301`) hoặc tên để xem danh sách lỗi; hỏi thống kê chung.

### Danh sách lỗi
Hiện có 7 lỗi: *Không đồng phục, Đi trễ, Dùng điện thoại, Không đeo thẻ, Không đội mũ bảo hiểm, Gây mất trật tự, Khác.* Muốn thêm/sửa, chỉnh `backend/violation_types.py` rồi khởi động lại server.

---

## 10. Xuất Excel

**Dashboard → chọn Từ ngày / Đến ngày → Xuất Excel.** Mặc định là tuần này. Ngày được tính theo giờ Việt Nam, gồm cả ngày cuối.

File `vi_pham_<từ>_<đến>.xlsx` gồm hai sheet:

**`CHI TIET`** — mỗi dòng một lỗi:

| STT | THỜI GIAN | HỌ VÀ TÊN | LỚP | LỖI VI PHẠM | GHI CHÚ | NGƯỜI GHI |
|---|---|---|---|---|---|---|

**`NHAP VI PHAM`** — cùng cột với sheet *NHAP VI PHAM* của sổ thi đua, đã gom theo tuần/lớp/mã lỗi:

| TUẦN | LỚP | MÃ LỖI | SỐ LẦN | ĐIỂM QUY ĐỊNH | ĐIỂM ÁP DỤNG 20–30 | TỔNG ĐIỂM TRỪ | GHI CHÚ / CĂN CỨ |
|---|---|---|---|---|---|---|---|

Cách dùng: copy cột **A:D** dán vào sheet *NHAP VI PHAM* của sổ.

**Ánh xạ lỗi → mã lỗi sổ thi đua** (sửa ở `backend/violation_types.py`):

| Lỗi trên app | Mã | Điểm trừ |
|---|---|---|
| Đi trễ | L03 | 2 |
| Không đồng phục | L04 | 2 |
| Dùng điện thoại | L06 | 2 |
| Gây mất trật tự | L02 | 1 |
| Không đội mũ bảo hiểm | L19 | 20 |
| Không đeo thẻ, Khác | *(trống)* | Sổ không có mã tương ứng, các dòng này ghi chú để nhập tay |

> Bảng ánh xạ là cách ghép mặc định, **nhà trường cần rà soát lại** cho đúng quy chế.

---

## 11. Ảnh chụp tự động

Mỗi lần quét **thấy khuôn mặt**, server tự lưu một ảnh JPEG vào:

```
data/capture/2026-10-20/065503_Nguyen_Van_A_10B3_ca1.jpg
```

Ảnh có dải chữ ở đáy: **ngày giờ**, họ tên, lớp, tài khoản ca trực. Khi cờ đỏ bấm **Lưu vi phạm**, ảnh được gắn vào bản ghi (`capture_path`) để làm bằng chứng.

- Giáo viên xem ảnh qua `GET /captures/<ngày>/<tên file>` (cần đăng nhập).
- Dung lượng khoảng 50–150 KB/ảnh. Server **tự xoá ảnh cũ hơn `CAPTURE_KEEP_DAYS` ngày (mặc định 60)** bằng một tác vụ chạy ngầm (lúc khởi động và mỗi 24 giờ), đồng thời gỡ liên kết ảnh trong bản ghi vi phạm tương ứng. Muốn giữ ảnh lâu hơn thì tăng giá trị này hoặc sao lưu thư mục `capture` trước; đặt `0` để tắt tự xoá.
- Nếu chữ tiếng Việt bị lỗi, đặt `CAPTURE_FONT` trỏ tới font `.ttf` hỗ trợ tiếng Việt.

---

## 12. Vận hành thực tế

### Chạy tự động khi bật máy (Windows)
Tạo `start_server.bat`:
```bat
@echo off
cd /d C:\duong\dan\khkt
call venv\Scripts\activate
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
Đặt tác vụ chạy lúc khởi động:
```bat
schtasks /Create /SC ONSTART /TN "KHKT-Server" /TR "C:\duong\dan\khkt\start_server.bat" /RU SYSTEM
```
Có thể dùng **NSSM** để chạy như Windows Service (tự khởi động lại khi lỗi).

### Cloudflare Tunnel
```bat
cloudflared tunnel login
cloudflared tunnel create khkt
cloudflared tunnel route dns khkt tenmien.example.com
```
File `config.yml`:
```yaml
tunnel: khkt
credentials-file: C:\Users\<ten>\.cloudflared\<id>.json
ingress:
  - hostname: tenmien.example.com
    service: http://127.0.0.1:8000
  - service: http_status:404
```
Cài thành service: `cloudflared service install`. Camera trên điện thoại cần HTTPS, Cloudflare đã cung cấp sẵn.

### Khuyến nghị khi mở ra internet
- Đặt **Cloudflare Access** (hoặc WAF/rate-limit) trước ứng dụng.
- Dùng `JWT_SECRET_KEY` dài, ngẫu nhiên; mật khẩu mạnh cho từng tài khoản.
- Máy chủ để chế độ không ngủ (Sleep) và gắn UPS nếu có thể.

### Hiệu năng
- Mô hình chạy CPU. Với ~40 cờ đỏ dùng cùng lúc, các lượt quét sẽ xếp hàng (tối đa 25 giây rồi báo "máy chủ đang bận").
- **Có GPU NVIDIA:** cài `onnxruntime-gpu` (xem mục GPU bên dưới), đặt `INFER_WORKERS=50`. Khi khởi động, log in ra `InsightFace đang chạy bằng: CUDAExecutionProvider, ...`; nếu chỉ thấy `CPUExecutionProvider` nghĩa là GPU chưa được dùng.
- Chỉ có CPU: giữ `INFER_WORKERS=2`; tăng lên không làm nhanh hơn mà còn làm chậm từng lượt.
- Nhiều lượt chạy song song vẫn dùng chung một GPU nên tổng tốc độ có giới hạn; `INFER_WORKERS` chỉ bỏ hàng đợi, không tăng sức mạnh GPU.
- Hãy **kiểm thử tải** bằng số thiết bị thật vào giờ cao điểm trước khi đưa vào sử dụng.

### GPU (NVIDIA)
1. Cài driver NVIDIA mới và **CUDA + cuDNN** đúng phiên bản mà `onnxruntime-gpu` yêu cầu (xem bảng tương thích trên trang onnxruntime).
2. Trong môi trường Python: `pip uninstall onnxruntime onnxruntime-gpu -y` rồi `pip install onnxruntime-gpu` (hai gói không được cài chung).
3. Đặt `INFER_WORKERS=50` trong `.env`, khởi động lại và kiểm tra log. Endpoint `/debug` (admin) cũng trả về `providers`.
4. Nếu CUDA lỗi hoặc thiếu thư viện, hệ thống tự rơi về CPU và vẫn chạy.

### Bảo mật dữ liệu khuôn mặt và chatbot
- Embedding lưu bằng `.npz` (mảng NumPy, đọc với `allow_pickle=False`), không còn dùng `pickle` nên không có rủi ro chạy mã từ file dữ liệu. File được ghi qua file tạm rồi đổi tên.
- Lần chạy đầu sau khi nâng cấp, `face_database.pkl` cũ được tự chuyển sang `.npz` (file cũ giữ nguyên, bạn có thể xoá sau khi kiểm tra nhận diện).
- Chatbot chỉ **đọc** dữ liệu, không có quyền ghi/sửa vi phạm. Đầu vào được làm sạch (cắt độ dài 500/1000 ký tự, bỏ ký tự ẩn, vô hiệu dòng giả danh `system:`), lịch sử giới hạn 10 tin, ghi chú vi phạm đưa vào AI bị ép thành một dòng ngắn, và System Prompt yêu cầu từ chối mọi lệnh giả mạo.
- Mã học sinh được cấp dưới khoá, kết hợp ràng buộc `UNIQUE` của cơ sở dữ liệu và tự thử lại, nên hai người tạo cùng lúc không bao giờ trùng mã.

### Tên lớp và mã học sinh
Mã học sinh luôn là `HS` + khối (2 số) + mã lớp (2 số) + STT. Mã lớp: lớp đánh số (`10A1`, `12B01`, `10 A 3`) lấy số cuối; `10A` lấy thứ tự chữ cái; lớp đặt tên bằng chữ (`10 Tin`, `11CT`, `10 Anh 1`) được gán mã 50–99 cố định theo tên lớp, không trùng với lớp đánh số.

---

## 13. Sao lưu và khôi phục

### Sao lưu
```bat
python tools\backup_db.py
```
Dùng API backup của SQLite (an toàn khi server đang chạy), kiểm tra `integrity_check`, giữ `BACKUP_KEEP` bản mới nhất trong `BACKUP_DIR`.

Đặt lịch mỗi đêm:
```bat
schtasks /Create /SC DAILY /ST 22:00 /TN "KHKT-Backup" /TR "C:\duong\dan\khkt\venv\Scripts\python.exe C:\duong\dan\khkt\tools\backup_db.py"
```
> Đặt `BACKUP_DIR` sang **ổ đĩa khác hoặc máy khác**. Backup cùng ổ với dữ liệu không cứu được khi ổ hỏng.

Cũng nên sao lưu: `resources/` và `data/capture/`.

### Khôi phục
1. Tắt server.
2. Chép bản sao lưu cần dùng thành `data/school.db` (xoá `school.db-wal` và `school.db-shm` nếu có).
3. Bật lại server.

Hãy **thử khôi phục** một lần định kỳ để chắc bản sao lưu dùng được.

---

## 14. Tài liệu API

Server tự sinh tài liệu tương tác tại `/docs` (Swagger). Các endpoint chính:

| Method | Đường dẫn | Quyền | Mô tả |
|---|---|---|---|
| POST | `/login` | công khai | Đăng nhập, trả JWT |
| POST | `/recognize-face` | đăng nhập | Nhận diện ảnh, tự lưu ảnh chụp |
| GET | `/violation-types` | đăng nhập | Danh sách lỗi cho phép |
| POST | `/violations` | đăng nhập | Thêm 1+ lỗi (`violation_types: []`) |
| GET | `/violations` | giáo viên | Danh sách vi phạm |
| GET | `/export/violations?from=&to=&class_name=` | giáo viên | Xuất Excel |
| GET | `/captures/<ngày>/<file>` | giáo viên | Xem ảnh chụp |
| GET | `/stats/summary`, `/stats/daily`, `/stats/by-type`, `/stats/top-violators` | giáo viên | Thống kê |
| GET/POST/PUT/DELETE | `/students` | giáo viên | Quản lý học sinh |
| POST | `/import-from-folders` | giáo viên | Đồng bộ khuôn mặt + hồ sơ |
| GET | `/chatbot/lookup` · POST `/chatbot` | giáo viên | Tra cứu / chatbot |
| POST | `/create-user` | admin | Tạo tài khoản |
| GET | `/debug` | admin | Trạng thái dữ liệu khuôn mặt |

---

## 15. Xử lý sự cố

| Hiện tượng | Nguyên nhân / cách xử lý |
|---|---|
| `JWT_SECRET_KEY chưa được đặt` | Điền `JWT_SECRET_KEY` trong `.env`. |
| Không bật được camera trên điện thoại | Phải truy cập bằng **HTTPS** (qua Cloudflare), cấp quyền camera cho trình duyệt. |
| "Cờ đỏ bị 403 khi lưu vi phạm" | Đang dùng bản cũ. Hãy cập nhật `backend/main.py` bản mới. |
| "Không nhận diện được" nhiều | Ảnh mờ/thiếu sáng/mặt quá nhỏ; thêm ảnh mẫu đa dạng cho học sinh; chụp gần và đủ sáng. |
| "Chưa có hồ sơ học sinh" | Khuôn mặt có trong `face_database.npz` nhưng chưa có học sinh; vào **Học sinh → Đồng bộ lại**. |
| Báo "Máy chủ đang bận" | Nhiều người quét cùng lúc; quét lại sau vài giây hoặc tăng `INFER_WORKERS`. |
| Chữ trên ảnh chụp bị ô vuông | Đặt `CAPTURE_FONT` tới font có tiếng Việt. |
| Excel cột TUẦN sai | Chỉnh `SCHOOL_WEEK1_START` cho đúng thứ Hai của tuần 1. |
| `database is locked` | Có tiến trình khác đang giữ DB (ví dụ DB Browser đang mở ở chế độ ghi); đóng lại. |
| Ảnh khuôn mặt hiện file con trỏ Git LFS | Repo còn dùng LFS: chạy `git lfs pull` hoặc chép file thật vào `resources/`. |
| Lỗi cài `insightface` trên Windows | Cài **Microsoft C++ Build Tools**, rồi `pip install insightface` lại. |

Chế độ thử nhanh bằng cửa sổ OpenCV (không cần server): `python run_local_cv.py` (phím `q`/`ESC` thoát, `a` học thêm người mới).

---

## 16. Giới hạn đã biết

- **Chưa có chống giả mạo** (ảnh in/ảnh trên điện thoại): hệ thống dựa vào việc cờ đỏ đứng trực tiếp tại cổng.
- Khi có nhiều khuôn mặt trong khung, hệ thống dùng khuôn mặt đầu tiên; nên quét từng học sinh một.
- **Chưa giới hạn số lần đăng nhập sai**; khi mở ra internet nên dùng Cloudflare Access/WAF.
- Token ảnh đang đi qua URL (`?token=`); nên ưu tiên dùng Cloudflare Access và HTTPS.
- Ngưỡng nhận diện cố định `0,5` (`core/FaissIndex.py`); nên đo tỉ lệ nhận nhầm/bỏ sót trên dữ liệu thật của trường và hiệu chỉnh.
- Chưa có cơ chế hủy/sửa bản ghi do nhận diện nhầm trên giao diện; hiện cần giáo viên xử lý trực tiếp trong cơ sở dữ liệu.
- Dữ liệu khuôn mặt và ảnh chụp của học sinh là **dữ liệu nhạy cảm**: chỉ lưu trong máy của trường, không đưa lên Git hoặc dịch vụ công khai, và giới hạn người có quyền truy cập thư mục `data/`, `resources/`.

---

*AI School — hệ thống ghi nhận vi phạm bằng nhận diện khuôn mặt.*
