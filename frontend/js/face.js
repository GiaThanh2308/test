     // FIX: dùng requireAuth() từ api.js
requireAuth();
document.getElementById("usernameDisplay").textContent = localStorage.getItem("username");

const video = document.getElementById("video");
let stream  = null;

// ─── Load stats on page load ─────────────────────────────────
async function loadStats() {
  try {
    // FIX: dùng apiFetch (tự gắn token)
    const res  = await apiFetch("/stats/summary");
    if (!res.ok) return;
    const data = await res.json();
    document.getElementById("statStudents").textContent = data.total_students;
    document.getElementById("statToday").textContent    = data.today_violations;
    document.getElementById("statWeek").textContent     = data.week_violations;
    document.getElementById("statMonth").textContent    = data.month_violations;
  } catch (e) {
    console.warn("Không load được stats:", e);
  }
}

async function loadRecentViolations() {
  try {
    const res  = await apiFetch("/violations?limit=5");
    if (!res.ok) return;
    const data = await res.json();
    const tbody = document.getElementById("recentViolations");
    if (!data.length) return;

    tbody.innerHTML = data
      .map(
        (v) => `
      <tr>
        <td><strong>${escHtml(v.student_name)}</strong><br><small style="color:var(--gray-400)">${escHtml(v.student_code)}</small></td>
        <td>${escHtml(v.class_name)}</td>
        <td><span class="badge badge-red">${escHtml(v.violation_type)}</span></td>
        <td style="color:var(--gray-400);font-size:13px">${formatDate(v.created_at)}</td>
      </tr>
    `,
      )
      .join("");
  } catch (e) {
    console.warn("Không load được vi phạm:", e);
  }
}

function formatDate(isoStr) {
  const d = new Date(isoStr);
  return (
    d.toLocaleDateString("vi-VN") +
    " " +
    d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })
  );
}

// FIX: helper escape HTML dùng nội bộ trong file này
function escHtml(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function apiAssetUrl(path) {
  if (!path) return "";
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

function renderProfileAvatar(student) {
  const imageUrl = apiAssetUrl(student.face_image_url);
  if (!imageUrl) {
    return `<div class="profile-avatar"><i class="fa-solid fa-user-graduate"></i></div>`;
  }

  return `
    <div class="profile-avatar has-photo">
      <i class="fa-solid fa-user-graduate"></i>
      <img
        src="${escHtml(imageUrl)}"
        alt="${escHtml(student.full_name)}"
        onerror="console.error('Failed image:', this.src); console.error('Natural size:', this.naturalWidth, this.naturalHeight);"
      />
    </div>`;
}

// ─── Camera ──────────────────────────────────────────────────
async function startCamera() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: true });
    video.srcObject = stream;
    video.style.display = "block";
    document.getElementById("cameraPlaceholder").style.display = "none";
  } catch (err) {
    alert("Không mở được camera: " + err.message);
  }
}

function stopCamera() {
  if (stream) {
    stream.getTracks().forEach((t) => t.stop());
    stream = null;
  }
  video.style.display   = "none";
  video.srcObject       = null;
  document.getElementById("cameraPlaceholder").style.display = "block";
}

async function captureAndRecognize() {
  if (!stream) {
    alert("Hãy bật camera trước");
    return;
  }
  const canvas = document.getElementById("canvas");
  const ctx    = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  canvas.toBlob(async (blob) => {
    const formData = new FormData();
    formData.append("file", blob, "capture.jpg");
    await sendRecognize(formData);
  }, "image/jpeg");
}

async function uploadImage() {
  const file = document.getElementById("imageInput").files[0];
  if (!file) {
    alert("Chọn ảnh trước");
    return;
  }
  const formData = new FormData();
  formData.append("file", file);
  await sendRecognize(formData);
}

async function sendRecognize(formData) {
  const profile = document.getElementById("studentProfile");
  profile.innerHTML = `<div class="empty-profile"><i class="fa-solid fa-spinner fa-spin"></i><p>Đang nhận diện...</p></div>`;

  try {
    // FIX: dùng apiFetch để gắn token tự động
    const response = await apiFetch("/recognize-face", {
      method: "POST",
      body:   formData,
    });

    if (!response.ok) {
      profile.innerHTML = `<div class="empty-profile"><i class="fa-solid fa-circle-exclamation"></i><p>Lỗi server (${response.status})</p></div>`;
      return;
    }

    const data = await response.json();
    renderStudentProfile(data);
  } catch (err) {
    profile.innerHTML = `<div class="empty-profile"><i class="fa-solid fa-circle-exclamation"></i><p>Lỗi kết nối server</p></div>`;
  }
}

// ─── Render profile ───────────────────────────────────────────
function renderStudentProfile(data) {
  const profile = document.getElementById("studentProfile");

  if (!data.faces || data.faces.length === 0) {
    profile.innerHTML = `
      <div class="empty-profile">
        <i class="fa-solid fa-user-slash"></i>
        <p>Không nhận diện được học sinh</p>
        <small>Vui lòng chụp lại hoặc kiểm tra database</small>
      </div>`;
    return;
  }

  const s        = data.faces[0];
  const accuracy = Math.round(s.score * 100);
  const accColor =
    accuracy >= 80 ? "var(--success)" :
    accuracy >= 60 ? "var(--warning)" : "var(--danger)";

  if (!s.id) {
    profile.innerHTML = `
      <div class="empty-profile">
        <i class="fa-solid fa-user-question"></i>
        <p>Khuôn mặt chưa có hồ sơ</p>
      </div>`;
    return;
  }

  // FIX: escape dữ liệu từ server khi render vào innerHTML
  profile.innerHTML = `
    <div class="profile-card">
      ${renderProfileAvatar(s)}
      <h2>${escHtml(s.full_name)}</h2>

      <div class="profile-info">
        <div class="profile-info-row"><span>Mã học sinh: </span><span>${escHtml(s.student_code)}</span></div>
        <div class="profile-info-row"><span>Lớp: </span><span>${escHtml(s.class_name)}</span></div>
        <div class="profile-info-row"><span>SĐT: </span><span>${escHtml(s.phone) || "—"}</span></div>
        <div class="profile-info-row"><span>Biển số xe: </span><span>${escHtml(s.plate_number) || "—"}</span></div>
        <div class="profile-info-row">
          <span>Độ chính xác:</span>  
          <span style="color:${accColor};font-weight:700">${accuracy}%</span>
        </div>
        <div class="accuracy-bar">
          <div class="accuracy-fill" style="width:${accuracy}%;background:${accColor}"></div>
        </div>
      </div>

      <div class="violation-section">
        <label>Loại vi phạm</label>
        <select id="violationType">
          <option>Không đồng phục</option>
          <option>Đi trễ</option>
          <option>Dùng điện thoại</option>
          <option>Không đeo thẻ</option>
          <option>Không đội mũ bảo hiểm</option>
          <option>Gây mất trật tự</option>
          <option>Khác</option>
        </select>

        <label>Ghi chú</label>
        <textarea id="violationNote" placeholder="Nhập ghi chú thêm (nếu có)..."></textarea>

        <button class="btn-danger" onclick="saveViolation(${s.id})">
          <i class="fa-solid fa-floppy-disk"></i> Lưu vi phạm
        </button>
      </div>
    </div>`;
}

// ─── Save violation ───────────────────────────────────────────
async function saveViolation(studentId) {
  const violationType = document.getElementById("violationType").value;
  const note          = document.getElementById("violationNote").value;

  try {
    const res = await apiFetch("/violations", {
      method: "POST",
      body:   JSON.stringify({
        student_id:     studentId,
        violation_type: violationType,
        note,
      }),
    });

    // FIX: kiểm tra res.ok thay vì chỉ kiểm tra data.id
    // Trước đây: nếu server trả lỗi 422/500, code im lặng hoàn toàn
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      showToast("❌ " + (err.detail || "Lỗi khi lưu vi phạm"), true);
      return;
    }

    showToast("✅ Đã lưu vi phạm thành công!");
    loadStats();
    loadRecentViolations();
    document.getElementById("violationNote").value = "";
  } catch (err) {
    showToast("❌ Lỗi kết nối server", true);
  }
}

function showToast(msg, isError = false) {
  const toast = document.createElement("div");
  toast.textContent = msg;
  Object.assign(toast.style, {
    position:     "fixed",
    bottom:       "24px",
    right:        "24px",
    background:   isError ? "var(--danger)" : "#1f2937",
    color:        "white",
    padding:      "14px 20px",
    borderRadius: "12px",
    fontSize:     "14px",
    fontWeight:   "600",
    zIndex:       "9999",
    boxShadow:    "0 8px 24px rgba(0,0,0,0.2)",
    fontFamily:   "inherit",
  });
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

// Init
loadStats();
loadRecentViolations();


