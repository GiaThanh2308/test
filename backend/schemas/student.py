from pydantic import BaseModel
from typing import Optional


class StudentCreate(BaseModel):
    student_code: str
    full_name: str
    class_name: str
    face_label: Optional[str] = None   # FIX: Optional — không bắt buộc nhập
    phone: str = ""
    parent_phone: str = ""
    plate_number: str = ""             # FIX: thêm trường bị thiếu


class StudentUpdate(BaseModel):        # FIX: class này hoàn toàn thiếu → server crash khi khởi động
    student_code: Optional[str] = None
    full_name: Optional[str] = None
    class_name: Optional[str] = None
    face_label: Optional[str] = None
    phone: Optional[str] = None
    parent_phone: Optional[str] = None
    plate_number: Optional[str] = None


class ViolationCreate(BaseModel):
    student_id: int
    violation_type: str
    note: str = ""
    image_path: str = ""


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


