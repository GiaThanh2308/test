
import argparse
import sys
import os

# Thêm thư mục gốc vào path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from backend.database.db import engine, SessionLocal
from backend.database.models import Base, User
from backend.auth import hash_password


def create_admin(username: str, password: str, role: str = "admin"):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            # Nếu đã tồn tại → cập nhật password sang bcrypt
            existing.hashed_password = hash_password(password)
            existing.role = role
            db.commit()
            print(f"✅ Đã cập nhật mật khẩu (bcrypt) cho user '{username}'")
        else:
            user = User(
                username        = username,
                hashed_password = hash_password(password),
                role            = role,
            )
            db.add(user)
            db.commit()
            print(f"✅ Đã tạo {role} '{username}' thành công")
    finally:
        db.close()


def migrate_all_users():

    print("⚠️  Để migrate user cũ, hãy dùng: python create_admin.py --username <tên> --password <mật khẩu mới>")
    print("    Lệnh này sẽ hash lại mật khẩu bằng bcrypt.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tạo hoặc cập nhật user")
    parser.add_argument("--username", default="admin",   help="Tên đăng nhập")
    parser.add_argument("--password", default=None,      help="Mật khẩu")
    parser.add_argument("--role",     default="admin",   help="Vai trò: admin / teacher")
    args = parser.parse_args()

    if not args.password:
        import getpass
        args.password = getpass.getpass(f"Nhập mật khẩu cho '{args.username}': ")

    if len(args.password) < 6:
        print("❌ Mật khẩu phải có ít nhất 6 ký tự")
        sys.exit(1)

    create_admin(args.username, args.password, args.role)
