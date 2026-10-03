"""Kết nối SQLite. (Tuỳ chọn) đồng bộ school.db với Hugging Face Dataset khi đặt HF_TOKEN + HF_DATASET_REPO."""
import os
import shutil

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("DB_PATH", os.path.join(_BASE_DIR, "school.db"))

HF_TOKEN        = os.getenv("HF_TOKEN", "")
HF_DATASET_REPO = os.getenv("HF_DATASET_REPO", "")  # vd: GiaThanh/KHKT-database
DB_FILENAME     = "school.db"


def _hf_enabled() -> bool:
    return bool(HF_TOKEN and HF_DATASET_REPO)


def pull_db():
    """Tải school.db từ HF Dataset về (chỉ khi đã cấu hình HF)."""
    if not _hf_enabled():
        return
    try:
        from huggingface_hub import hf_hub_download
        path = hf_hub_download(repo_id=HF_DATASET_REPO, filename=DB_FILENAME,
                               repo_type="dataset", token=HF_TOKEN, local_dir=_BASE_DIR)
        if os.path.abspath(path) != os.path.abspath(DB_PATH):
            shutil.copy(path, DB_PATH)
        print(f"✅ Đã tải database từ HF Dataset ({HF_DATASET_REPO})")
    except ImportError:
        print("⚠️ Chưa cài huggingface_hub — bỏ qua đồng bộ HF")
    except Exception as e:
        print(f"ℹ️ Không tải được DB từ HF (có thể chưa có): {e}")


def push_db():
    """Đẩy school.db lên HF Dataset (không làm gì nếu chưa cấu hình HF)."""
    if not _hf_enabled() or not os.path.exists(DB_PATH):
        return
    try:
        from huggingface_hub import HfApi
        HfApi(token=HF_TOKEN).upload_file(
            path_or_fileobj=DB_PATH, path_in_repo=DB_FILENAME,
            repo_id=HF_DATASET_REPO, repo_type="dataset", commit_message="Auto-sync school.db",
        )
        print("✅ Đã đẩy database lên HF Dataset")
    except ImportError:
        pass
    except Exception as e:
        print(f"⚠️ Không đẩy được DB lên HF: {e}")


pull_db()  # chạy lúc import, trước khi mở kết nối

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
