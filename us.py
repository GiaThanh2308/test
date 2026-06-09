from backend.database.db import SessionLocal, engine, Base
from backend.database.models import User
from backend.auth import hash_password
from sqlalchemy import text

# Ensure tables exist (creates missing tables)
Base.metadata.create_all(bind=engine)

# Ensure the users table has `hashed_password` column (SQLite ALTER if needed)
with engine.begin() as conn:
    res = conn.execute(text("PRAGMA table_info('users')")).fetchall()
    cols = [row[1] for row in res]
    if 'hashed_password' not in cols:
        conn.execute(text("ALTER TABLE users ADD COLUMN hashed_password VARCHAR"))

db = SessionLocal()

admin = User(
    username="admin",
    hashed_password=hash_password("123456"),
    role="admin"
)

db.add(admin)
db.commit()

print("Admin created")