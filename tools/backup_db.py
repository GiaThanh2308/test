"""Sao lưu school.db an toàn (dùng API backup của SQLite, không chép file đang ghi).

    python tools/backup_db.py

Mặc định lưu vào data/backups/, giữ BACKUP_KEEP bản mới nhất (14). Đặt BACKUP_DIR sang ổ khác để an toàn hơn.
Chạy mỗi đêm bằng Windows Task Scheduler (xem README).
"""
import os
import sqlite3
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.abspath(os.getenv("DATA_DIR", os.path.join(ROOT, "data")))
DB_PATH = os.path.abspath(os.getenv("DB_PATH", os.path.join(DATA_DIR, "school.db")))
BACKUP_DIR = os.path.abspath(os.getenv("BACKUP_DIR", os.path.join(DATA_DIR, "backups")))
KEEP = int(os.getenv("BACKUP_KEEP", "14"))


def main():
    if not os.path.exists(DB_PATH):
        sys.exit(f"❌ Không thấy database: {DB_PATH}")
    os.makedirs(BACKUP_DIR, exist_ok=True)
    dest = os.path.join(BACKUP_DIR, f"school_{datetime.now():%Y%m%d_%H%M%S}.db")

    src = sqlite3.connect(DB_PATH)
    dst = sqlite3.connect(dest)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()

    check = sqlite3.connect(dest)
    try:
        ok = check.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        check.close()
    if ok != "ok":
        os.remove(dest)
        sys.exit(f"❌ Bản sao lưu bị lỗi ({ok}), đã xoá")

    backups = sorted(f for f in os.listdir(BACKUP_DIR) if f.startswith("school_") and f.endswith(".db"))
    for old in backups[:-KEEP]:
        os.remove(os.path.join(BACKUP_DIR, old))
    print(f"✅ Đã sao lưu -> {dest} (giữ {min(len(backups), KEEP)} bản)")


if __name__ == "__main__":
    main()
