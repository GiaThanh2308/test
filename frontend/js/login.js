// login.js — đăng nhập rồi chuyển đúng trang theo vai trò (student → Nhận diện, còn lại → Dashboard)

function redirectByRole(role) {
  location.href = role === "student" ? "index.html" : "dashboard.html";
}

if (localStorage.getItem("access_token")) redirectByRole(localStorage.getItem("role"));

async function login() {
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;
  const msg = document.getElementById("loginMessage");
  const btn = document.getElementById("loginBtn");

  if (!username || !password) {
    msg.textContent = "Vui lòng nhập đầy đủ thông tin";
    return;
  }

  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang đăng nhập...';
  msg.textContent = "";

  try {
    const res = await fetch(`${API_BASE}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ username, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      msg.textContent = err.detail || "Sai tài khoản hoặc mật khẩu";
      return;
    }
    const data = await res.json();
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("username", data.username);
    localStorage.setItem("role", data.role);
    redirectByRole(data.role);
  } catch {
    msg.textContent = "Không kết nối được server";
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-right-to-bracket"></i> Đăng nhập';
  }
}
