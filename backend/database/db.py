"""Kết nối SQLite (chạy local). Dữ liệu nằm ở <dự án>/data/school.db, tách khỏi mã nguồn."""
import os
import shutil

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_BASE_DIR))

DATA_DIR = os.path.abspath(os.getenv("DATA_DIR", os.path.join(_PROJECT_ROOT, "data")))
DB_PATH = os.path.abspath(os.getenv("DB_PATH", os.path.join(DATA_DIR, "school.db")))
_LEGACY_DB_PATH = os.path.join(_BASE_DIR, "school.db")  # vị trí cũ: backend/database/school.db

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Lần chạy đầu sau khi nâng cấp: COPY (không xoá) DB cũ sang vị trí mới để không mất dữ liệu thật.
if not os.path.exists(DB_PATH) and os.path.exists(_LEGACY_DB_PATH) and _LEGACY_DB_PATH != DB_PATH:
    shutil.copy2(_LEGACY_DB_PATH, DB_PATH)
    print(f"📦 Đã chép database cũ {_LEGACY_DB_PATH} -> {DB_PATH} (file cũ được giữ nguyên)")

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False, "timeout": 30})


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_conn, _record):
    """WAL: nhiều cờ đỏ ghi cùng lúc không khoá nhau; đọc không chặn ghi."""
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA busy_timeout=30000")
    cur.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def migrate():
    """Thêm cột mới vào DB đang chạy thật (create_all không tự thêm cột vào bảng có sẵn)."""
    insp = inspect(engine)
    tables = insp.get_table_names()
    wanted = {"violations": (("recorded_by", "VARCHAR"), ("capture_path", "VARCHAR")),
              "students": (("graduated_at", "DATETIME"),)}
    for table, columns in wanted.items():
        if table not in tables:
            continue
        have = {c["name"] for c in insp.get_columns(table)}
        for name, sql_type in columns:
            if name not in have:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}"))
                print(f"🛠️ Đã thêm cột {table}.{name}")
