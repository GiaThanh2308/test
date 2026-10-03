"""FaceDatabase — lưu/đọc embedding khuôn mặt đã biết (file pickle)."""
import os
import pickle
from datetime import datetime

import numpy as np


class FaceDatabase:
    def __init__(self, database_path: str = "face_database.pkl"):
        self.database_path = database_path
        self.known_encodings: list = []  # vector trung bình mỗi người
        self.known_names: list[str] = []
        self.face_metadata: dict = {}    # tên -> {"embeddings": [...], "added": ..., "num_images": ...}
        self.load_database()

    def load_database(self):
        if not os.path.exists(self.database_path):
            print(f"⚠️ Không tìm thấy database tại: {self.database_path}")
            return
        try:
            with open(self.database_path, "rb") as f:
                data = pickle.load(f)
            self.known_encodings = data.get("encodings", [])
            self.known_names     = data.get("names", [])
            self.face_metadata   = data.get("metadata", {})
            print(f"📂 Đã tải database: {len(self.known_names)} người từ {self.database_path}")
        except Exception as e:
            print(f"⚠️ Không đọc được database: {e}. Sẽ tạo mới.")
            self.known_encodings, self.known_names, self.face_metadata = [], [], {}

    def save_database(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.database_path)), exist_ok=True)
        tmp = self.database_path + ".tmp"
        with open(tmp, "wb") as f:  # ghi file tạm rồi đổi tên: mất điện giữa chừng không hỏng DB
            pickle.dump({
                "encodings": self.known_encodings,
                "names":     self.known_names,
                "metadata":  self.face_metadata,
            }, f)
        os.replace(tmp, self.database_path)
        print(f"💾 Đã lưu database: {len(self.known_names)} người → {self.database_path}")

    def set_person(self, name: str, embeddings) -> bool:
        """Thêm hoặc thay thế một người. Không tự lưu — gọi save_database() sau khi thêm xong."""
        if len(embeddings) == 0:
            return False
        mean_vec  = np.mean(embeddings, axis=0)
        mean_vec /= np.linalg.norm(mean_vec) + 1e-10
        mean_vec  = mean_vec.astype(np.float32)

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
