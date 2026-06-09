// login.js — Đăng nhập và redirect đúng trang theo role

// Nếu đã đăng nhập rồi thì redirect luôn
const _existingToken = localStorage.getItem("access_token");
const _existingRole  = localStorage.getItem("role");
if (_existingToken) {
  window.location.href = _existingRole === "security" ? "scan.html" : "dashboard.html";
}

async function login() {
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;
  const msg      = document.getElementById("loginMessage");
  const btn      = document.getElementById("loginBtn");

  if (!username || !password) {
    msg.textContent = "Vui lòng nhập đầy đủ thông tin";
    return;
  }

  btn.disabled = true;
  btn.textContent = "Đang đăng nhập...";
  msg.textContent = "";

  try {
    const response = await fetch("http://127.0.0.1:8000/login", {
      method:  "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body:    new URLSearchParams({ username, password }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      msg.textContent = err.detail || "Sai tài khoản hoặc mật khẩu";
      return;
    }

    const data = await response.json();
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("username",     data.username);
    localStorage.setItem("role",         data.role);

    // Redirect đúng trang theo role
    if (data.role === "security") {
      window.location.href = "scan.html";       // đội an ninh → trang quét
    } else {
      window.location.href = "dashboard.html";  // teacher/admin → dashboard
    }

  } catch {
    msg.textContent = "Không kết nối được server";
  } finally {
    btn.disabled = false;
    btn.textContent = "Đăng nhập";
  }
}

// Cho phép nhấn Enter để đăng nhập
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("password")?.addEventListener("keydown", e => {
    if (e.key === "Enter") login();
  });
});
