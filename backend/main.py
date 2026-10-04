"""AI School API — nhận diện khuôn mặt, quản lý học sinh/vi phạm, thống kê, chatbot."""
import os
import re
import time
from collections import Counter, defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import quote

import cv2
import httpx
import numpy as np
from dotenv import load_dotenv

load_dotenv()  # phải chạy trước khi import các module đọc biến môi trường

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.security import OAuth2PasswordRequestForm  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from sqlalchemy import func  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from backend.auth import (  # noqa: E402
    TEACHER_ROLES, create_access_token, decode_token, get_current_user,
    hash_password, require_admin, require_teacher, verify_password,
)
from backend.database.db import SessionLocal, engine, push_db  # noqa: E402
from backend.database.models import Base, IgnoredLabel, Student, User, Violation  # noqa: E402
from backend.face_folders import CodeAllocator, FaceFolderIndex, plain_text, sync_students  # noqa: E402
from backend.schemas.student import (  # noqa: E402
    ChatRequest, CreateUserRequest, StudentCreate, StudentUpdate, ViolationCreate,
)
from core.AdvancedFaceRecognitionSystem import AdvancedFaceRecognitionSystem  # noqa: E402

# ── Cấu hình ─────────────────────────────────────────────────────────────────
PROJECT_ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCE_DIR       = os.getenv("RESOURCE_DIR", os.path.join(PROJECT_ROOT, "resources"))
FACE_DATABASE_PATH = os.path.abspath(os.getenv("FACE_DATABASE_PATH", os.path.join(RESOURCE_DIR, "face_database.pkl")))
KNOWN_FACES_DIR    = os.path.abspath(os.getenv("KNOWN_FACES_DIR", os.path.join(RESOURCE_DIR, "known_faces")))
FRONTEND_DIR       = os.path.join(PROJECT_ROOT, "frontend")
GROQ_MODEL         = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
ROLES              = ("admin", "teacher", "student")

# Thống kê "hôm nay / tuần / tháng" phải tính theo giờ Việt Nam, không phải UTC
LOCAL_TZ = timezone(timedelta(hours=float(os.getenv("TZ_OFFSET_HOURS", "7"))))

system     = AdvancedFaceRecognitionSystem(database_path=FACE_DATABASE_PATH)
FACE_INDEX = FaceFolderIndex(KNOWN_FACES_DIR)  # label → ảnh đại diện, dựng một lần


def refresh_face_index() -> FaceFolderIndex:
    global FACE_INDEX
    FACE_INDEX = FaceFolderIndex(KNOWN_FACES_DIR)
    return FACE_INDEX


@asynccontextmanager
async def lifespan(app: FastAPI):
    if system.database.known_names:
        system.build_ann_index()
    else:
        print("⚠️ Database khuôn mặt đang trống")

    # Tự tạo hồ sơ học sinh từ thư mục known_faces (đặt AUTO_SYNC_STUDENTS=0 để tắt)
    if os.getenv("AUTO_SYNC_STUDENTS", "1") != "0":
        db = SessionLocal()
        try:
            result = sync_students(db, Student, FACE_INDEX, ignored_labels(db))
            if result["created"] or result["recoded"]:
                push_db()
            print(f"👥 Đồng bộ học sinh: +{len(result['created'])} mới, {len(result['recoded'])} đổi mã, "
                  f"{len(result['skipped'])} đã có, {len(result['errors'])} lỗi")
        except Exception as e:
            print(f"⚠️ Không đồng bộ được học sinh: {e}")
        finally:
            db.close()
    yield


app = FastAPI(title="AI School API", lifespan=lifespan)

# CORS chỉ cần khi frontend chạy ở origin khác (vd Live Server). Cùng origin thì không cần.
_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()] or [
    "http://localhost:5500", "http://127.0.0.1:5500", "http://localhost:5501", "http://127.0.0.1:5501",
]
_wildcard = _origins == ["*"]
app.add_middleware(
    CORSMiddleware, allow_origins=_origins, allow_credentials=not _wildcard,
    allow_methods=["*"], allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Tiện ích ─────────────────────────────────────────────────────────────────
def iso_utc(dt: Optional[datetime]) -> Optional[str]:
    """SQLite trả datetime không múi giờ → gắn UTC để trình duyệt đổi đúng sang giờ máy."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def local_midnight(days_ago: int = 0) -> datetime:
    now = datetime.now(LOCAL_TZ)
    return now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_ago)


def period_starts() -> dict:
    """Mốc đầu ngày/tuần(T2)/tháng theo giờ VN, đã đổi sang UTC để so với DB."""
    today = local_midnight()
    return {
        "today": today.astimezone(timezone.utc),
        "week":  (today - timedelta(days=today.weekday())).astimezone(timezone.utc),
        "month": today.replace(day=1).astimezone(timezone.utc),
    }


def violation_counts(db: Session) -> dict:
    s = period_starts()
    count = lambda *f: db.query(Violation).filter(*f).count()  # noqa: E731
    return {
        "total_students":   db.query(Student).count(),
        "today_violations": count(Violation.created_at >= s["today"]),
        "week_violations":  count(Violation.created_at >= s["week"]),
        "month_violations": count(Violation.created_at >= s["month"]),
        "total_violations": count(),
    }


def top_violators(db: Session, limit: int, since: Optional[datetime] = None):
    q = (db.query(Student.full_name, Student.class_name, Student.student_code,
                  func.count(Violation.id).label("count"))
         .join(Violation, Student.id == Violation.student_id))
    if since is not None:
        q = q.filter(Violation.created_at >= since)
    return q.group_by(Student.id).order_by(func.count(Violation.id).desc()).limit(limit).all()


def face_image_url(face_label: Optional[str]) -> Optional[str]:
    label = (face_label or "").strip()
    return f"/face-image/{quote(label, safe='')}" if FACE_INDEX.image_path(label) else None


def student_dict(s: Student) -> dict:
    return {
        "id": s.id, "student_code": s.student_code, "full_name": s.full_name,
        "class_name": s.class_name, "phone": s.phone, "face_label": s.face_label,
        "face_image_url": face_image_url(s.face_label),
    }


def ensure_unique(db: Session, student_id: Optional[int], code: Optional[str], label: Optional[str]):
    """Mã học sinh và face_label không được trùng người khác."""
    for column, value, msg in ((Student.student_code, code, "Mã học sinh đã tồn tại"),
                               (Student.face_label, label, "Face label đã được dùng bởi học sinh khác")):
        if not value:
            continue
        q = db.query(Student).filter(column == value)
        if student_id is not None:
            q = q.filter(Student.id != student_id)
        if q.first():
            raise HTTPException(status_code=400, detail=msg)


MAX_UPLOAD_BYTES = 8 * 1024 * 1024
LOGIN_MAX_FAILS, LOGIN_WINDOW = 5, 300  # tối đa 5 lần sai / 5 phút cho mỗi (IP, tài khoản)
_login_fails: dict[str, list[float]] = defaultdict(list)


def client_ip(request: Request) -> str:
    """Qua Cloudflare Tunnel IP thật nằm ở header cf-connecting-ip."""
    return (request.headers.get("cf-connecting-ip")
            or request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            or (request.client.host if request.client else "?"))


def login_blocked(key: str) -> int:
    """Số giây còn bị khóa (0 = được thử)."""
    now = time.time()
    hits = [t for t in _login_fails.get(key, []) if now - t < LOGIN_WINDOW]
    if hits:
        _login_fails[key] = hits
    else:
        _login_fails.pop(key, None)
    return int(LOGIN_WINDOW - (now - hits[0])) + 1 if len(hits) >= LOGIN_MAX_FAILS else 0


def ignored_labels(db: Session) -> set:
    return {label for (label,) in db.query(IgnoredLabel.label).all()}


def forget_ignored(db: Session, label: Optional[str]):
    if label:
        db.query(IgnoredLabel).filter(IgnoredLabel.label == label).delete()


# ── Ảnh khuôn mặt ────────────────────────────────────────────────────────────
@app.get("/face-image/{face_label}")
def serve_face_image(face_label: str, request: Request):
    """Cần đăng nhập (header Authorization). Frontend tải ảnh bằng fetch rồi dựng blob nên token không nằm trong URL."""
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Cần đăng nhập")
    decode_token(auth[7:])
    path = FACE_INDEX.image_path(face_label)
    if not path:
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh")
    return FileResponse(path, headers={"Cache-Control": "private, max-age=3600"})


# ── Nhận diện ────────────────────────────────────────────────────────────────
@app.post("/recognize-face")
def recognize_face(  # def (không async): AI nặng chạy ở thread riêng, không chặn server
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    raw = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Ảnh quá lớn (tối đa 8 MB)")
    img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Không đọc được ảnh")

    results = []
    for item in system.recognize_image(img):
        name, score = item["name"], float(item["score"])
        if name == "unknown":
            results.append({"id": None, "face_label": "unknown", "score": score, "status": "unknown", "message": "Không nhận diện được"})
            continue
        student = db.query(Student).filter(Student.face_label == name).first()
        if student:
            results.append({**student_dict(student), "score": score, "status": "ok"})
        else:
            results.append({"id": None, "face_label": name, "score": score, "status": "no_profile", "message": "Chưa có hồ sơ học sinh"})

    if current_user["role"] not in TEACHER_ROLES:
        # student chỉ xem họ tên + lớp + ảnh + độ khớp; ẩn mã HS, SĐT, nhãn khuôn mặt
        keep = ("id", "full_name", "class_name", "face_image_url", "score", "status", "message")
        results = [{k: r[k] for k in keep if k in r} for r in results]
    return {"faces": results}


# ── Học sinh ─────────────────────────────────────────────────────────────────
@app.get("/students")
def list_students(db: Session = Depends(get_db), _user: dict = Depends(require_teacher)):
    return [student_dict(s) for s in db.query(Student).order_by(Student.class_name, Student.full_name).all()]


@app.post("/students")
def create_student(body: StudentCreate, db: Session = Depends(get_db), _user: dict = Depends(require_teacher)):
    face_label = (body.face_label or "").strip() or None
    code = (body.student_code or "").strip()
    if not code:  # không nhập mã → tự cấp theo lớp: HS + khối + lớp + STT
        code = CodeAllocator(c for (c,) in db.query(Student.student_code).all()).allocate(body.class_name)
    ensure_unique(db, None, code, face_label)
    forget_ignored(db, face_label)
    student = Student(student_code=code, full_name=body.full_name,
                      class_name=body.class_name, face_label=face_label, phone=body.phone)
    db.add(student)
    db.commit()
    push_db()
    return {"message": "Đã thêm học sinh", "id": student.id}


@app.put("/students/{student_id}")
def update_student(student_id: int, body: StudentUpdate, db: Session = Depends(get_db),
                   _user: dict = Depends(require_teacher)):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Không tìm thấy học sinh")

    changes = body.model_dump(exclude_unset=True)
    if "student_code" in changes:
        changes["student_code"] = (changes["student_code"] or "").strip() or None
        if changes["student_code"] is None:
            del changes["student_code"]  # để trống = giữ mã cũ
    if "face_label" in changes:
        changes["face_label"] = (changes["face_label"] or "").strip() or None
    ensure_unique(db, student_id, changes.get("student_code"), changes.get("face_label"))  # bản cũ không kiểm tra mã trùng → lỗi 500
    forget_ignored(db, changes.get("face_label"))
    for field, value in changes.items():
        setattr(student, field, value)
    db.commit()
    push_db()
    return {"message": "Đã cập nhật học sinh"}


@app.delete("/students/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db), _user: dict = Depends(require_teacher)):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Không tìm thấy học sinh")
    if student.face_label and student.face_label not in ignored_labels(db):
        db.add(IgnoredLabel(label=student.face_label))  # "Đồng bộ lại" sẽ bỏ qua nhãn này
    db.delete(student)
    db.commit()
    push_db()
    return {"message": "Đã xóa học sinh"}


@app.post("/import-from-folders")
def sync_from_folders(db: Session = Depends(get_db), _user: dict = Depends(require_teacher)):
    """Đồng bộ lại: học khuôn mặt người mới trong known_faces, rồi tạo hồ sơ học sinh còn thiếu."""
    if not os.path.isdir(KNOWN_FACES_DIR):
        raise HTTPException(status_code=404, detail=f"Không tìm thấy thư mục: {KNOWN_FACES_DIR}")
    learned = system.rescan_known_faces(KNOWN_FACES_DIR)  # trước đây chỉ tạo hồ sơ, người mới không bao giờ được nhận diện
    result = sync_students(db, Student, refresh_face_index(), ignored_labels(db))
    if result["created"] or result["recoded"]:
        push_db()
    return {
        "message": f"Đồng bộ xong: {len(result['created'])} hồ sơ mới, {len(result['recoded'])} hồ sơ đổi sang mã mới, "
                   f"{len(learned)} khuôn mặt mới học, {len(result['skipped'])} đã có, {len(result['errors'])} lỗi",
        "learned": learned, **result,
    }


# ── Vi phạm ──────────────────────────────────────────────────────────────────
@app.post("/violations")
def create_violation(body: ViolationCreate, db: Session = Depends(get_db), _user: dict = Depends(require_teacher)):
    if not db.get(Student, body.student_id):
        raise HTTPException(status_code=404, detail="Không tìm thấy học sinh")
    violation = Violation(student_id=body.student_id, violation_type=body.violation_type, note=body.note)
    db.add(violation)
    db.commit()
    push_db()
    return {"message": "Đã lưu vi phạm", "id": violation.id}


@app.get("/violations")
def list_violations(
    student_id: Optional[int] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: dict = Depends(require_teacher),
):
    q = db.query(Violation)
    if student_id:
        q = q.filter(Violation.student_id == student_id)
    return [
        {
            "id": v.id, "student_id": v.student_id,
            "student_name": v.student.full_name if v.student else "",
            "student_code": v.student.student_code if v.student else "",
            "class_name":   v.student.class_name if v.student else "",
            "violation_type": v.violation_type, "note": v.note,
            "created_at": iso_utc(v.created_at),
        }
        for v in q.order_by(Violation.created_at.desc()).limit(limit).all()
    ]


# ── Thống kê ─────────────────────────────────────────────────────────────────
@app.get("/stats/summary")
def stats_summary(db: Session = Depends(get_db), _user: dict = Depends(require_teacher)):
    return violation_counts(db)


@app.get("/stats/daily")
def stats_daily(days: int = Query(default=7, ge=1, le=90), db: Session = Depends(get_db),
                _user: dict = Depends(require_teacher)):
    start = local_midnight(days - 1)
    rows = db.query(Violation.created_at).filter(Violation.created_at >= start.astimezone(timezone.utc)).all()
    per_day = Counter(
        (r[0] if r[0].tzinfo else r[0].replace(tzinfo=timezone.utc)).astimezone(LOCAL_TZ).date() for r in rows
    )
    return [
        {"date": (start + timedelta(days=i)).strftime("%d/%m"), "count": per_day[(start + timedelta(days=i)).date()]}
        for i in range(days)
    ]


@app.get("/stats/by-type")
def stats_by_type(db: Session = Depends(get_db), _user: dict = Depends(require_teacher)):
    rows = db.query(Violation.violation_type, func.count(Violation.id)).group_by(Violation.violation_type).all()
    return [{"type": t, "count": c} for t, c in rows]


@app.get("/stats/top-violators")
def stats_top_violators(limit: int = Query(default=5, ge=1, le=50), db: Session = Depends(get_db),
                        _user: dict = Depends(require_teacher)):
    return [{"full_name": r.full_name, "class_name": r.class_name,
             "student_code": r.student_code, "count": r.count}
            for r in top_violators(db, limit, period_starts()["month"])]  # nhãn "Tháng này" trên dashboard


# ── Đăng nhập / người dùng ───────────────────────────────────────────────────
@app.post("/login")
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    key = f"{client_ip(request)}|{form.username.strip().lower()}"
    wait = login_blocked(key)
    if wait:
        raise HTTPException(status_code=429, detail=f"Sai quá nhiều lần. Thử lại sau {wait // 60 + 1} phút.")
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        _login_fails[key].append(time.time())
        raise HTTPException(status_code=401, detail="Sai tài khoản hoặc mật khẩu",
                            headers={"WWW-Authenticate": "Bearer"})
    _login_fails.pop(key, None)
    token = create_access_token({"sub": user.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer", "role": user.role, "username": user.username}


@app.post("/create-user")
def create_user(body: CreateUserRequest, db: Session = Depends(get_db), _admin: dict = Depends(require_admin)):
    if body.role not in ROLES:
        raise HTTPException(status_code=400, detail="Role phải là admin / teacher / student")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Mật khẩu phải có ít nhất 6 ký tự")
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail="Username đã tồn tại")
    db.add(User(username=body.username, hashed_password=hash_password(body.password), role=body.role))
    db.commit()
    return {"message": "User created"}


@app.get("/debug")
def debug(_admin: dict = Depends(require_admin)):
    return {
        "FACE_DATABASE_PATH": FACE_DATABASE_PATH, "KNOWN_FACES_DIR": KNOWN_FACES_DIR,
        "db_exists": os.path.exists(FACE_DATABASE_PATH),
        "known_faces_exists": os.path.isdir(KNOWN_FACES_DIR),
        "loaded_people": len(system.database.known_names),
        "indexed_folders": len(FACE_INDEX.students),
    }


# ── Tra cứu học sinh (chatbot) ───────────────────────────────────────────────
CODE_IN_TEXT = re.compile(r"\bHS\s?\d{3,}\b", re.IGNORECASE)
FULL_CODE    = re.compile(r"^HS\d{6,}$")
MAX_LISTED_VIOLATIONS = 20


def find_students(db: Session, query: str, limit: int = 5) -> list[Student]:
    """Tìm theo mã (khớp CHÍNH XÁC, không phân biệt hoa thường) → tên (không dấu) → mã một phần."""
    query = (query or "").strip()
    if not query:
        return []
    students = db.query(Student).order_by(Student.class_name, Student.full_name).all()

    compact = re.sub(r"[\s\-_.]", "", query).upper()
    for cand in ((compact, "HS" + compact) if compact.isdigit() else (compact,)):
        exact = [s for s in students if (s.student_code or "").upper() == cand]
        if exact:
            return exact[:1]
    if FULL_CODE.match(compact):
        return []  # đã nhập đủ mã mà không có → báo không tìm thấy, không đoán sang người khác

    words = plain_text(query).split()
    by_name = [s for s in students if all(w in plain_text(s.full_name) for w in words)]
    if by_name:
        return by_name[:limit]
    return [s for s in students if compact and compact in (s.student_code or "").upper()][:limit]


def format_student_report(db: Session, s: Student) -> str:
    vs = (db.query(Violation).filter(Violation.student_id == s.id)
          .order_by(Violation.created_at.desc()).all())
    lines = [f"**{s.full_name}** — Mã HS: **{s.student_code}** · Lớp: {s.class_name}"]
    if not vs:
        lines.append("- Không có lỗi vi phạm nào")
        return "\n".join(lines)
    lines.append(f"- Tổng số lỗi vi phạm: {len(vs)}")
    for v in vs[:MAX_LISTED_VIOLATIONS]:
        when = (v.created_at if v.created_at.tzinfo else v.created_at.replace(tzinfo=timezone.utc))
        note = f" ({v.note.strip()})" if (v.note or "").strip() else ""
        lines.append(f"- {when.astimezone(LOCAL_TZ):%d/%m/%Y %H:%M} — {v.violation_type}{note}")
    if len(vs) > MAX_LISTED_VIOLATIONS:
        lines.append(f"- … và {len(vs) - MAX_LISTED_VIOLATIONS} lỗi cũ hơn")
    return "\n".join(lines)


def lookup_text(db: Session, query: str) -> str:
    found = find_students(db, query)
    if not found:
        return f'Không tìm thấy học sinh nào khớp với "{query}".'
    head = "" if len(found) == 1 else f'Tìm thấy {len(found)} học sinh khớp với "{query}":\n\n'
    return head + "\n\n".join(format_student_report(db, s) for s in found)


@app.get("/chatbot/lookup")
def chatbot_lookup(q: str = Query(..., min_length=1, max_length=100), db: Session = Depends(get_db),
                   _user: dict = Depends(require_teacher)):
    """Tra cứu học sinh theo mã/tên: trả đúng dữ liệu trong DB, không qua AI nên không bịa."""
    return {"reply": lookup_text(db, q)}


# ── Chatbot (Groq) ───────────────────────────────────────────────────────────
def build_chat_context(db: Session, lookup: str = "") -> str:
    c = violation_counts(db)
    st = period_starts()
    top_of = lambda since: "\n".join(  # noqa: E731
        f"  {i}. {r.full_name} ({r.student_code} - {r.class_name}): {r.count} vi phạm"
        for i, r in enumerate(top_violators(db, 5, since), 1)) or "  (chưa có dữ liệu)"
    top_week, top_month, top_all = top_of(st["week"]), top_of(st["month"]), top_of(None)
    types = db.query(Violation.violation_type, func.count(Violation.id)).group_by(Violation.violation_type).all()
    type_list = "\n".join(f"  - {t}: {n} lần" for t, n in types) or "  (chưa có dữ liệu)"
    recent = "\n".join(
        f"  - {v.student.full_name if v.student else '?'} ({v.student.class_name if v.student else '?'}): "
        f"{v.violation_type} lúc "
        f"{(v.created_at if v.created_at.tzinfo else v.created_at.replace(tzinfo=timezone.utc)).astimezone(LOCAL_TZ):%d/%m/%Y %H:%M}"
        for v in db.query(Violation).order_by(Violation.created_at.desc()).limit(10).all()
    ) or "  (chưa có dữ liệu)"

    lookup_block = (f"\nKẾT QUẢ TRA CỨU HỌC SINH THEO MÃ (lấy trực tiếp từ cơ sở dữ liệu, chính xác tuyệt đối):\n{lookup}\n"
                    if lookup else "")

    return f"""Bạn là AI School Assistant — trợ lý thông minh của hệ thống quản lý học sinh THPT.

Thời gian hiện tại: {datetime.now(LOCAL_TZ):%d/%m/%Y %H:%M}

=== DỮ LIỆU THỰC TẾ HỆ THỐNG ===

TỔNG QUAN:
- Tổng học sinh: {c['total_students']}
- Vi phạm hôm nay: {c['today_violations']}
- Vi phạm tuần này: {c['week_violations']}
- Vi phạm tháng này: {c['month_violations']}
- Tổng vi phạm toàn thời gian: {c['total_violations']}

HỌC SINH VI PHẠM NHIỀU NHẤT TUẦN NÀY:
{top_week}

HỌC SINH VI PHẠM NHIỀU NHẤT THÁNG NÀY:
{top_month}

HỌC SINH VI PHẠM NHIỀU NHẤT TOÀN THỜI GIAN:
{top_all}

PHÂN LOẠI VI PHẠM:
{type_list}

VI PHẠM GẦN ĐÂY NHẤT:
{recent}
{lookup_block}
=== HƯỚNG DẪN ===
- Chỉ trả lời về quản lý học sinh, vi phạm, thống kê trường học
- Dùng số liệu thực tế ở trên, không bịa đặt, không suy diễn thêm
- Tiếng Việt, ngắn gọn, đi thẳng vào trọng tâm
- Không lặp lại câu hỏi, không mở đầu kiểu "Chào bạn", "Dựa trên dữ liệu trên..."
- Không thêm lời khuyên, nhận xét, hay diễn giải ngoài những gì được hỏi
- Dùng danh sách gạch đầu dòng khi liệt kê nhiều mục, không viết thành đoạn văn dài
- Khi có mục KẾT QUẢ TRA CỨU: chép đúng họ tên, mã, lớp và danh sách lỗi trong đó; nếu ghi "Không có lỗi vi phạm nào" thì trả lời học sinh đó không có lỗi; tuyệt đối không lấy dữ liệu của học sinh khác
- Nếu câu hỏi nằm ngoài phạm vi, từ chối trong 1 câu, không giải thích dài dòng"""


@app.post("/chatbot")
async def chatbot(req: ChatRequest, db: Session = Depends(get_db), _user: dict = Depends(require_teacher)):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY chưa được cấu hình trong file .env")

    last_user = next((m.content for m in reversed(req.messages) if m.role != "assistant"), "")
    codes = list(dict.fromkeys(re.sub(r"\s", "", c).upper() for c in CODE_IN_TEXT.findall(last_user)))[:3]
    lookup = "\n\n".join(lookup_text(db, c) for c in codes)

    messages = [{"role": "system", "content": build_chat_context(db, lookup)}] + [
        {"role": "assistant" if m.role == "assistant" else "user", "content": m.content}
        for m in req.messages[-20:]  # giới hạn lịch sử để không vượt giới hạn token / tốn phí
    ]
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                json={"model": GROQ_MODEL, "messages": messages, "max_tokens": 512, "temperature": 0.3},
                headers={"Authorization": f"Bearer {api_key}"}, timeout=30.0,
            )
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Không kết nối được dịch vụ AI. Kiểm tra mạng rồi thử lại.")
    if resp.status_code != 200:
        print(f"⚠️ Groq lỗi {resp.status_code}: {resp.text[:300]}")  # chi tiết chỉ ghi log server
        friendly = {429: "Chatbot đang quá tải hoặc đã hết lượt dùng, thử lại sau ít phút.",
                    401: "Khóa GROQ_API_KEY không hợp lệ — báo admin kiểm tra."}
        raise HTTPException(status_code=502, detail=friendly.get(resp.status_code, f"Chatbot tạm thời không phản hồi (mã {resp.status_code})."))
    try:
        return {"reply": resp.json()["choices"][0]["message"]["content"]}
    except (KeyError, IndexError, ValueError):
        raise HTTPException(status_code=502, detail="Groq trả về response không hợp lệ")


# ── Frontend (mount "/" SAU CÙNG để không che các route API ở trên) ──────────
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
