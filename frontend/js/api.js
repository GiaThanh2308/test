/**
 * api.js — Helper dùng chung cho toàn bộ frontend.
 * - apiFetch(): tự gắn JWT token, xử lý 401
 * - requireAuth(): guard cần đăng nhập
 * - requireTeacher(): guard chỉ cho teacher/admin
 * - logout(): xóa token và về login
 */

const API_BASE = "http://127.0.0.1:8000";

async function apiFetch(path, options = {}) {
  const token = localStorage.getItem("access_token");

  const headers = { ...(options.headers || {}) };
  if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    localStorage.removeItem("access_token");
    localStorage.removeItem("username");
    localStorage.removeItem("role");
    window.location.href = "login.html";
    return res;
  }
  return res;
}

function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("username");
  localStorage.removeItem("role");
  window.location.href = "login.html";
}

/** Guard: cần đăng nhập (mọi role) */
function requireAuth() {
  if (!localStorage.getItem("access_token")) {
    window.location.href = "login.html";
  }
}

/** Guard: chỉ teacher và admin mới vào được */
function requireTeacher() {
  const role = localStorage.getItem("role");
  if (!["admin", "teacher"].includes(role)) {
    // security bị chặn → về trang quét
    window.location.href = "scan.html";
  }
}
