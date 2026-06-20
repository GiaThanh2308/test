// scan.js — Trang quét vi phạm cho đội an ninh / cờ đỏ
// Hỗ trợ 2 chế độ: nhận diện khuôn mặt & nhận diện biển số xe
requireAuth();

document.getElementById("usernameDisplay").textContent =
  localStorage.getItem("username") || "---";

const video = document.getElementById("video");
let stream  = null;
let currentStudentId = null;
let currentMode = "face"; // "face" | "plate"

// ── Mode switching ─────────────────────────────────────────────
function switchMode(mode) {
  currentMode = mode;
  currentStudentId = null;

  // Cập nhật tab UI
  document.getElementById("tabFace").classList.toggle("active", mode === "face");
  document.getElementById("tabPlate").classList.toggle("active", mode === "plate");

  // Cập nhật scan frame
  document.getElementById("scanFrameFace").classList.toggle("visible", mode === "face" && !!stream);
  document.getElementById("scanFramePlate").classList.toggle("visible", mode === "plate" && !!stream);

  // Cập nhật hint
  const hint = document.getElementById("modeHint");
  if (stream) {
    hint.classList.add("visible");
    if (mode === "face") {
      hint.className = "cam-mode-hint face-hint visible";
      hint.innerHTML = '<i class="fa-solid fa-face-viewfinder"></i> Hướng camera vào khuôn mặt';
    } else {
      hint.className = "cam-mode-hint plate-hint visible";
      hint.innerHTML = '<i class="fa-solid fa-car"></i> Hướng camera vào biển số xe';
    }
  }

  // Cập nhật nút scan
  const btnScan = document.getElementById("btnScan");
  if (mode === "face") {
    btnScan.className = "btn-cam-scan";
    btnScan.innerHTML = '<i class="fa-solid fa-face-viewfinder"></i> Nhận diện';
  } else {
    btnScan.className = "btn-cam-scan plate";
    btnScan.innerHTML = '<i class="fa-solid fa-car"></i> Đọc biển số';
  }

  // Reset kết quả
  setResultEmpty();
}

// ── Camera ─────────────────────────────────────────────────────
async function startCamera() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment", width: 640, height: 480 }
    });
    video.srcObject    = stream;
    video.style.display = "block";
    document.getElementById("camPlaceholder").style.display = "none";

    // Hiện đúng frame theo mode hiện tại
    document.getElementById("scanFrameFace").classList.toggle("visible", currentMode === "face");
    document.getElementById("scanFramePlate").classList.toggle("visible", currentMode === "plate");

    // Hiện hint
    const hint = document.getElementById("modeHint");
    hint.classList.add("visible");
    if (currentMode === "face") {
      hint.className = "cam-mode-hint face-hint visible";
      hint.innerHTML = '<i class="fa-solid fa-face-viewfinder"></i> Hướng camera vào khuôn mặt';
    } else {
      hint.className = "cam-mode-hint plate-hint visible";
      hint.innerHTML = '<i class="fa-solid fa-car"></i> Hướng camera vào biển số xe';
    }
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
  document.getElementById("scanFrameFace").classList.remove("visible");
  document.getElementById("scanFramePlate").classList.remove("visible");
  document.getElementById("modeHint").classList.remove("visible");
}

// ── Capture & dispatch theo mode ───────────────────────────────
async function captureAndRecognize() {
  if (!stream) { showToast("Hãy bật camera trước", "error"); return; }

  const canvas = document.getElementById("canvas");
  canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
  canvas.toBlob(async blob => {
    const fd = new FormData();
    fd.append("file", blob, "capture.jpg");
    if (currentMode === "face") {
      await recognizeFace(fd);
    } else {
      await recognizePlate(fd);
    }
  }, "image/jpeg", 0.9);
}

async function uploadImage() {
  const file = document.getElementById("imageInput").files[0];
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file);
  if (currentMode === "face") {
    await recognizeFace(fd);
  } else {
    await recognizePlate(fd);
  }
}

// ── Face recognition ──────────────────────────────────────────
async function recognizeFace(formData) {
  setResultLoading("Đang nhận diện khuôn mặt...");
  try {
    const res = await apiFetch("/recognize-face", { method: "POST", body: formData });
    if (!res.ok) { showToast("Lỗi server " + res.status, "error"); setResultEmpty(); return; }
    const data = await res.json();
    renderFaceResult(data);
  } catch {
    showToast("Không kết nối được server", "error");
    setResultEmpty();
  }
}

// ── Plate recognition ─────────────────────────────────────────
async function recognizePlate(formData) {
  setResultLoading("Đang đọc biển số xe...");
  try {
    const res = await apiFetch("/recognize-plate", { method: "POST", body: formData });
    if (!res.ok) { showToast("Lỗi server " + res.status, "error"); setResultEmpty(); return; }
    const data = await res.json();
    renderPlateResult(data);
  } catch {
    showToast("Không kết nối được server", "error");
    setResultEmpty();
  }
}

// ── Result rendering helpers ──────────────────────────────────
function setResultLoading(msg = "Đang nhận diện...") {
  currentStudentId = null;
  document.getElementById("resultArea").innerHTML = `
    <div class="result-empty">
      <i class="fa-solid fa-spinner fa-spin" style="font-size:40px;color:#3b82f6"></i>
      <p>${escHtml(msg)}</p>
    </div>`;
}

function setResultEmpty() {
  currentStudentId = null;
  const hints = {
    face:  { icon: "fa-user-slash",  text: "Chưa nhận diện", sub: "Hướng camera vào khuôn mặt rồi nhấn Nhận diện" },
    plate: { icon: "fa-car-side",    text: "Chưa đọc biển số", sub: "Hướng camera vào biển số xe rồi nhấn Đọc biển số" },
  };
  const h = hints[currentMode] || hints.face;
  document.getElementById("resultArea").innerHTML = `
    <div class="result-empty">
      <i class="fa-solid ${h.icon}"></i>
      <p>${h.text}</p>
      <small>${h.sub}</small>
    </div>`;
}

function escHtml(s) {
  if (!s) return "—";
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

// ── Render face result ────────────────────────────────────────
function renderFaceResult(data) {
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
      <div class="student-card-top face-top">
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
          <span class="info-label">Biển số xe</span>
          <span class="info-value">${escHtml(s.plate_number) || "Chưa đăng ký"}</span>
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

// ── Render plate result ───────────────────────────────────────
function renderPlateResult(data) {
  if (!data.plate_number && !data.raw_text) {
    document.getElementById("resultArea").innerHTML = `
      <div class="result-empty">
        <i class="fa-solid fa-car-side" style="color:#f59e0b"></i>
        <p>Không đọc được biển số</p>
        <small>Thử lại với ảnh rõ hơn, đủ ánh sáng</small>
      </div>`;
    return;
  }

  const plateDisplay = data.plate_number || data.raw_text;
  const conf = data.confidence ? `${Math.round(data.confidence * 100)}%` : "";

  // Có tìm thấy học sinh không?
  if (data.student) {
    const s = data.student;
    currentStudentId = s.id;

    document.getElementById("resultArea").innerHTML = `
      <div class="plate-result-card">
        <div class="plate-number-display">
          <div class="plate-number-text">${escHtml(plateDisplay)}</div>
          <div class="plate-number-label">
            <i class="fa-solid fa-car"></i> Biển số xe
            ${conf ? `· Độ tin cậy: ${conf}` : ""}
          </div>
        </div>

        <div class="student-card-top plate-top">
          <div class="student-avatar"><i class="fa-solid fa-user-graduate"></i></div>
          <div>
            <div class="student-name">${escHtml(s.full_name)}</div>
            <div class="student-meta">${escHtml(s.class_name)} · ${escHtml(s.student_code)}</div>
          </div>
          <div class="confidence-pill" style="background:rgba(255,255,255,0.2);border:1.5px solid rgba(255,255,255,0.5);color:white">
            Tìm thấy
          </div>
        </div>

        <div class="student-info">
          <div class="info-row">
            <span class="info-label">SĐT học sinh</span>
            <span class="info-value">${escHtml(s.phone)}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Biển số xe</span>
            <span class="info-value">${escHtml(s.plate_number)}</span>
          </div>
        </div>

        <div class="violation-form">
          <h3><i class="fa-solid fa-triangle-exclamation" style="color:#ef4444;margin-right:6px"></i>Ghi vi phạm</h3>
          <select id="violationType">
            <option>Không đội mũ bảo hiểm</option>
            <option>Không đồng phục</option>
            <option>Đi trễ</option>
            <option>Dùng điện thoại</option>
            <option>Không đeo thẻ</option>
            <option>Gây mất trật tự</option>
            <option>Khác</option>
          </select>
          <textarea id="violationNote" placeholder="Ghi chú thêm (không bắt buộc)..."></textarea>
          <button class="btn-save-violation" onclick="saveViolation()">
            <i class="fa-solid fa-floppy-disk"></i> Lưu vi phạm
          </button>
        </div>
      </div>`;

  } else {
    // Đọc được biển số nhưng không tìm thấy học sinh
    currentStudentId = null;
    document.getElementById("resultArea").innerHTML = `
      <div class="plate-result-card">
        <div class="plate-number-display">
          <div class="plate-number-text">${escHtml(plateDisplay)}</div>
          <div class="plate-number-label">
            <i class="fa-solid fa-car"></i> Biển số xe
            ${conf ? `· Độ tin cậy: ${conf}` : ""}
          </div>
        </div>
        <div class="result-empty" style="border-radius:0;background:transparent;padding:20px 20px 24px">
          <i class="fa-solid fa-user-slash" style="font-size:36px;color:#64748b"></i>
          <p style="margin-top:8px">Không tìm thấy học sinh</p>
          <small>Biển số chưa được đăng ký trong hệ thống</small>
        </div>
      </div>`;
  }
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
