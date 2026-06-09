async function login() {
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;
  const msg      = document.getElementById("loginMessage");

  if (!username || !password) {
    msg.textContent = "Vui lòng nhập đầy đủ thông tin";
    return;
  }

  try {
    // FIX: backend dùng OAuth2PasswordRequestForm — gửi form-urlencoded
    const response = await fetch("http://127.0.0.1:8000/login", {
      method:  "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body:    new URLSearchParams({ username, password }),
    });

    // FIX: kiểm tra HTTP status thay vì chỉ đọc data.success
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      msg.textContent = err.detail || "Sai tài khoản hoặc mật khẩu";
      return;
    }

    const data = await response.json();

    // FIX: lưu JWT token vào localStorage để gửi kèm mọi request sau này
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("username",     data.username);
    localStorage.setItem("role",         data.role);

    window.location.href = "index.html";
  } catch (err) {
    msg.textContent = "Không kết nối được server";
  }
}

// Nếu đã đăng nhập rồi thì chuyển thẳng vào dashboard
if (localStorage.getItem("access_token")) {
  window.location.href = "index.html";
}
