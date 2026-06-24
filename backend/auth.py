"""
auth.py — Xác thực: hash mật khẩu (bcrypt) + JWT token
Cài đặt thêm: pip install passlib[bcrypt] python-jose[cryptography]
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
load_dotenv()
# ── Cấu hình ──────────────────────────────────────────────────
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "CHANGE_THIS_SECRET_IN_ENV")  # đặt trong .env!
if SECRET_KEY == "CHANGE_THIS_SECRET_IN_ENV":
    raise RuntimeError(
        "JWT_SECRET_KEY chưa được cấu hình trong .env"
    )
ALGORITHM  = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 giờ

pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


# ── Password helpers ──────────────────────────────────────────
def hash_password(plain: str) -> str:
    """Hash mật khẩu trước khi lưu vào DB."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Kiểm tra mật khẩu nhập vào có khớp hash không."""
    return pwd_context.verify(plain, hashed)


# ── JWT helpers ───────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Giải mã token, raise nếu không hợp lệ."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Dependency: lấy user hiện tại từ token ───────────────────
def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Dùng làm Depends() trong các route cần đăng nhập.
    Trả về dict {"username": ..., "role": ...}
    """
    payload = decode_token(token)
    username = payload.get("sub")
    role     = payload.get("role")
    if not username:
        raise HTTPException(status_code=401, detail="Token thiếu thông tin user")
    return {"username": username, "role": role}


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Chỉ cho phép admin. Dùng Depends(require_admin) trên route nhạy cảm."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Chỉ admin mới có quyền này")
    return current_user


