/**
 * api.js — Helper fetch dùng chung cho toàn bộ frontend.
 *
 * Tự động:
 *  - Gắn Authorization: Bearer <token> vào mọi request
 *  - Nếu nhận 401 → xóa token, redirect về login
 *
 * Cách dùng: thay fetch(...) bằng apiFetch(...)
 * Ví dụ:  const data = await apiFetch("/students").then(r => r.json());
 */

const API_BASE = "http://127.0.0.1:8000";

async function apiFetch(path, options = {}) {
  const token = localStorage.getItem("access_token");

  const headers = {
    ...(options.headers || {}),
  };

  // Không override Content-Type nếu gửi FormData
  if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  // FIX: tự động logout khi token hết hạn hoặc không hợp lệ
  if (res.status === 401) {
    localStorage.removeItem("access_token");
    localStorage.removeItem("username");
    localStorage.removeItem("role");
    window.location.href = "login.html";
    return res; // dừng lại, không xử lý tiếp
  }

  return res;
}

function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("username");
  localStorage.removeItem("role");
  window.location.href = "login.html";
}

// Auth guard — gọi ở đầu mỗi trang cần đăng nhập
function requireAuth() {
  if (!localStorage.getItem("access_token")) {
    window.location.href = "login.html";
  }
}
