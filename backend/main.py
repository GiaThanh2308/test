from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from typing import Optional, Annotated
import numpy as np
import cv2
import os
import re
import httpx
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

from backend.database.db import engine, SessionLocal
from backend.database.models import Base, Student, User, Violation
from backend.schemas.student import (
    StudentCreate, StudentUpdate, ViolationCreate,
    ChatMessage, ChatRequest
)
from backend.auth import (
    hash_password, verify_password,
    create_access_token, get_current_user, require_admin
)
from core.AdvancedFaceRecognitionSystem import AdvancedFaceRecognitionSystem

# FIX: dùng lifespan thay @app.on_event("startup") đã deprecated
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Loading face recognition model...")
    if system.database.known_encodings:
        system.faiss_index.build_index(
            system.database.known_encodings,
            system.database.known_names
        )
        print("✅ FAISS loaded")
    else:
        print("⚠️ Database khuôn mặt đang trống")
    print("✅ Model loaded")
    yield  # app chạy ở đây
    # shutdown logic nếu cần đặt sau yield

app = FastAPI(title="AI School API", lifespan=lifespan)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", ["http://127.0.0.1:5500", "http://localhost:5500", "http://127.0.0.1:5501", "http://localhost:5501"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

system = AdvancedFaceRecognitionSystem()

_ocr_reader = None

def get_ocr():
    global _ocr_reader
    if _ocr_reader is None:
        import easyocr
        _ocr_reader = easyocr.Reader(["en"], gpu=False)
        print("✅ EasyOCR loaded")
    return _ocr_reader


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── FACE RECOGNITION ────────────────────────────────────────

@app.post("/recognize-face")
async def recognize_face(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    contents = await file.read()
    np_arr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(status_code=400, detail="Không đọc được ảnh")

    ai_results = system.recognize_image(img)

    if not ai_results:
        return {"faces": []}

    results = []
    for item in ai_results:
        name = item["name"]
        score = item["score"]
        if name == "unknown":
            results.append({
                "id": None,
                "face_label": "unknown",
                "score": float(score),
                "message": "Không nhận diện được"
            })
            continue
        student = db.query(Student).filter(Student.face_label == name).first()

        if student:
            results.append({
                "id":           student.id,
                "student_code": student.student_code,
                "full_name":    student.full_name,
                "class_name":   student.class_name,
                "phone":        student.phone,
                "parent_phone": student.parent_phone,
                "plate_number": student.plate_number,
                "score":        float(score)
            })
        else:
            results.append({
                "id":         None,
                "face_label": name,
                "score":      float(score),
                "message":    "Chưa có hồ sơ học sinh"
            })

    return {"faces": results}


# ─── PLATE RECOGNITION ───────────────────────────────────────

def clean_plate(raw: str) -> str:
    text = re.sub(r"[^A-Za-z0-9]", "", raw).upper()
    return text


def preprocess_plate(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


@app.post("/recognize-plate")
async def recognize_plate(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    contents = await file.read()
    np_arr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(status_code=400, detail="Không đọc được ảnh")

    ocr = get_ocr()
    results = ocr.readtext(img, detail=1, paragraph=False)

    if not results:
        processed = preprocess_plate(img)
        results = ocr.readtext(processed, detail=1, paragraph=False)

    if not results:
        return {"plate_number": None, "student": None, "message": "Không đọc được biển số"}

    results.sort(key=lambda x: x[2], reverse=True)
    raw_texts   = [r[1] for r in results[:3]]
    raw_plate   = " ".join(raw_texts)
    plate_clean = clean_plate(raw_plate)

    if len(plate_clean) < 5:
        return {
            "plate_number": plate_clean or raw_plate,
            "student": None,
            "message": "Biển số quá ngắn, không thể tra cứu"
        }

    student = db.query(Student).filter(
        Student.plate_number.ilike(f"%{plate_clean}%")
    ).first()

    if not student and len(plate_clean) >= 6:
        suffix = plate_clean[-6:]
        student = db.query(Student).filter(
            Student.plate_number.ilike(f"%{suffix}%")
        ).first()

    student_data = None
    if student:
        student_data = {
            "id":           student.id,
            "student_code": student.student_code,
            "full_name":    student.full_name,
            "class_name":   student.class_name,
            "phone":        student.phone,
            "parent_phone": student.parent_phone,
            "plate_number": student.plate_number,
        }

    return {
        "plate_number": plate_clean,
        "raw_text":     raw_plate,
        "confidence":   round(float(results[0][2]), 2),
        "student":      student_data,
        "message":      "Tìm thấy học sinh" if student_data else "Không tìm thấy học sinh với biển số này"
    }


# ─── STUDENTS ────────────────────────────────────────────────

@app.get("/students")
def get_students(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    students = db.query(Student).all()
    return [
        {
            "id":           s.id,
            "student_code": s.student_code,
            "full_name":    s.full_name,
            "class_name":   s.class_name,
            "phone":        s.phone,
            "parent_phone": s.parent_phone,
            "face_label":   s.face_label,
            "plate_number": s.plate_number,
        }
        for s in students
    ]


@app.get("/students/{student_id}")
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Không tìm thấy học sinh")
    return {
        "id":           student.id,
        "student_code": student.student_code,
        "full_name":    student.full_name,
        "class_name":   student.class_name,
        "phone":        student.phone,
        "parent_phone": student.parent_phone,
        "face_label":   student.face_label,
        "plate_number": student.plate_number,
    }


@app.post("/students")
def create_student(
    student: StudentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    existing = db.query(Student).filter(Student.student_code == student.student_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Mã học sinh đã tồn tại")

    face_label = (student.face_label or "").strip() or None

    if face_label:
        dup = db.query(Student).filter(Student.face_label == face_label).first()
        if dup:
            raise HTTPException(status_code=400, detail="Face label đã được dùng bởi học sinh khác")

    new_student = Student(
        student_code = student.student_code,
        full_name    = student.full_name,
        class_name   = student.class_name,
        face_label   = face_label,
        phone        = student.phone,
        parent_phone = student.parent_phone,
        plate_number = student.plate_number,
    )
    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    return {"message": "Đã thêm học sinh", "id": new_student.id}


@app.put("/students/{student_id}")
def update_student(
    student_id: int,
    student: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    db_student = db.query(Student).filter(Student.id == student_id).first()
    if not db_student:
        raise HTTPException(status_code=404, detail="Không tìm thấy học sinh")

    if student.student_code is not None: db_student.student_code = student.student_code
    if student.full_name    is not None: db_student.full_name    = student.full_name
    if student.class_name   is not None: db_student.class_name   = student.class_name
    if student.phone        is not None: db_student.phone        = student.phone
    if student.parent_phone is not None: db_student.parent_phone = student.parent_phone
    if student.plate_number is not None: db_student.plate_number = student.plate_number

    if student.face_label is not None:
        face_label = student.face_label.strip() or None
        if face_label:
            dup = db.query(Student).filter(
                Student.face_label == face_label,
                Student.id != student_id
            ).first()
            if dup:
                raise HTTPException(status_code=400, detail="Face label đã được dùng bởi học sinh khác")
        db_student.face_label = face_label

    db.commit()
    return {"message": "Đã cập nhật học sinh"}


@app.delete("/students/{student_id}")
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Không tìm thấy học sinh")
    db.delete(student)
    db.commit()
    return {"message": "Đã xóa học sinh"}


# ─── VIOLATIONS ──────────────────────────────────────────────

@app.post("/violations")
def create_violation(
    violation: ViolationCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    student = db.query(Student).filter(Student.id == violation.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Không tìm thấy học sinh")

    new_v = Violation(
        student_id     = violation.student_id,
        violation_type = violation.violation_type,
        note           = violation.note,
        image_path     = violation.image_path,
    )
    db.add(new_v)
    db.commit()
    db.refresh(new_v)
    return {"message": "Đã lưu vi phạm", "id": new_v.id}


@app.get("/violations")
def get_violations(
    student_id: Optional[int] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    query = db.query(Violation)
    if student_id:
        query = query.filter(Violation.student_id == student_id)
    violations = query.order_by(Violation.created_at.desc()).limit(limit).all()

    return [
        {
            "id":             v.id,
            "student_id":     v.student_id,
            "student_name":   v.student.full_name    if v.student else "",
            "student_code":   v.student.student_code if v.student else "",
            "class_name":     v.student.class_name   if v.student else "",
            "violation_type": v.violation_type,
            "note":           v.note,
            "image_path":     v.image_path,   # FIX: thêm trường bị thiếu
            "created_at":     v.created_at.isoformat(),
        }
        for v in violations
    ]


# ─── THỐNG KÊ ────────────────────────────────────────────────

@app.get("/stats/summary")
def get_summary(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    now         = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start  = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    return {
        "total_students":   db.query(Student).count(),
        "today_violations": db.query(Violation).filter(Violation.created_at >= today_start).count(),
        "week_violations":  db.query(Violation).filter(Violation.created_at >= week_start).count(),
        "month_violations": db.query(Violation).filter(Violation.created_at >= month_start).count(),
        "total_violations": db.query(Violation).count(),
    }


@app.get("/stats/daily")
def get_daily_stats(
    days: int = Query(default=7, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    result = []
    for i in range(days - 1, -1, -1):
        day     = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
        day_end = day + timedelta(days=1)
        count   = db.query(Violation).filter(
            Violation.created_at >= day,
            Violation.created_at < day_end
        ).count()
        result.append({"date": day.strftime("%d/%m"), "count": count})
    return result


@app.get("/stats/by-type")
def get_stats_by_type(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    rows = db.query(
        Violation.violation_type,
        func.count(Violation.id).label("count")
    ).group_by(Violation.violation_type).all()
    return [{"type": r.violation_type, "count": r.count} for r in rows]


@app.get("/stats/top-violators")
def get_top_violators(
    limit: int = Query(default=5, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    rows = db.query(
        Student.full_name,
        Student.class_name,
        Student.student_code,
        func.count(Violation.id).label("count")
    ).join(Violation, Student.id == Violation.student_id)\
     .group_by(Student.id)\
     .order_by(func.count(Violation.id).desc())\
     .limit(limit).all()   # FIX: giới hạn tối đa 50

    return [
        {"full_name": r.full_name, "class_name": r.class_name,
         "student_code": r.student_code, "count": r.count}
        for r in rows
    ]


# ─── AUTH ─────────────────────────────────────────────────────

@app.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Sai tài khoản hoặc mật khẩu",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": user.username, "role": user.role})
    return {
        "access_token": token,
        "token_type":   "bearer",
        "role":         user.role,
        "username":     user.username,
    }


# FIX: dùng Pydantic body thay query params — tránh lộ password qua URL/log
class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "teacher"

@app.post("/create-user")
def create_user(
    body: CreateUserRequest,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin)
):
    existing = db.query(User).filter(User.username == body.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username đã tồn tại")

    user = User(username=body.username, hashed_password=hash_password(body.password), role=body.role)
    db.add(user)
    db.commit()
    return {"message": "User created"}


# ─── CHATBOT (Gemini) ─────────────────────────────────────────

@app.post("/chatbot")
async def chatbot(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY chưa được cấu hình trong file .env")

    now         = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start  = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    total_students = db.query(Student).count()
    today_v  = db.query(Violation).filter(Violation.created_at >= today_start).count()
    week_v   = db.query(Violation).filter(Violation.created_at >= week_start).count()
    month_v  = db.query(Violation).filter(Violation.created_at >= month_start).count()
    total_v  = db.query(Violation).count()

    top_rows = (
        db.query(Student.full_name, Student.student_code, Student.class_name,
                 func.count(Violation.id).label("cnt"))
        .join(Violation, Student.id == Violation.student_id)
        .group_by(Student.id)
        .order_by(func.count(Violation.id).desc())
        .limit(5).all()
    )
    top_list = "\n".join(
        f"  {i+1}. {r.full_name} ({r.student_code} - {r.class_name}): {r.cnt} vi phạm"
        for i, r in enumerate(top_rows)
    ) or "  (chưa có dữ liệu)"

    type_rows = db.query(Violation.violation_type, func.count(Violation.id).label("cnt"))\
                  .group_by(Violation.violation_type).all()
    type_list = "\n".join(f"  - {r.violation_type}: {r.cnt} lần" for r in type_rows) or "  (chưa có dữ liệu)"

    recent = db.query(Violation).order_by(Violation.created_at.desc()).limit(10).all()
    recent_list = "\n".join(
        f"  - {v.student.full_name if v.student else '?'} ({v.student.class_name if v.student else '?'}): "
        f"{v.violation_type} lúc {v.created_at.strftime('%d/%m/%Y %H:%M')}"
        for v in recent
    ) or "  (chưa có dữ liệu)"

    system_prompt = f"""Bạn là AI School Assistant — trợ lý thông minh của hệ thống quản lý học sinh THPT.

Thời gian hiện tại: {now.strftime('%d/%m/%Y %H:%M')}

=== DỮ LIỆU THỰC TẾ HỆ THỐNG ===

TỔNG QUAN:
- Tổng học sinh: {total_students}
- Vi phạm hôm nay: {today_v}
- Vi phạm tuần này: {week_v}
- Vi phạm tháng này: {month_v}
- Tổng vi phạm toàn thời gian: {total_v}

HỌC SINH VI PHẠM NHIỀU NHẤT:
{top_list}

PHÂN LOẠI VI PHẠM:
{type_list}

VI PHẠM GẦN ĐÂY NHẤT:
{recent_list}

=== HƯỚNG DẪN ===
- Chỉ trả lời về quản lý học sinh, vi phạm, thống kê trường học
- Dùng số liệu thực tế ở trên, không bịa đặt
- Tiếng Việt, ngắn gọn, chuyên nghiệp
- Dùng danh sách khi liệt kê nhiều mục
- Nếu câu hỏi nằm ngoài phạm vi, lịch sự từ chối"""

    gemini_contents = [
        {
            "role": "model" if msg.role == "assistant" else "user",
            "parts": [{"text": msg.content}]
        }
        for msg in req.messages
    ]

    gemini_url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={api_key}"
    )

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": gemini_contents,
        "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.7},
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(gemini_url, json=payload, timeout=30.0)

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Gemini API lỗi {response.status_code}: {response.text[:300]}")

    data = response.json()
    try:
        reply = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise HTTPException(status_code=502, detail="Gemini trả về response không hợp lệ")

    return {"reply": reply}
