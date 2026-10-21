"""Làm sạch dữ liệu đưa vào chatbot (chống prompt injection). Không phụ thuộc FastAPI/DB nên kiểm thử được."""
import re
import unicodedata

MAX_USER_CHARS = 1000       # một tin của người dùng
MAX_ASSISTANT_CHARS = 1500  # một tin "assistant" trong lịch sử (do trình duyệt gửi lên nên KHÔNG đáng tin)
MAX_HISTORY = 10            # số tin gần nhất giữ lại
MAX_NOTE_CHARS = 120        # ghi chú vi phạm đưa vào prompt

# Ký tự điều khiển (trừ xuống dòng/tab), ký tự ẩn và ký tự đảo chiều văn bản thường dùng để giấu chỉ thị
_INVISIBLE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f​-‏‪-‮⁠-⁤⁦-⁩﻿]")
# Dòng giả danh vai trò hệ thống / ranh giới dữ liệu
_FAKE_ROLE = re.compile(r"(?im)^\s*(system|assistant|developer|hệ thống|quản trị)\s*[:：]")
_DELIMS = re.compile(r"</?\s*du_lieu\s*>", re.IGNORECASE)


def sanitize(text, limit: int) -> str:
    s = unicodedata.normalize("NFC", str(text or ""))
    s = _INVISIBLE.sub("", s)
    s = _DELIMS.sub("", s)
    s = _FAKE_ROLE.sub(lambda m: m.group(0).replace(":", " -").replace("：", " -"), s)
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    return s[:limit]


def one_line(text, limit: int = MAX_NOTE_CHARS) -> str:
    """Dữ liệu do người khác nhập (ghi chú, tên...) được ép thành một dòng ngắn trước khi đưa vào prompt."""
    s = sanitize(text, limit * 3)
    s = re.sub(r"\s+", " ", s).replace("`", "'").replace("<", "‹").replace(">", "›")
    return s[:limit]


def clean_history(messages) -> list[dict]:
    """Chỉ nhận vai trò user/assistant, cắt độ dài, giữ MAX_HISTORY tin cuối, bắt đầu bằng tin của user."""
    out = []
    for m in messages[-MAX_HISTORY:]:
        role = "assistant" if getattr(m, "role", "") == "assistant" else "user"
        limit = MAX_ASSISTANT_CHARS if role == "assistant" else MAX_USER_CHARS
        content = sanitize(getattr(m, "content", ""), limit)
        if content:
            out.append({"role": role, "content": content})
    while out and out[0]["role"] != "user":
        out.pop(0)
    return out
