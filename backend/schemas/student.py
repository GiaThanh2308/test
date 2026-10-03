from typing import Optional

from pydantic import BaseModel


class StudentCreate(BaseModel):
    student_code: Optional[str] = None  # để trống → tự cấp HS<khối><lớp><STT>
    full_name: str
    class_name: str
    face_label: Optional[str] = None
    phone: str = ""


class StudentUpdate(BaseModel):
    student_code: Optional[str] = None
    full_name: Optional[str] = None
    class_name: Optional[str] = None
    face_label: Optional[str] = None
    phone: Optional[str] = None


class ViolationCreate(BaseModel):
    student_id: int
    violation_type: str
    note: str = ""


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "teacher"
