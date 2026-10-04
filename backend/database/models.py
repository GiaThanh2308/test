from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.database.db import Base


def utcnow() -> datetime:
    """Giờ UTC có múi giờ (aware)."""
    return datetime.now(timezone.utc)


class Student(Base):
    __tablename__ = "students"

    id           = Column(Integer, primary_key=True, index=True)
    student_code = Column(String, unique=True, index=True)
    full_name    = Column(String, nullable=False)
    class_name   = Column(String, index=True)
    face_label   = Column(String, unique=True, nullable=True, default=None)  # khớp tên trong face_database.pkl
    phone        = Column(String, default="")
    created_at   = Column(DateTime(timezone=True), default=utcnow)

    violations = relationship("Violation", back_populates="student", cascade="all, delete")


class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    username        = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role            = Column(String, default="teacher")  # admin | teacher | student


class Violation(Base):
    __tablename__ = "violations"

    id             = Column(Integer, primary_key=True, index=True)
    student_id     = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    violation_type = Column(String, nullable=False)
    note           = Column(Text, default="")
    created_at     = Column(DateTime(timezone=True), default=utcnow, index=True)

    student = relationship("Student", back_populates="violations")
class IgnoredLabel(Base):
    """Nhãn khuôn mặt của học sinh đã bị xóa — để "Đồng bộ lại" không tạo lại hồ sơ."""
    __tablename__ = "ignored_labels"

    id    = Column(Integer, primary_key=True)
    label = Column(String, unique=True, index=True, nullable=False)
