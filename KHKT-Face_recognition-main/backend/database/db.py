import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# FIX: dùng absolute path dựa trên vị trí file này — tránh lỗi khi chạy từ thư mục khác
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = f"sqlite:///{os.path.join(_BASE_DIR, 'school.db')}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()
