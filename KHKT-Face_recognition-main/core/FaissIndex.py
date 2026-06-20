import numpy as np
import faiss
class FaissIndex:
    def __init__(self, dim=512):
        self.dim = dim
        self.index = None
        self.names = []

    def build_index(self, embeddings, names):
        """Tạo FAISS index chạy trên CPU."""
        if not embeddings:
            print("⚠️ Không có embeddings để tạo FAISS index.")
            return
        xb = np.vstack(embeddings).astype('float32')
        faiss.normalize_L2(xb)
        self.index = faiss.IndexFlatIP(self.dim)  # inner product = cosine similarity (sau normalize)
        self.index.add(xb)
        self.names = names
        print(f"✅ FAISS CPU index đã tạo ({len(names)} khuôn mặt)")

    def search(self, query_embedding, threshold=0.5):
        """Tìm người giống nhất (CPU)."""
        if self.index is None:
            return "unknown", 0.0
        q = np.array(query_embedding, dtype='float32').reshape(1, -1)
        faiss.normalize_L2(q)
        D, I = self.index.search(q, 1)  # tìm top-1
        sim = float(D[0][0])
        if sim >= threshold:
            return self.names[int(I[0][0])], sim
        return "unknown", sim