"""FaceDatabase — lưu/đọc embedding khuôn mặt đã biết.

Định dạng mới: file .npz của NumPy (mảng thuần, đọc với allow_pickle=False nên không thể chạy mã độc).
Tự chuyển đổi một lần từ file .pickle cũ (face_database.pkl) nếu có — file cũ được giữ nguyên.
"""
import os
import pickle
from datetime import datetime

import numpy as np

from core.FaissIndex import l2_normalize


def _mean_vector(embeddings) -> np.ndarray:
    return l2_normalize(np.mean(np.vstack(embeddings), axis=0))[0]


class FaceDatabase:
    def __init__(self, database_path: str = "face_database.npz"):
        root, ext = os.path.splitext(database_path)
        # .env cũ có thể vẫn trỏ tới .pkl: dùng .npz cùng tên, còn .pkl chỉ để chuyển đổi
        self.database_path = root + ".npz"
        self.legacy_path = database_path if ext.lower() == ".pkl" else root + ".pkl"
        self.known_encodings: list = []  # vector trung bình mỗi người
        self.known_names: list[str] = []
        self.face_metadata: dict = {}    # tên -> {"embeddings": [...], "added": ..., "num_images": ...}
        self.load_database()

    # ── Đọc ──────────────────────────────────────────────────
    def load_database(self):
        if os.path.exists(self.database_path):
            try:
                self._load_npz(self.database_path)
                print(f"📂 Đã tải database: {len(self.known_names)} người từ {self.database_path}")
                return
            except Exception as e:
                print(f"⚠️ Không đọc được database {self.database_path}: {e}")
                self.clear()
                return
        if os.path.exists(self.legacy_path):
            self._migrate_from_pickle()
            return
        print(f"⚠️ Không tìm thấy database tại: {self.database_path}")

    def _load_npz(self, path: str):
        with np.load(path, allow_pickle=False) as z:
            names, counts = [str(n) for n in z["names"]], z["counts"].astype(int)
            added, emb = [str(a) for a in z["added"]], z["embeddings"].astype(np.float32)
        if counts.sum() != len(emb) or len(names) != len(counts):
            raise ValueError("file embedding không khớp (có thể bị hỏng)")
        self.clear()
        pos = 0
        for name, n, when in zip(names, counts, added):
            vecs = [emb[pos + i] for i in range(n)]
            pos += n
            self.known_names.append(name)
            self.known_encodings.append(_mean_vector(vecs))
            self.face_metadata[name] = {"embeddings": vecs, "added": when, "num_images": int(n)}

    def _migrate_from_pickle(self):
        """Chạy đúng một lần: đọc file pickle CŨ CỦA CHÍNH BẠN rồi ghi sang .npz. Sau đó pickle không còn được dùng."""
        try:
            with open(self.legacy_path, "rb") as f:
                data = pickle.load(f)  # noqa: S301 — chỉ cho file cũ do hệ thống này tạo ra
            names, enc, meta = data.get("names", []), data.get("encodings", []), data.get("metadata", {})
            self.clear()
            for i, name in enumerate(names):
                vecs = [np.asarray(v, dtype=np.float32) for v in meta.get(name, {}).get("embeddings", [])]
                if not vecs and i < len(enc):  # database rất cũ: chỉ có vector trung bình
                    vecs = [np.asarray(enc[i], dtype=np.float32)]
                if vecs:
                    self.set_person(name, vecs)
                    if "added" in meta.get(name, {}):
                        self.face_metadata[name]["added"] = meta[name]["added"]
            self.save_database()
            print(f"🔁 Đã chuyển {len(self.known_names)} người từ {self.legacy_path} sang {self.database_path}. "
                  f"File pickle cũ được giữ nguyên, có thể xoá sau khi kiểm tra.")
        except Exception as e:
            print(f"⚠️ Không chuyển đổi được database cũ ({self.legacy_path}): {e}. Sẽ tạo mới.")
            self.clear()

    # ── Ghi ──────────────────────────────────────────────────
    def save_database(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.database_path)), exist_ok=True)
        names = list(self.known_names)
        groups = [self.face_metadata[n]["embeddings"] for n in names]
        emb = (np.vstack([np.vstack(g) for g in groups]).astype(np.float32)
               if groups else np.zeros((0, 512), dtype=np.float32))
        tmp = self.database_path + ".tmp"
        with open(tmp, "wb") as f:  # ghi file tạm rồi đổi tên: mất điện giữa chừng không hỏng DB
            np.savez_compressed(
                f,
                names=np.array(names, dtype=str),
                counts=np.array([len(g) for g in groups], dtype=np.int64),
                added=np.array([str(self.face_metadata[n].get("added", "")) for n in names], dtype=str),
                embeddings=emb,
            )
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.database_path)
        print(f"💾 Đã lưu database: {len(self.known_names)} người → {self.database_path}")

    def set_person(self, name: str, embeddings) -> bool:
        """Thêm hoặc thay thế một người. Không tự lưu — gọi save_database() sau khi thêm xong."""
        if len(embeddings) == 0:
            return False
        mean_vec = _mean_vector(embeddings)
        if name in self.known_names:  # trước đây trùng tên sẽ bị thêm 2 lần
            self.known_encodings[self.known_names.index(name)] = mean_vec
        else:
            self.known_names.append(name)
            self.known_encodings.append(mean_vec)
        self.face_metadata[name] = {
            "embeddings": [np.asarray(e, dtype=np.float32) for e in embeddings],
            "added":      datetime.now().isoformat(),
            "num_images": len(embeddings),
        }
        return True

    def clear(self):
        self.known_encodings, self.known_names, self.face_metadata = [], [], {}
