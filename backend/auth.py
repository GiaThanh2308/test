"""auth.py — mật khẩu (bcrypt) + JWT + kiểm tra quyền."""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
if not SECRET_KEY or SECRET_KEY.startswith("doi-chuoi-bi-mat"):
    raise RuntimeError("JWT_SECRET_KEY chưa được đặt (hoặc còn là giá trị mẫu) trong file .env")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 giờ
TEACHER_ROLES = ("admin", "teacher")

pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return jwt.encode({**data, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Trả về {"username", "role"} của người đang đăng nhập."""
    payload = decode_token(token)
    if not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Token thiếu thông tin user")
    return {"username": payload["sub"], "role": payload.get("role")}


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ admin mới có quyền này")
    return current_user


def require_teacher(current_user: dict = Depends(get_current_user)) -> dict:
    """admin/teacher mới qua; student (hoặc role lạ/thiếu) bị 403."""
    if current_user["role"] not in TEACHER_ROLES:
        raise HTTPException(status_code=403, detail="Tài khoản của bạn không có quyền này")
    return current_user
