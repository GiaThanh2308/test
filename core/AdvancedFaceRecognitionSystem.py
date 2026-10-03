"""AdvancedFaceRecognitionSystem — phát hiện + nhận diện khuôn mặt (InsightFace + FAISS)."""
import os

import cv2
import numpy as np
from insightface.app import FaceAnalysis

from core.FaceDatabase import FaceDatabase
from core.FaissIndex import FaissIndex

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp")


def _read_image(path: str):
    """Đọc ảnh kể cả đường dẫn có dấu tiếng Việt (cv2.imread không đọc được trên Windows)."""
    return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)


def iter_people(main_dir: str):
    """Duyệt known_faces ở mọi độ sâu: thư mục nào có ảnh = 1 người.
    Trả về (nhãn, thư mục, danh sách ảnh); nhãn = "<tên>_<lớp>" (lớp = thư mục cha)."""
    for root, dirs, files in os.walk(main_dir):
        dirs.sort()
        images = sorted(f for f in files if f.lower().endswith(IMAGE_EXTS))
        if images:
            person = os.path.basename(root)
            cls    = os.path.basename(os.path.dirname(root))
            yield f"{person}_{cls}", root, images


class AdvancedFaceRecognitionSystem:
    def __init__(self, database_path: str = "face_database.pkl"):
        self.database    = FaceDatabase(database_path=database_path)
        self.app         = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        self.app.prepare(ctx_id=0, det_size=(480, 480))
        self.faiss_index = FaissIndex(dim=512)

    # ── Index ────────────────────────────────────────────────
    def build_ann_index(self):
        """Dựng FAISS từ TẤT CẢ embedding gốc của mỗi người (chính xác hơn vector trung bình)."""
        embs, names = [], []
        for name, info in self.database.face_metadata.items():
            for vec in info.get("embeddings", []):
                embs.append(vec)
                names.append(name)

        if not embs:  # database cũ không có metadata → dùng vector trung bình
            embs, names = list(self.database.known_encodings), list(self.database.known_names)
        if not embs:
            print("⚠️ Chưa có dữ liệu khuôn mặt để tạo index.")
            return
        self.faiss_index.build_index(embs, names)

    # ── Xây / cập nhật database từ ảnh ───────────────────────
    def _embeddings_from_images(self, folder: str, images) -> list:
        encs = []
        for fn in images:
            path = os.path.join(folder, fn)
            img = _read_image(path)
            if img is None:
                print(f"❌ Không đọc được ảnh: {path}")
                continue
            faces = self.app.get(img)
            if not faces:
                print(f"⚠️ Không phát hiện khuôn mặt: {path}")
            encs.extend(f.embedding for f in faces)
        return encs

    def build_database_from_images(self, main_dir: str = "known_faces"):
        """Tạo lại TOÀN BỘ database từ thư mục ảnh (ghi đè)."""
        print("🧠 Đang tạo database khuôn mặt từ ảnh...")
        people = {}
        for label, folder, images in iter_people(main_dir):
            print(f"🔍 Đang xử lý: {label}")
            encs = self._embeddings_from_images(folder, images)
            if encs:
                people[label] = encs
            else:
                print(f"❌ {label}: không có khuôn mặt hợp lệ")
        if not people:
            print("❌ Không có dữ liệu khuôn mặt nào được tạo! (giữ nguyên database cũ)")
            return
        self.database.clear()
        for label, encs in people.items():
            self.database.set_person(label, encs)
        self.database.save_database()
        self.build_ann_index()

    def rescan_known_faces(self, main_dir: str = "known_faces") -> list[str]:
        """Chỉ thêm những người CHƯA có trong database. Trả về danh sách nhãn mới.
        (Bản cũ giả định cấu trúc 2 cấp lớp/học sinh nên với khối/lớp/học sinh sẽ đặt nhãn sai.)"""
        known, added = set(self.database.known_names), []
        for label, folder, images in iter_people(main_dir):
            if label in known:
                continue
            if self.database.set_person(label, self._embeddings_from_images(folder, images)):
                added.append(label)
                print(f"✅ Đã thêm {label}")
        if added:
            self.database.save_database()
            self.build_ann_index()
        else:
            print("📂 Không có người mới nào được thêm.")
        return added

    # ── Nhận diện ────────────────────────────────────────────
    def _match(self, face):
        emb = face.embedding.copy()
        emb /= np.linalg.norm(emb) + 1e-10
        return self.faiss_index.search(emb)

    def recognize_image(self, img) -> list[dict]:
        results = []
        for face in self.app.get(img):
            name, score = self._match(face)
            results.append({"name": name, "score": float(score)})
        return results

    def process_frame(self, frame):
        """Vẽ khung + tên lên frame (dùng cho chế độ camera trên máy tính, main.py)."""
        for face in self.app.get(frame):
            x1, y1, x2, y2 = face.bbox.astype(int)
            name, score = self._match(face)
            color = (0, 255, 0) if name != "unknown" else (0, 0, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{name} ({score:.2f})", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        return frame
