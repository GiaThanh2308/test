import os, pickle
import numpy as np
from datetime import datetime
class FaceDatabase:
    def __init__(self, database_path="face_database.pkl"):
        self.database_path = database_path
        self.known_encodings = []
        self.known_names = []
        self.face_metadata = {}
        self.load_database()
    def load_database(self):
        if os.path.exists(self.database_path):
            with open(self.database_path, 'rb') as f:
                data = pickle.load(f)
                self.known_encodings = data['encodings']
                self.known_names = data['names']
                self.face_metadata = data.get('metadata', {})
            print(f"📂 Đã tải database: {len(self.known_names)} người")
    
    def save_database(self):
        data = {
            'encodings': self.known_encodings,
            'names': self.known_names,
            'metadata': self.face_metadata
        }
        with open(self.database_path, 'wb') as f:
            pickle.dump(data, f)
        print("💾 Đã lưu database")  
    def add_person(self, name, encodings, metadata=None):
        if not encodings:
            return False

        mean_vec = np.mean(encodings, axis=0)
        mean_vec /= np.linalg.norm(mean_vec) + 1e-10

        self.known_encodings.append(
            mean_vec.astype(np.float32)
        )
        self.known_names.append(name)

        self.face_metadata[name] = {
            "embeddings": [e.astype(np.float32) for e in encodings],
            "added": datetime.now().isoformat(),
            "num_images": len(encodings)
        }

        self.save_database()
        return True

