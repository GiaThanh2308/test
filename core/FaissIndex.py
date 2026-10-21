"""FaissIndex — tìm khuôn mặt giống nhất bằng cosine similarity (FAISS, chạy CPU)."""
import faiss
import numpy as np

MATCH_THRESHOLD = 0.5  # ngưỡng cosine; dưới ngưỡng này coi là "unknown"


def l2_normalize(vectors) -> np.ndarray:
    """MỘT hàm chuẩn hoá duy nhất (NumPy) cho cả lúc dựng index lẫn lúc truy vấn.
    Nhận vector (d,) hoặc ma trận (n, d); trả về float32 có độ dài 1."""
    x = np.atleast_2d(np.asarray(vectors, dtype=np.float64))
    x = x / (np.linalg.norm(x, axis=1, keepdims=True) + 1e-10)
    return np.ascontiguousarray(x, dtype=np.float32)


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
        xb = l2_normalize(np.vstack(embeddings))
        index = faiss.IndexFlatIP(self.dim)  # inner product = cosine sau khi chuẩn hóa
        index.add(xb)
        # gán một lần ở cuối để request đang tìm kiếm không thấy index dở dang
        self.names, self.index = list(names), index
        print(f"✅ FAISS index đã tạo ({len(names)} vector)")

    def search(self, query_embedding, threshold: float = MATCH_THRESHOLD):
        """Trả về (tên, độ giống). Dưới ngưỡng → ("unknown", độ giống)."""
        index, names = self.index, self.names  # đọc một lần: không lệch nhau nếu index bị thay giữa chừng
        if index is None:
            return "unknown", 0.0
        scores, ids = index.search(l2_normalize(query_embedding), 1)
        sim = float(scores[0][0])
        if sim >= threshold:
            return names[int(ids[0][0])], sim
        return "unknown", sim
