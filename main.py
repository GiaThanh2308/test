from core.AdvancedFaceRecognitionSystem import AdvancedFaceRecognitionSystem
import cv2
import threading
import queue
import os
import numpy as np
from dotenv import load_dotenv

load_dotenv()


def main():
    system = AdvancedFaceRecognitionSystem()

    # FIX: bỏ hardcode "D:\python\KHKT\resources"
    # Ưu tiên: biến môi trường RESOURCE_DIR → thư mục "resources" cạnh file này
    resource_dir = os.getenv(
        "RESOURCE_DIR",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")
    )
    db_path   = os.path.join(resource_dir, "face_database.pkl")
    known_dir = os.path.join(resource_dir, "known_faces")

    if not os.path.exists(resource_dir):
        print(f"❌ Không tìm thấy thư mục resources: {resource_dir}")
        print("   Đặt biến môi trường RESOURCE_DIR hoặc tạo thư mục 'resources/' cạnh main.py")
        return

    if not os.path.exists(db_path):
        system.database.database_path = db_path
        system.build_database_from_images(known_dir)
        system.build_ann_index()
    else:
        print("📂 Database có sẵn, đang tải...")
        system.database.database_path = db_path
        system.database.load_database()
        system.faiss_index.build_index(
            system.database.known_encodings,
            system.database.known_names
        )

    stop_evt = threading.Event()
    frame_q  = queue.Queue(maxsize=2)

    def camera_thread():
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Không mở được camera.")
            stop_evt.set()
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        while not stop_evt.is_set():
            ret, frame = cap.read()
            if not ret:
                continue
            frame = cv2.flip(frame, 1)
            if frame_q.full():
                try:
                    frame_q.get_nowait()
                except queue.Empty:
                    pass
            frame_q.put(frame)
        cap.release()

    def recognition_thread():
        while not stop_evt.is_set():
            try:
                frame = frame_q.get(timeout=0.5)
            except queue.Empty:
                continue
            processed = system.process_frame(frame)
            cv2.imshow("AI Face Recognition", processed)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), 27):
                stop_evt.set()
            elif key == ord('a'):
                print("🔄 Đang quét lại thư mục known_faces...")
                system.rescan_known_faces(known_dir)
                system.build_ann_index()
        cv2.destroyAllWindows()

    print("🎥 Đang khởi động camera...")
    print(f"   📁 Resource dir: {resource_dir}")
    print("""
    🎮 Phím điều khiển:
    [q] hoặc [ESC] - Thoát
    [a] - Quét lại thư mục known_faces""")

    t1 = threading.Thread(target=camera_thread,     daemon=True)
    t2 = threading.Thread(target=recognition_thread, daemon=True)
    t1.start()
    t2.start()
    t2.join()
    stop_evt.set()

    cv2.destroyAllWindows()
    system.database.save_database()
    print("✅ Đã lưu database & thoát an toàn.")


if __name__ == "__main__":
    main()
