import cv2, os, numpy as np
from insightface.app import FaceAnalysis
from core.FaceDatabase import FaceDatabase
from core.FaissIndex import FaissIndex
from datetime import datetime


class AdvancedFaceRecognitionSystem:
    def __init__(self):
        self.database    = FaceDatabase()
        self.app         = FaceAnalysis(name="buffalo_l")
        self.app.prepare(ctx_id=0, det_size=(480, 480))
        self.faiss_index = FaissIndex(dim=512)
        # FIX: không gọi load_database() ở đây vì FaceDatabase.__init__ đã tự gọi rồi

    def build_ann_index(self):
        if len(self.database.known_encodings) == 0:
            print("⚠️ Chưa có dữ liệu khuôn mặt để tạo index.")
            return

        all_embs  = []
        all_names = []
        for name, info in self.database.face_metadata.items():
            if "embeddings" in info:
                for vec in info["embeddings"]:
                    all_embs.append(vec)
                    all_names.append(name)

        if not all_embs:
            all_embs  = self.database.known_encodings
            all_names = self.database.known_names

        if not all_embs:
            print("⚠️ Không có embeddings để tạo ANN index.")
            return

        self.faiss_index.build_index(all_embs, all_names)
        print(f"✅ FAISS index rebuilt từ {len(all_embs)} vectors của {len(set(all_names))} người")

    def add_person(self, name, folder_path):
        if not os.path.exists(folder_path):
            print(f"❌ Không tìm thấy thư mục: {folder_path}")
            return

        encs = []
        for fn in os.listdir(folder_path):
            if not fn.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            img_path = os.path.join(folder_path, fn)
            img = cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                print(f"⚠️ Không đọc được ảnh: {img_path}")
                continue
            faces = self.app.get(img)
            for f in faces:
                encs.append(f.embedding)

        if not encs:
            print(f"⚠️ Không tìm thấy khuôn mặt hợp lệ trong thư mục {folder_path}")
            return

        mean_vec  = np.mean(encs, axis=0)
        mean_vec /= np.linalg.norm(mean_vec) + 1e-10
        self.database.known_names.append(name)
        self.database.known_encodings.append(mean_vec.astype(np.float32))
        self.database.face_metadata[name] = {
            "embeddings": [e.astype(np.float32) for e in encs],
            "added":      datetime.now().isoformat(),
            "num_images": len(encs)
        }
        self.database.save_database()
        self.faiss_index.build_index(self.database.known_encodings, self.database.known_names)
        print(f"✅ Đã thêm {name} vào database ({len(encs)} ảnh)")

    def rescan_known_faces(self, main_dir="known_faces"):
        known_set = set(self.database.known_names)
        new_people = []
        for class_name in os.listdir(main_dir):

            class_path = os.path.join(main_dir, class_name)

            if not os.path.isdir(class_path):
                continue

            for person_name in os.listdir(class_path):

                folder = os.path.join(class_path, person_name)

                if not os.path.isdir(folder):
                    continue

                label_name = f"{person_name}_{class_name}"

                if label_name in known_set:
                    continue

                encs = []

                for fn in os.listdir(folder):

                    if not fn.lower().endswith(
                        (".jpg", ".jpeg", ".png")
                    ):
                        continue

                    img_path = os.path.join(folder, fn)

                    img = cv2.imdecode(
                        np.fromfile(
                            img_path,
                            dtype=np.uint8
                        ),
                        cv2.IMREAD_COLOR
                    )

                    if img is None:
                        continue

                    faces = self.app.get(img)

                    for f in faces:
                        encs.append(f.embedding)

                if encs:

                    mean_vec = np.mean(encs, axis=0)
                    mean_vec /= np.linalg.norm(mean_vec) + 1e-10

                    self.database.known_names.append(
                        label_name
                    )

                    self.database.known_encodings.append(
                        mean_vec.astype(np.float32)
                    )

                    self.database.face_metadata[label_name] = {
                        "embeddings": [
                            e.astype(np.float32)
                            for e in encs
                        ],
                        "added": datetime.now().isoformat(),
                        "num_images": len(encs)
                    }

                    new_people.append(label_name)

                    print(
                        f"✅ Đã thêm {label_name}"
                    )

        if new_people:
            self.database.save_database()
            self.faiss_index.build_index(self.database.known_encodings, self.database.known_names)
            print(f"💾 Database cập nhật với {len(new_people)} người mới.")
        else:
            print("📂 Không có người mới nào được thêm.")

    def build_database_from_images(self, main_dir="known_faces"):
        print("🧠 Đang tạo database khuôn mặt từ ảnh...")
        people = []

        for root, dirs, files in os.walk(main_dir):

            image_files = [
                f for f in files
                if f.lower().endswith((".jpg", ".jpeg", ".png"))
            ]

            # Chỉ xử lý các thư mục thực sự chứa ảnh
            if not image_files:
                continue

            person_name = os.path.basename(root)

            # Ví dụ:
            # root = known_faces/Khối 10/10A1/Nguyễn Văn A
            # class_name = 10A1
            class_name = os.path.basename(os.path.dirname(root))

            label_name = f"{person_name}_{class_name}"
            encodings = []

            print(f"🔍 Đang xử lý: {label_name}")

            for filename in image_files:
                img_path = os.path.join(root, filename)

                img = cv2.imdecode(
                    np.fromfile(img_path, dtype=np.uint8),
                    cv2.IMREAD_COLOR
                )

                if img is None:
                    print("❌ Không đọc được ảnh:", img_path)
                    continue

                faces = self.app.get(img)

                if len(faces) == 0:
                    print("⚠️ Không phát hiện khuôn mặt:", img_path)
                    continue

                for face in faces:
                    encodings.append(face.embedding)

            if encodings:
                mean_encoding = np.mean(encodings, axis=0)
                mean_encoding /= (np.linalg.norm(mean_encoding) + 1e-10)

                people.append(
                    (label_name, mean_encoding.astype(np.float32))
                )

                print(
                    f"✅ {label_name}: {len(encodings)} ảnh → lưu 1 vector"
                )
            else:
                print(
                    f"❌ {label_name}: không có encoding hợp lệ"
                )

        if people:
            self.database.known_names = []
            self.database.known_encodings = []

            for name, vec in people:
                self.database.known_names.append(name)
                self.database.known_encodings.append(vec)

            self.database.save_database()

            print(f"💾 Đã lưu database: {len(people)} người")

            self.faiss_index.build_index(
                self.database.known_encodings,
                self.database.known_names
            )

        else:
            print("❌ Không có dữ liệu khuôn mặt nào được tạo!")

    def recognize_image(self, img):
        faces   = self.app.get(img)
        results = []
        for face in faces:
            embedding  = face.embedding
            embedding /= np.linalg.norm(embedding) + 1e-10
            name, score = self.faiss_index.search(embedding)
            results.append({"name": name, "score": float(score)})
        return results

    def process_frame(self, frame):
        faces = self.app.get(frame)
        for face in faces:
            bbox      = face.bbox.astype(int)
            embedding = face.embedding / (np.linalg.norm(face.embedding) + 1e-10)
            name, score = self.faiss_index.search(embedding)
            color = (0, 255, 0) if score > 0.5 else (0, 0, 255)
            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
            label = f"{name} ({score:.2f})"
            cv2.putText(frame, label, (bbox[0], bbox[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        return frame


