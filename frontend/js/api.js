/**
 * api.js — tiện ích dùng chung cho mọi trang: gọi API, đăng nhập/đăng xuất, kiểm tra quyền, dựng menu.
 * Vai trò: admin / teacher = dùng mọi trang · student = chỉ trang Nhận diện (index.html).
 */

/** Địa chỉ API. Mở file trực tiếp hoặc bằng Live Server (5500/5501) → server ở 127.0.0.1:8000;
 *  còn lại (server tự phục vụ giao diện, kể cả qua tunnel) → cùng origin với trang. */
function getApiBase() {
  const manual = localStorage.getItem("api_base");
  if (manual) return manual.replace(/\/$/, "");
  const devServer = location.protocol === "file:" || ["5500", "5501"].includes(location.port);
  return devServer ? "http://127.0.0.1:8000" : location.origin;
}

const API_BASE = getApiBase();
const TEACHER_ROLES = ["admin", "teacher"];
const ROLE_LABEL = { admin: "Admin", teacher: "Giáo viên", student: "Học sinh" };

function escapeHtml(value) {
  return value == null
    ? ""
    : String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function getRole() {
  return localStorage.getItem("role") || "student";
}
function isTeacher() {
  return TEACHER_ROLES.includes(localStorage.getItem("role"));
}

/** Địa chỉ đầy đủ của một đường dẫn trả về từ API; đính token cho ảnh (thẻ <img> không gửi được header). */
function apiAssetUrl(path, { withToken = false } = {}) {
  if (!path) return "";
  let url = /^https?:\/\//i.test(path) ? path : `${API_BASE}${path.startsWith("/") ? path : "/" + path}`;
  if (withToken) {
    const token = encodeURIComponent(localStorage.getItem("access_token") || "");
    url += `${url.includes("?") ? "&" : "?"}token=${token}`;
  }
  return url;
}

function clearSession() {
  ["access_token", "username", "role"].forEach((k) => localStorage.removeItem(k));
}

async function apiFetch(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const token = localStorage.getItem("access_token");
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (res.status === 401) {
    clearSession();
    location.href = "login.html";
  }
  return res;
}

function logout() {
  clearSession();
  location.href = "login.html";
}

/** Chưa đăng nhập → về trang đăng nhập. */
function requireAuth() {
  if (!localStorage.getItem("access_token")) location.href = "login.html";
}

/** Chỉ admin/teacher; student bị đưa về trang Nhận diện. (Server cũng kiểm tra lại — đây chỉ là lớp giao diện.) */
function requireTeacher() {
  if (!isTeacher()) location.href = "index.html";
}

const NAV_ITEMS = [
  { key: "dashboard", href: "dashboard.html", icon: "fa-chart-line", label: "Dashboard" },
  { key: "index", href: "index.html", icon: "fa-camera", label: "Nhận diện" },
  { key: "students", href: "students.html", icon: "fa-user-graduate", label: "Học sinh" },
  { key: "chatbot", href: "chatbot.html", icon: "fa-robot", label: "Chatbot AI" },
];

/** Dựng thanh menu (PC) và thanh menu dưới đáy (điện thoại). activePage: dashboard | index | students | chatbot */
function renderNav(activePage) {
  const role = getRole();
  const username = localStorage.getItem("username") || "---";
  const items = isTeacher() ? NAV_ITEMS : NAV_ITEMS.filter((i) => i.key === "index");

  const sidebar = document.getElementById("sidebar");
  if (sidebar) {
    sidebar.innerHTML = `
      <div class="logo"><i class="fa-solid fa-school"></i><span>AI School</span></div>
      <ul class="menu">${items
        .map(
          (i) => `
        <li class="${i.key === activePage ? "active" : ""}">
          <a href="${i.href}"><i class="fa-solid ${i.icon}"></i>${i.label}</a>
        </li>`,
        )
        .join("")}</ul>
      <div class="sidebar-user">
        <i class="fa-solid fa-user-circle"></i>
        <div class="sidebar-user-info">
          <span class="sidebar-username">${escapeHtml(username)}</span>
          <span class="sidebar-role">${ROLE_LABEL[role] || role}</span>
        </div>
      </div>
      <button class="logout-btn" onclick="logout()"><i class="fa-solid fa-right-from-bracket"></i> Đăng xuất</button>`;
  }

  const mobileNav = document.getElementById("mobileNav");
  if (mobileNav) {
    mobileNav.innerHTML =
      items
        .map(
          (i) => `
      <a class="mobile-item ${i.key === activePage ? "active" : ""}" href="${i.href}">
        <i class="fa-solid ${i.icon}"></i><span>${i.label}</span>
      </a>`,
        )
        .join("") +
      `<span class="mobile-item" onclick="logout()"><i class="fa-solid fa-right-from-bracket"></i><span>Thoát</span></span>`;
  }

  const nameEl = document.getElementById("usernameDisplay");
  if (nameEl) nameEl.textContent = username;
  const badge = document.getElementById("roleBadge");
  if (badge) {
    badge.textContent = ROLE_LABEL[role] || role;
    badge.dataset.role = role; // màu theo vai trò nằm trong theme.css
  }
}
/* ── Toast + hộp xác nhận dùng chung (thay alert/confirm của trình duyệt) ── */
function toast(msg, err = false, ms = 3200) {
  document.querySelectorAll(".toast").forEach((t) => t.remove());
  const t = document.createElement("div");
  t.className = "toast" + (err ? " err" : "");
  t.setAttribute("role", "status");
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), ms);
}

function confirmDialog({ title = "Xác nhận", message = "", okText = "Đồng ý", danger = false } = {}) {
  return new Promise((resolve) => {
    const box = document.createElement("div");
    box.className = "dlg-backdrop";
    box.innerHTML = `<div class="dlg" role="dialog" aria-modal="true">
      <h3>${escapeHtml(title)}</h3><p>${escapeHtml(message)}</p>
      <div class="dlg-btns"><button type="button" class="dlg-cancel">Hủy</button>
      <button type="button" class="dlg-ok${danger ? " danger" : ""}">${escapeHtml(okText)}</button></div></div>`;
    const onKey = (e) => { if (e.key === "Escape") done(false); };
    const done = (v) => { document.removeEventListener("keydown", onKey); box.remove(); resolve(v); };
    box.addEventListener("mousedown", (e) => { if (e.target === box) done(false); });
    box.querySelector(".dlg-cancel").onclick = () => done(false);
    box.querySelector(".dlg-ok").onclick = () => done(true);
    document.addEventListener("keydown", onKey);
    document.body.appendChild(box);
    box.querySelector(".dlg-cancel").focus();
  });
}

/* Ảnh cần đăng nhập: <img data-auth-src="/face-image/..."> được tải bằng fetch (header Authorization)
   rồi dựng blob — token không còn nằm trong URL (log, lịch sử trình duyệt, Referer). */
const _imgCache = new Map();
const _imgObserver = "IntersectionObserver" in window
  ? new IntersectionObserver((entries) => entries.forEach((e) => {
      if (e.isIntersecting) { _imgObserver.unobserve(e.target); _loadAuthImg(e.target); }
    }), { rootMargin: "200px" })
  : null;

async function _loadAuthImg(img) {
  const path = img.dataset.authSrc;
  if (!path) return;
  try {
    if (!_imgCache.has(path)) {
      _imgCache.set(path, apiFetch(path).then(async (r) => {
        if (!r.ok) throw new Error(r.status);
        return URL.createObjectURL(await r.blob());
      }));
    }
    img.src = await _imgCache.get(path);
  } catch {
    _imgCache.delete(path);
    img.remove();
  }
}

function hydrateAuthImages(root = document) {
  root.querySelectorAll("img[data-auth-src]:not([src])").forEach((img) => (_imgObserver ? _imgObserver.observe(img) : _loadAuthImg(img)));
}
