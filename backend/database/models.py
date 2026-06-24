from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.database.db import Base

def utcnow():
    """Trả về datetime UTC có timezone (aware) — tránh lỗi so sánh với query."""
    return datetime.now(timezone.utc)


class Student(Base):
    __tablename__ = "students"

    id           = Column(Integer, primary_key=True, index=True)
    student_code = Column(String, unique=True, index=True)
    full_name    = Column(String, nullable=False)
    class_name   = Column(String)
    # FIX: nullable=True + unique chỉ áp dụng khi có giá trị (None không bị unique check trong SQLite)
    face_label   = Column(String, unique=True, nullable=True, default=None)
    phone        = Column(String, default="")
    parent_phone = Column(String, default="")
    plate_number = Column(String, default="", index=True)
    # FIX: dùng utcnow() thay datetime.utcnow (naive) để tránh timezone mismatch
    created_at   = Column(DateTime(timezone=True), default=utcnow)

    violations = relationship("Violation", back_populates="student", cascade="all, delete")


class User(Base):
    __tablename__ = "users"

    id           = Column(Integer, primary_key=True, index=True)
    username     = Column(String, unique=True, index=True)
    # FIX: đổi tên cột thành hashed_password để tránh nhầm lẫn — lưu hash bcrypt
    hashed_password = Column(String)
    role         = Column(String, default="teacher")


class Violation(Base):
    __tablename__ = "violations"

    id             = Column(Integer, primary_key=True, index=True)
    student_id     = Column(Integer, ForeignKey("students.id"), nullable=False)
    violation_type = Column(String, nullable=False)
    note           = Column(Text, default="")
    image_path     = Column(String, default="")
    # FIX: timezone-aware
    created_at     = Column(DateTime(timezone=True), default=utcnow)

    student = relationship("Student", back_populates="violations")


