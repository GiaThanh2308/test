// scan.js — Trang quét vi phạm cho đội an ninh / cờ đỏ
requireAuth();

document.getElementById("usernameDisplay").textContent =
  localStorage.getItem("username") || "---";

const video = document.getElementById("video");
let stream  = null;
let currentStudentId = null;

// ── Camera ────────────────────────────────────────────────────
async function startCamera() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment", width: 640, height: 480 }
    });
    video.srcObject    = stream;
    video.style.display = "block";
    document.getElementById("camPlaceholder").style.display = "none";
    document.getElementById("scanFrame").classList.add("visible");
  } catch (err) {
    showToast("Không mở được camera: " + err.message, "error");
  }
}

function stopCamera() {
  if (stream) {
    stream.getTracks().forEach(t => t.stop());
    stream = null;
  }
  video.style.display = "none";
  video.srcObject = null;
  document.getElementById("camPlaceholder").style.display = "flex";
  document.getElementById("scanFrame").classList.remove("visible");
}

async function captureAndRecognize() {
  if (!stream) { showToast("Hãy bật camera trước", "error"); return; }

  const canvas = document.getElementById("canvas");
  canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
  canvas.toBlob(async blob => {
    const fd = new FormData();
    fd.append("file", blob, "capture.jpg");
    await recognize(fd);
  }, "image/jpeg", 0.9);
}

async function uploadImage() {
  const file = document.getElementById("imageInput").files[0];
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file);
  await recognize(fd);
}

async function recognize(formData) {
  setResultLoading();
  try {
    const res = await apiFetch("/recognize-face", { method: "POST", body: formData });
    if (!res.ok) { showToast("Lỗi server " + res.status, "error"); setResultEmpty(); return; }
    const data = await res.json();
    renderResult(data);
  } catch {
    showToast("Không kết nối được server", "error");
    setResultEmpty();
  }
}

// ── Result rendering ──────────────────────────────────────────
function setResultLoading() {
  currentStudentId = null;
  document.getElementById("resultArea").innerHTML = `
    <div class="result-empty">
      <i class="fa-solid fa-spinner fa-spin" style="font-size:40px;color:#3b82f6"></i>
      <p>Đang nhận diện...</p>
    </div>`;
}

function setResultEmpty() {
  currentStudentId = null;
  document.getElementById("resultArea").innerHTML = `
    <div class="result-empty">
      <i class="fa-solid fa-user-slash"></i>
      <p>Không nhận diện được</p>
      <small>Thử lại hoặc kiểm tra ảnh</small>
    </div>`;
}

function escHtml(s) {
  if (!s) return "—";
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

function renderResult(data) {
  const faces = data.faces;
  if (!faces || faces.length === 0) { setResultEmpty(); return; }

  const s = faces[0];
  if (!s.id) {
    currentStudentId = null;
    document.getElementById("resultArea").innerHTML = `
      <div class="result-empty">
        <i class="fa-solid fa-user-question" style="color:#f59e0b"></i>
        <p>Khuôn mặt chưa có hồ sơ</p>
        <small>Độ khớp: ${Math.round(s.score * 100)}%</small>
      </div>`;
    return;
  }

  currentStudentId = s.id;
  const acc   = Math.round(s.score * 100);
  const color = acc >= 80 ? "#22c55e" : acc >= 60 ? "#f59e0b" : "#ef4444";

  document.getElementById("resultArea").innerHTML = `
    <div class="student-card">
      <div class="student-card-top">
        <div class="student-avatar"><i class="fa-solid fa-user-graduate"></i></div>
        <div>
          <div class="student-name">${escHtml(s.full_name)}</div>
          <div class="student-meta">${escHtml(s.class_name)} · ${escHtml(s.student_code)}</div>
        </div>
        <div class="confidence-pill" style="background:${color}44;border:1.5px solid ${color};color:${color}">
          ${acc}%
        </div>
      </div>

      <div class="student-info">
        <div class="info-row">
          <span class="info-label">SĐT học sinh</span>
          <span class="info-value">${escHtml(s.phone)}</span>
        </div>
        <div class="info-row">
          <span class="info-label">SĐT phụ huynh</span>
          <span class="info-value">${escHtml(s.parent_phone)}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Biển số xe</span>
          <span class="info-value">${escHtml(s.plate_number)}</span>
        </div>
      </div>

      <div class="violation-form">
        <h3><i class="fa-solid fa-triangle-exclamation" style="color:#ef4444;margin-right:6px"></i>Ghi vi phạm</h3>
        <select id="violationType">
          <option>Không đồng phục</option>
          <option>Đi trễ</option>
          <option>Dùng điện thoại</option>
          <option>Không đeo thẻ</option>
          <option>Không đội mũ bảo hiểm</option>
          <option>Gây mất trật tự</option>
          <option>Khác</option>
        </select>
        <textarea id="violationNote" placeholder="Ghi chú thêm (không bắt buộc)..."></textarea>
        <button class="btn-save-violation" onclick="saveViolation()">
          <i class="fa-solid fa-floppy-disk"></i> Lưu vi phạm
        </button>
      </div>
    </div>`;
}

// ── Save violation ────────────────────────────────────────────
async function saveViolation() {
  if (!currentStudentId) return;

  const btn  = document.querySelector(".btn-save-violation");
  const type = document.getElementById("violationType").value;
  const note = document.getElementById("violationNote").value;

  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang lưu...';

  try {
    const res = await apiFetch("/violations", {
      method: "POST",
      body: JSON.stringify({ student_id: currentStudentId, violation_type: type, note }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      showToast("❌ " + (err.detail || "Lỗi khi lưu"), "error");
      return;
    }

    showToast("✅ Đã lưu vi phạm thành công!", "success");
    document.getElementById("violationNote").value = "";

  } catch {
    showToast("❌ Lỗi kết nối server", "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Lưu vi phạm';
  }
}

// ── Toast ─────────────────────────────────────────────────────
function showToast(msg, type = "success") {
  document.querySelectorAll(".toast").forEach(t => t.remove());
  const t = document.createElement("div");
  t.className = `toast ${type}`;
  t.innerHTML = `<i class="fa-solid fa-${type === "success" ? "circle-check" : "circle-xmark"}"></i> ${escHtml(msg)}`;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}
