"""FaissIndex — tìm khuôn mặt giống nhất bằng cosine similarity (FAISS, chạy CPU)."""
import faiss
import numpy as np

MATCH_THRESHOLD = 0.5  # ngưỡng cosine; dưới ngưỡng này coi là "unknown"


class FaissIndex:
    def __init__(self, dim: int = 512):
        self.dim = dim
        self.index = None
        self.names: list[str] = []

    def build_index(self, embeddings, names):
        """Dựng index từ danh sách vector (mỗi vector ứng với một tên trong `names`)."""
        if len(embeddings) == 0 or len(embeddings) != len(names):
            print("⚠️ Không có embeddings hợp lệ để tạo FAISS index.")
            return
        xb = np.vstack(embeddings).astype("float32")
        faiss.normalize_L2(xb)
        index = faiss.IndexFlatIP(self.dim)  # inner product = cosine sau khi chuẩn hóa
        index.add(xb)
        # gán một lần ở cuối để request đang tìm kiếm không thấy index dở dang
        self.names, self.index = list(names), index
        print(f"✅ FAISS index đã tạo ({len(names)} vector)")

    def search(self, query_embedding, threshold: float = MATCH_THRESHOLD):
        """Trả về (tên, độ giống). Dưới ngưỡng → ("unknown", độ giống)."""
        if self.index is None:
            return "unknown", 0.0
        q = np.asarray(query_embedding, dtype="float32").reshape(1, -1)
        faiss.normalize_L2(q)
        scores, ids = self.index.search(q, 1)
        sim = float(scores[0][0])
        if sim >= threshold:
            return self.names[int(ids[0][0])], sim
        return "unknown", sim
