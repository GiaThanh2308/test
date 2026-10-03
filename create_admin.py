"""Tạo hoặc cập nhật tài khoản.

    python create_admin.py --username hs01 --password MatKhau123 --role student
    python create_admin.py                      # hỏi mật khẩu cho 'admin'
"""
import argparse
import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

from backend.auth import hash_password  # noqa: E402
from backend.database.db import SessionLocal, engine  # noqa: E402
from backend.database.models import Base, User  # noqa: E402

ROLES = ("admin", "teacher", "student")


def create_admin(username: str, password: str, role: str = "admin"):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user:
            user.hashed_password, user.role = hash_password(password), role
            print(f"✅ Đã cập nhật mật khẩu và vai trò ({role}) cho '{username}'")
        else:
            db.add(User(username=username, hashed_password=hash_password(password), role=role))
            print(f"✅ Đã tạo {role} '{username}'")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tạo hoặc cập nhật user")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default=os.getenv("ADMIN_PASSWORD"), help="Mật khẩu (mặc định lấy từ ADMIN_PASSWORD)")
    parser.add_argument("--role", default="admin", choices=ROLES)
    args = parser.parse_args()

    password = args.password or getpass.getpass(f"Nhập mật khẩu cho '{args.username}': ")
    if len(password) < 6:
        sys.exit("❌ Mật khẩu phải có ít nhất 6 ký tự")
    create_admin(args.username, password, args.role)
