from typing import Optional

from pydantic import BaseModel, Field


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
    violation_types: list[str] = Field(min_length=1, max_length=10)  # chọn 1 hoặc nhiều lỗi có sẵn
    note: str = Field(default="", max_length=500)
    capture: Optional[str] = None  # tên ảnh chụp do /recognize-face trả về


class ChatMessage(BaseModel):
    role: str = Field(max_length=20)
    content: str = Field(max_length=2000)  # trình duyệt cắt 1000 ký tự; server chặn cứng ở đây


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=50)


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "teacher"
