// face.js — Trang nhận diện (index.html): đóng băng khung hình khi chụp + hiệu ứng quét mặt
requireAuth();
renderNav("index");

const $ = (id) => document.getElementById(id);
const IS_TEACHER = isTeacher(); // student: chỉ xem kết quả nhận diện
const video = $("video"), stage = $("stage"), freezeImg = $("freezeImg");
let stream = null, facing = "user", busy = false, freezeUrl = null;

const TYPES = ["Không đồng phục","Đi trễ","Dùng điện thoại","Không đeo thẻ","Không đội mũ bảo hiểm","Gây mất trật tự","Khác"];
const BADGE = { ok:"fa-check", unknown:"fa-question", fail:"fa-xmark" };
const CONF_OK = 65; // % độ khớp từ mức này mới coi là chắc chắn; thấp hơn phải xác nhận thủ công
const MIN_SCAN_MS = 1400; // quét tối thiểu để animation đủ đẹp dù server trả nhanh

const esc = escapeHtml;
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const initials = (n) => (n || "?").trim().split(/\s+/).slice(-2).map(w => w[0]).join("").toUpperCase();

function setState(state, text) {
  stage.dataset.state = state;
  if (text) $("statusText").textContent = text;
  if (BADGE[state]) $("camBadge").innerHTML = `<i class="fa-solid ${BADGE[state]}"></i>`;
}

// ── Camera ──────────────────────────────────────────────
function cameraError(e) {
  const map = {
    NotAllowedError: "Bạn chưa cho phép dùng camera. Bấm biểu tượng ổ khóa trên thanh địa chỉ và bật Camera.",
    NotFoundError: "Không tìm thấy camera trên thiết bị này.",
    NotReadableError: "Camera đang được ứng dụng khác sử dụng. Hãy đóng ứng dụng đó rồi thử lại.",
    OverconstrainedError: "Camera không hỗ trợ cấu hình yêu cầu.",
    SecurityError: "Trình duyệt chặn camera. Hãy mở trang bằng HTTPS.",
  };
  return map[e.name] || "Không mở được camera (" + (e.message || e.name) + ")";
}

async function startCamera() {
  if (!navigator.mediaDevices?.getUserMedia) {
    toast("Camera chỉ hoạt động trên HTTPS hoặc localhost. Hãy mở trang bằng địa chỉ https://", true, 6000);
    return;
  }
  try {
    if (stream) stream.getTracks().forEach(t => t.stop());
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: facing, width: { ideal: 1280 }, height: { ideal: 960 } }, audio: false,
    });
    video.srcObject = stream;
    await video.play().catch(() => {});
    if (facing === "user") stage.setAttribute("data-mirror", ""); else stage.removeAttribute("data-mirror");
    releaseFreeze();
    setState("live", "Đưa khuôn mặt vào khung");
  } catch (e) {
    toast(cameraError(e), true, 5000);
  }
}

function stopCamera() {
  if (stream) stream.getTracks().forEach(t => t.stop());
  stream = null; video.srcObject = null;
  releaseFreeze();
  setState("idle");
}

async function flipCamera() {
  facing = facing === "user" ? "environment" : "user";
  await startCamera();
}

function releaseFreeze() {
  if (freezeUrl) { URL.revokeObjectURL(freezeUrl); freezeUrl = null; }
  freezeImg.removeAttribute("src");
}

// Quay lại camera trực tiếp sau khi xem kết quả
function resumeLive() {
  releaseFreeze();
  if (stream) {
    if (facing === "user") stage.setAttribute("data-mirror", ""); else stage.removeAttribute("data-mirror");
    setState("live", "Đưa khuôn mặt vào khung");
  } else setState("idle");
}

// ── Chụp: dừng ngay khung hình, rồi quét ────────────────
async function captureAndRecognize() {
  if (busy) return;
  if (!stream || !video.videoWidth) { toast("Hãy bật camera trước", true); return; }

  const c = $("canvas");
  c.width = video.videoWidth; c.height = video.videoHeight;
  c.getContext("2d").drawImage(video, 0, 0, c.width, c.height); // ảnh GỐC (không lật) gửi cho AI
  const blob = await new Promise(r => c.toBlob(r, "image/jpeg", 0.9));

  releaseFreeze();
  freezeUrl = URL.createObjectURL(blob);
  freezeImg.src = freezeUrl;          // hiện đúng khung hình lúc chụp
  video.pause();
  await runRecognition(blob, "capture.jpg");
}

async function uploadImage() {
  const file = $("imageInput").files[0];
  if (!file) return;
  if (busy) return;
  releaseFreeze();
  freezeUrl = URL.createObjectURL(file);
  freezeImg.src = freezeUrl;
  stage.removeAttribute("data-mirror");
  $("imageInput").value = "";
  await runRecognition(file, file.name);
}

async function runRecognition(blob, name) {
  busy = true;
  $("shutter").disabled = true;
  setState("scanning", "Đang quét khuôn mặt...");
  showScanning();

  const fd = new FormData();
  fd.append("file", blob, name);
  const t0 = Date.now();
  let data = null, errMsg = "";
  try {
    const res = await apiFetch("/recognize-face", { method: "POST", body: fd });
    if (res.ok) data = await res.json(); else errMsg = "Lỗi server (" + res.status + ")";
  } catch { errMsg = "Không kết nối được server"; }

  const wait = MIN_SCAN_MS - (Date.now() - t0);
  if (wait > 0) await sleep(wait);

  if (errMsg) {
    setState("fail", errMsg); renderEmpty("fa-circle-exclamation", errMsg, "Thử lại sau ít phút");
  } else if (!data.faces || !data.faces.length) {
    setState("fail", "Không thấy khuôn mặt"); renderEmpty("fa-user-slash", "Không nhận diện được", "Chụp lại rõ mặt hơn");
  } else if (data.faces[0].status === "unknown") {
    setState("fail", "Không nhận ra"); renderEmpty("fa-user-slash", "Không nhận ra khuôn mặt này", "Độ giống cao nhất chỉ " + Math.round(data.faces[0].score * 100) + "% — chưa đủ để kết luận");
  } else if (!data.faces[0].id) {
    setState("unknown", "Chưa có hồ sơ");
    renderEmpty("fa-circle-question", "Có ảnh khuôn mặt nhưng chưa có hồ sơ", IS_TEACHER ? "Vào trang Học sinh → Đồng bộ lại để tạo hồ sơ" : "Hãy báo giáo viên");
  } else {
    setState("ok", data.faces[0].full_name); renderStudent(data.faces[0]);
    if (data.faces.length > 1) toast("Có " + data.faces.length + " khuôn mặt trong ảnh, đang hiển thị người rõ nhất.");
  }
  busy = false;
  $("shutter").disabled = false;
  await sleep(2600);
  if (!busy && stage.dataset.state !== "scanning") resumeLive(); // tự trở về camera, kết quả vẫn giữ ở thẻ bên dưới
  if (stream) video.play().catch(() => {});
}

// ── Kết quả ─────────────────────────────────────────────
function showScanning() {
  $("studentProfile").innerHTML = `<div class="res-empty"><i class="fa-solid fa-spinner fa-spin"></i><p>Đang phân tích...</p><small>Vui lòng giữ yên</small></div>`;
}
function renderEmpty(icon, title, sub) {
  $("studentProfile").innerHTML = `<div class="res-empty"><i class="fa-solid ${icon}"></i><p>${esc(title)}</p><small>${esc(sub)}</small></div>`;
}

function renderStudent(s) {
  const acc = Math.round(s.score * 100), sure = acc >= CONF_OK;
  const col = sure ? "#22d3a5" : "#f97316";
  const img = s.face_image_url || "";
  $("studentProfile").innerHTML = `
    <div class="res-card">
      <div class="res-head">
        <div class="res-avatar"><i class="fa-solid fa-user-graduate"></i>${img ? `<img data-auth-src="${esc(img)}" alt="">` : ""}</div>
        <div style="min-width:0">
          <div class="res-name">${esc(s.full_name)}</div>
          <div class="res-meta">${[s.class_name, s.student_code, s.phone].filter(Boolean).map(esc).join(" · ")}</div>
        </div>
        <div class="res-score" style="background:${col}22;color:${col}">${acc}%</div>
      </div>
      <div class="res-bar"><b style="width:${acc}%;background:${col}"></b></div>
      <div class="res-conf ${sure ? "ok" : "warn"}"><i class="fa-solid ${sure ? "fa-circle-check" : "fa-triangle-exclamation"}"></i>
        <span>${sure ? "Độ khớp cao" : "Độ khớp thấp — hãy đối chiếu ảnh hoặc hỏi lại học sinh trước khi ghi vi phạm"}</span></div>
      ${IS_TEACHER ? `
      <div>
        <div class="res-label">Loại vi phạm</div>
        <div class="chips" id="chips">${TYPES.map((t, i) => `<button class="chip${i === 0 ? " on" : ""}" onclick="pickType(this)">${t}</button>`).join("")}</div>
      </div>
      <div>
        <div class="res-label">Ghi chú</div>
        <textarea id="violationNote" placeholder="Thêm ghi chú (không bắt buộc)..."></textarea>
      </div>
      ${sure ? "" : `<label class="res-confirm"><input type="checkbox" onchange="document.getElementById('saveBtn').disabled=!this.checked"> Tôi đã xác nhận đúng học sinh này</label>`}
      <button class="btn-save" id="saveBtn" onclick="saveViolation(${s.id})" ${sure ? "" : "disabled"}><i class="fa-solid fa-floppy-disk"></i> Lưu vi phạm</button>
      ` : ""}
    </div>`;
  hydrateAuthImages($("studentProfile"));
  if (innerWidth <= 768) $("studentProfile").scrollIntoView({ behavior: "smooth", block: "start" });
}
function pickType(el) {
  document.querySelectorAll("#chips .chip").forEach(c => c.classList.remove("on"));
  el.classList.add("on");
}

async function saveViolation(id) {
  const btn = $("saveBtn"), type = document.querySelector("#chips .chip.on")?.textContent || TYPES[0];
  if (btn.disabled) return;
  let saved = false;
  btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang lưu...';
  try {
    const res = await apiFetch("/violations", { method: "POST", body: JSON.stringify({ student_id: id, violation_type: type, note: $("violationNote").value }) });
    if (!res.ok) { const e = await res.json().catch(() => ({})); toast(e.detail || "Lỗi khi lưu vi phạm", true); return; }
    toast("Đã lưu vi phạm");
    saved = true;
    btn.innerHTML = '<i class="fa-solid fa-check"></i> Đã lưu';  // giữ khóa để không bấm đúp ra 2 bản ghi
    $("violationNote").value = "";
    loadRecentViolations();
  } catch { toast("Lỗi kết nối server", true); }
  finally { if (!saved) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Lưu vi phạm'; } }
}

// ── Vi phạm gần đây ─────────────────────────────────────
function fmtDate(iso) {
  const s = iso && !/Z|\+/.test(iso) ? iso + "Z" : iso, d = new Date(s);
  return d.toLocaleDateString("vi-VN") + " " + d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
}
async function loadRecentViolations() {
  if (!IS_TEACHER) return;
  const box = $("recentViolations");
  try {
    const res = await apiFetch("/violations?limit=5");
    if (!res.ok) return;
    const data = await res.json();
    box.innerHTML = data.length ? data.map(v => `
      <div class="rv">
        <div class="rv-av">${esc(initials(v.student_name))}</div>
        <div class="rv-main"><b>${esc(v.student_name)}</b><small>${esc(v.class_name)} · ${esc(v.violation_type)}</small></div>
        <div class="rv-time">${fmtDate(v.created_at)}</div>
      </div>`).join("") : `<div class="res-empty"><small>Chưa có vi phạm nào</small></div>`;
  } catch {}
}

loadRecentViolations();
if (!IS_TEACHER) document.querySelector(".recent-card")?.remove();
