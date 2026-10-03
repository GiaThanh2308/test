"""Chế độ camera trên máy tính (cửa sổ OpenCV) — dùng để thử nhanh AI, KHÔNG phải server web.
Chạy server web bằng:  uvicorn backend.main:app --host 127.0.0.1 --port 8000

Phím: [q]/[ESC] thoát · [a] học thêm người mới trong known_faces
"""
import os
import queue
import threading

import cv2
from dotenv import load_dotenv

load_dotenv()

from core.AdvancedFaceRecognitionSystem import AdvancedFaceRecognitionSystem  # noqa: E402

RESOURCE_DIR = os.getenv("RESOURCE_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources"))
DB_PATH      = os.path.join(RESOURCE_DIR, "face_database.pkl")
KNOWN_DIR    = os.path.join(RESOURCE_DIR, "known_faces")


def main():
    if not os.path.isdir(RESOURCE_DIR):
        print(f"❌ Không tìm thấy thư mục resources: {RESOURCE_DIR}")
        return

    system = AdvancedFaceRecognitionSystem(database_path=DB_PATH)
    if system.database.known_names:
        system.build_ann_index()
    else:
        system.build_database_from_images(KNOWN_DIR)

    stop   = threading.Event()
    frames = queue.Queue(maxsize=1)  # luôn giữ frame mới nhất, bỏ frame cũ

    def grab():
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Không mở được camera.")
            stop.set()
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        while not stop.is_set():
            ok, frame = cap.read()
            if not ok:
                continue
            if frames.full():
                try:
                    frames.get_nowait()
                except queue.Empty:
                    pass
            frames.put(cv2.flip(frame, 1))
        cap.release()

    threading.Thread(target=grab, daemon=True).start()
    print("🎥 Đang khởi động camera...  [q]/[ESC] thoát · [a] học người mới")

    while not stop.is_set():
        try:
            frame = frames.get(timeout=0.5)
        except queue.Empty:
            continue
        cv2.imshow("AI Face Recognition", system.process_frame(frame))
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            stop.set()
        elif key == ord("a"):
            system.rescan_known_faces(KNOWN_DIR)

    cv2.destroyAllWindows()
    print("✅ Đã thoát.")


if __name__ == "__main__":
    main()
