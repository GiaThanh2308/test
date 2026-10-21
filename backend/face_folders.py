"""
face_folders.py — đọc thư mục known_faces MỘT LẦN, dựng chỉ mục trong RAM và
tự tạo hồ sơ học sinh còn thiếu. Không phụ thuộc FastAPI/SQLAlchemy.

Cấu trúc: known_faces / khoi 10 / 10A1 / Nguyen Van A / *.jpg
face_label = "Nguyen Van A_10A1"

Mã học sinh: HS + 2 số khối + 2 số lớp + số thứ tự trong sổ.
VD: lớp 12B01, STT 22  →  HS120122
"""
import os
import re
import unicodedata
import zlib
from typing import Optional

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp")


def normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


class FaceFolderIndex:
    """Tra cứu label → ảnh đại diện trong O(1), thay cho os.walk mỗi lần gọi."""

    def __init__(self, root: str):
        self.root = root
        self.by_person_class: dict[tuple[str, str], str] = {}
        self.by_folder: dict[str, str] = {}
        self.students: list[tuple[str, str]] = []  # (tên, lớp) theo cấu trúc khối/lớp/học sinh
        self._build()

    def _build(self):
        if not os.path.isdir(self.root):
            return
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames.sort()
            imgs = sorted(f for f in filenames if f.lower().endswith(IMAGE_EXTS))
            if not imgs:
                continue
            first = os.path.join(dirpath, imgs[0])
            folder = os.path.basename(dirpath)
            parent = os.path.basename(os.path.dirname(dirpath))
            self.by_person_class.setdefault((normalize(folder), normalize(parent)), first)
            self.by_folder.setdefault(normalize(folder), first)

            # đúng cấu trúc khối/lớp/học sinh (3 cấp dưới root) mới tạo hồ sơ
            rel = os.path.relpath(dirpath, self.root).split(os.sep)
            if len(rel) == 3 and normalize(rel[0]).startswith("khoi"):
                self.students.append((rel[2], rel[1]))

    def image_path(self, face_label: Optional[str]) -> Optional[str]:
        label = (face_label or "").strip()
        if not label:
            return None
        if "_" in label:
            person, cls = label.rsplit("_", 1)
            hit = self.by_person_class.get((normalize(person), normalize(cls)))
            if hit:
                return hit
            hit = self.by_folder.get(normalize(label))
            return hit or self.by_folder.get(normalize(person))
        return self.by_folder.get(normalize(label))


# ── Mã học sinh: HS + khối(2) + mã lớp(2) + STT ─────────────────────────────
# Mã luôn chỉ gồm CHỮ SỐ (chatbot tra cứu theo dạng HS\d{6,}). Hỗ trợ nhiều kiểu tên lớp:
#   10A1, 12B01, 10 A 3  → mã lớp = số cuối                    (HS1001, HS1201, HS1003)
#   10A                  → mã lớp = thứ tự chữ cái (A=01)       (HS1001)
#   10 Tin, 11CT, 10 Anh 1 → mã lớp 50–99 tính ổn định từ chữ   (HS1050…; không đụng 01–49 của lớp đánh số)
_CLASS_HEAD = re.compile(r"^\s*(\d{1,2})(.*)$")


def class_prefix(class_name: Optional[str]) -> str:
    """Tiền tố mã cho một lớp: 'HS' + khối(2 số) + mã lớp(2 số). Xác định, không phụ thuộc dữ liệu."""
    m = _CLASS_HEAD.match(class_name or "")
    khoi, rest = (int(m.group(1)), m.group(2)) if m else (0, class_name or "")
    letters = re.sub(r"[^a-z]", "", plain_text(rest))
    digits = re.findall(r"\d+", rest)
    number = int(digits[-1]) if digits else None

    if len(letters) <= 1 and number is not None:      # 10A1, 12B01, 10 A 3
        no = number % 100
    elif len(letters) == 1:                           # 10A
        no = ord(letters) - 96
    else:                                             # 10 Tin, 11CT, 10 Anh 1, "Chuyên Tin"
        no = 50 + (zlib.crc32(letters.encode()) + (number or 0)) % 50 if letters else 0
    return f"HS{khoi:02d}{no:02d}"


def plain_text(text: Optional[str]) -> str:
    """Bỏ dấu tiếng Việt (kể cả đ), chữ thường — chỉ dùng để sắp xếp tên."""
    return normalize((text or "").replace("đ", "d").replace("Đ", "D"))


def name_sort_key(full_name: Optional[str]) -> tuple[str, str]:
    """Thứ tự sổ điểm của Việt Nam: theo TÊN (từ cuối), rồi tới họ + tên đệm."""
    parts = plain_text(full_name).split()
    return (parts[-1] if parts else "", " ".join(parts[:-1]))


class CodeAllocator:
    """Cấp mã HS<khối><lớp><STT>. STT tiếp theo = số lớn nhất đang có của cùng tiền tố + 1,
    nên không bao giờ trùng mã đã có (kể cả mã nhập tay)."""

    def __init__(self, existing_codes):
        self.taken = {c for c in existing_codes if c}
        self._next: dict[str, int] = {}

    def _start(self, prefix: str) -> int:
        if prefix not in self._next:
            nums = [int(c[len(prefix):]) for c in self.taken
                    if c.startswith(prefix) and c[len(prefix):].isdigit()]
            self._next[prefix] = max(nums, default=0) + 1
        return self._next[prefix]

    def allocate(self, class_name: Optional[str]) -> str:
        prefix = class_prefix(class_name)
        n = self._start(prefix)
        code = f"{prefix}{n:02d}"
        while code in self.taken:
            n += 1
            code = f"{prefix}{n:02d}"
        self._next[prefix] = n + 1
        self.taken.add(code)
        return code


def sync_students(db, Student, index: FaceFolderIndex) -> dict:
    """Thêm học sinh còn thiếu và đổi mã AUTO_xxx cũ sang mã mới, bằng MỘT transaction.
    Chạy lại nhiều lần vẫn an toàn."""
    all_students = db.query(Student).all()
    labels = {s.face_label for s in all_students if s.face_label}
    pairs = {(s.full_name, s.class_name) for s in all_students}
    allocator = CodeAllocator(s.student_code for s in all_students)

    # (lớp, tên, học sinh cũ cần đổi mã | None nếu là học sinh mới)
    pending, skipped = [], []
    for s in all_students:
        if (s.student_code or "").startswith("AUTO_") or not s.student_code:
            pending.append((s.class_name, s.full_name, s))
    for name, cls in index.students:
        label = f"{name}_{cls}"
        if label in labels or (name, cls) in pairs:
            skipped.append(f"{name} ({cls}) — đã có hồ sơ")
            continue
        labels.add(label)
        pending.append((cls, name, None))

    # cấp STT theo thứ tự sổ: từng lớp, theo tên A→Z
    pending.sort(key=lambda p: (class_prefix(p[0]), name_sort_key(p[1])))
    created, recoded = [], []
    for cls, name, existing in pending:
        code = allocator.allocate(cls)
        if existing is not None:
            existing.student_code = code
            recoded.append(f"{name} ({cls}) → {code}")
        else:
            db.add(Student(student_code=code, full_name=name, class_name=cls,
                           face_label=f"{name}_{cls}", phone=""))
            created.append(f"{name} ({cls}) → {code}")

    errors = []
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        errors.append(str(e))
        created, recoded = [], []
    return {"created": created, "recoded": recoded, "skipped": skipped, "errors": errors}
