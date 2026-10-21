// students.js — Chỉ dành cho teacher/admin
requireAuth();
requireTeacher();
renderNav("students");

let allStudents = [];

async function loadStudents() {
  try {
    const res = await apiFetch("/students");
    if (!res.ok) { showError("Không tải được danh sách học sinh (lỗi " + res.status + ")"); return; }
    allStudents = await res.json();

    const classes  = new Set(allStudents.map(s => s.class_name).filter(Boolean));
    const withFace = allStudents.filter(s => s.face_label).length;

    document.getElementById("studentCount").textContent = allStudents.length;
    document.getElementById("classCount").textContent   = classes.size;
    document.getElementById("faceCount").textContent    = withFace;

    // Cập nhật bộ lọc lớp
    buildClassFilter(classes);
    filterStudents(true);
  } catch (e) {
    console.error("loadStudents:", e);
    showError(e instanceof TypeError && /fetch|network/i.test(e.message)
      ? "Không kết nối được server"
      : "Lỗi hiển thị danh sách: " + e.message);
  }
}

// "10A2" -> "10"; sắp xếp tự nhiên để 10A2 đứng trước 10A10
const khoiOf = (cls) => (String(cls || "").match(/^\d+/) || [""])[0];
const natCmp = (a, b) => String(a).localeCompare(String(b), "vi", { numeric: true, sensitivity: "base" });

let classesByKhoi = {}; // { "10": ["10A1","10A2",...], ... }
let activeKhoi = "";

function buildClassFilter(classes) {
  const keepLop = document.getElementById("lopFilter")?.value || "";
  classesByKhoi = {};
  [...classes].forEach(cls => {
    const k = khoiOf(cls);
    (classesByKhoi[k] = classesByKhoi[k] || []).push(cls);
  });
  Object.values(classesByKhoi).forEach(list => list.sort(natCmp));

  // Nếu khối đang chọn không còn tồn tại thì quay về "Tất cả"
  if (activeKhoi && !classesByKhoi[activeKhoi]) activeKhoi = "";

  const bar = document.getElementById("classFilterBar");
  if (bar) {
    const khois = Object.keys(classesByKhoi).sort(natCmp);
    bar.innerHTML =
      `<button class="filter-btn ${activeKhoi === "" ? "active" : ""}" onclick="setKhoiFilter('', this)">Tất cả</button>` +
      khois.map(k => `<button class="filter-btn ${activeKhoi === k ? "active" : ""}" onclick="setKhoiFilter('${k}', this)">Khối ${k}</button>`).join("");
  }
  populateLopSelect(keepLop);
}

// Dropdown lớp chỉ hiện các lớp thuộc khối đang chọn (đã sắp xếp)
function populateLopSelect(keep = "") {
  const sel = document.getElementById("lopFilter");
  if (!sel) return;
  sel.innerHTML = `<option value="">${activeKhoi ? `Tất cả lớp khối ${activeKhoi}` : "Tất cả lớp"}</option>`;

  const khois = activeKhoi ? [activeKhoi] : Object.keys(classesByKhoi).sort(natCmp);
  khois.forEach(k => {
    const addOpt = (parent, cls) => {
      const o = document.createElement("option");
      o.value = cls; o.textContent = cls;
      parent.appendChild(o);
    };
    if (activeKhoi) {
      (classesByKhoi[k] || []).forEach(cls => addOpt(sel, cls));
    } else {
      const g = document.createElement("optgroup");
      g.label = `Khối ${k}`;
      (classesByKhoi[k] || []).forEach(cls => addOpt(g, cls));
      sel.appendChild(g);
    }
  });
  sel.value = keep && [...sel.options].some(o => o.value === keep) ? keep : "";
}

function setKhoiFilter(khoi, btn) {
  activeKhoi = khoi;
  document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  populateLopSelect(); // đổi khối → làm mới danh sách lớp, bỏ lớp cũ
  filterStudents();
}

function filterStudents(keepPage = false) {
  const q      = (document.getElementById("searchInput")?.value || "").toLowerCase();
  const lopVal = document.getElementById("lopFilter")?.value || "";

  let filtered = allStudents;

  if (activeKhoi) filtered = filtered.filter(s => khoiOf(s.class_name) === activeKhoi);
  if (lopVal)     filtered = filtered.filter(s => s.class_name === lopVal);

  if (q) {
    filtered = filtered.filter(s =>
      (s.full_name    || "").toLowerCase().includes(q) ||
      (s.student_code || "").toLowerCase().includes(q) ||
      (s.class_name   || "").toLowerCase().includes(q)
    );
  }

  renderTable(filtered, keepPage === true);
}

function showError(msg) {
  const tbody = document.getElementById("studentTable");
  if (tbody)
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:var(--danger);padding:32px">${escapeHtml(msg)}</td></tr>`;
}


const PAGE_SIZE = 50;
let viewList = [], page = 1;

const initials = (n) => (n || "?").trim().split(/\s+/).slice(-2).map(w => w[0]).join("").toUpperCase();

function renderTable(students, keepPage = false) {
  viewList = students;
  if (!keepPage) page = 1;
  const pages = Math.max(1, Math.ceil(viewList.length / PAGE_SIZE));
  page = Math.min(page, pages);

  const tbody = document.getElementById("studentTable");
  if (!viewList.length) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:var(--gray-400);padding:32px">Chưa có học sinh nào</td></tr>`;
    renderPager(0, 1);
    return;
  }
  const start = (page - 1) * PAGE_SIZE;
  tbody.innerHTML = viewList.slice(start, start + PAGE_SIZE).map((s, i) => {
    const img = apiAssetUrl(s.face_image_url, { withToken: true });
    return `
    <tr>
      <td style="color:var(--gray-400)">${start + i + 1}</td>
      <td><span class="badge badge-blue">${escapeHtml(s.student_code)}</span></td>
      <td>
        <div class="stu-cell">
          <span class="stu-thumb">${escapeHtml(initials(s.full_name))}${img ? `<img loading="lazy" decoding="async" src="${escapeHtml(img)}" alt="" onerror="this.remove()">` : ""}</span>
          <strong>${escapeHtml(s.full_name)}</strong>
        </div>
      </td>
      <td>${escapeHtml(s.class_name)}</td>
      <td style="font-size:13px">${escapeHtml(s.phone) || "—"}</td>
      <td>
        <div class="action-btns">
          <button class="btn-sm edit-btn"   onclick="openEdit(${s.id})"><i class="fa-solid fa-pen"></i></button>
          <button class="btn-sm delete-btn" onclick="deleteStudent(${s.id})"><i class="fa-solid fa-trash"></i></button>
        </div>
      </td>
    </tr>`;
  }).join("");
  renderPager(viewList.length, pages);
}

function renderPager(total, pages) {
  const el = document.getElementById("pager");
  if (!el) return;
  if (total <= PAGE_SIZE) { el.innerHTML = total ? `<span class="pager-info">${total} học sinh</span>` : ""; return; }
  el.innerHTML = `
    <span class="pager-info">${(page - 1) * PAGE_SIZE + 1}–${Math.min(page * PAGE_SIZE, total)} / ${total} học sinh</span>
    <div class="pager-btns">
      <button class="btn-sm" onclick="goPage(${page - 1})" ${page <= 1 ? "disabled" : ""}><i class="fa-solid fa-chevron-left"></i></button>
      <span class="pager-cur">${page} / ${pages}</span>
      <button class="btn-sm" onclick="goPage(${page + 1})" ${page >= pages ? "disabled" : ""}><i class="fa-solid fa-chevron-right"></i></button>
    </div>`;
}

function goPage(n) {
  page = n;
  renderTable(viewList, true);
  document.querySelector(".table-card")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function showModal() {
  document.getElementById("studentModal").classList.add("open");
  document.body.classList.add("modal-open"); // bản cũ chỉ khoá cuộn khi THÊM, không khoá khi SỬA
}

function openModal() {
  document.getElementById("modalTitle").textContent = "Thêm học sinh";
  document.getElementById("editingId").value = "";
  ["studentCode","fullName","className","faceLabel","phone"].forEach(id => {
    document.getElementById(id).value = "";
  });
  showModal();
}

function openEdit(id) {
  const s = allStudents.find(x => x.id === id);
  if (!s) return;
  document.getElementById("modalTitle").textContent   = "Chỉnh sửa học sinh";
  document.getElementById("editingId").value          = id;
  document.getElementById("studentCode").value        = s.student_code;
  document.getElementById("fullName").value           = s.full_name;
  document.getElementById("className").value          = s.class_name;
  document.getElementById("faceLabel").value          = s.face_label || "";
  document.getElementById("phone").value              = s.phone || "";
  showModal();
}

function closeModal() {
  document.getElementById("studentModal").classList.remove("open");
  document.body.classList.remove("modal-open");
}

async function saveStudent() {
  const id   = document.getElementById("editingId").value;
  const body = {
    student_code: document.getElementById("studentCode").value.trim(),
    full_name:    document.getElementById("fullName").value.trim(),
    class_name:   document.getElementById("className").value.trim(),
    face_label:   document.getElementById("faceLabel").value.trim() || null,
    phone:        document.getElementById("phone").value.trim(),
  };

  if (!body.full_name || !body.class_name) {
    alert("Vui lòng điền đầy đủ thông tin bắt buộc (*)"); return;
  }

  try {
    const res = await apiFetch(id ? `/students/${id}` : "/students", {
      method: id ? "PUT" : "POST",
      body:   JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(err.detail || "Lỗi khi lưu học sinh"); return;
    }
    closeModal();
    loadStudents();
  } catch { alert("Lỗi kết nối server"); }
}

async function deleteStudent(id) {
  const s    = allStudents.find(x => x.id === id);
  const name = s ? s.full_name : `ID ${id}`;
  if (!confirm(`Xóa học sinh "${name}"? Tất cả vi phạm liên quan cũng sẽ bị xóa.`)) return;
  try {
    const res = await apiFetch(`/students/${id}`, { method: "DELETE" });
    if (!res.ok) { const err = await res.json().catch(() => ({})); alert(err.detail || "Xóa thất bại"); return; }
    loadStudents();
  } catch { alert("Lỗi kết nối server"); }
}

if (isTeacher()) loadStudents(); // student đang bị chuyển trang, không gọi API nữa

/** Nút "Đồng bộ lại": học khuôn mặt người mới trong known_faces + tạo hồ sơ còn thiếu. */
async function importFromFolders() {
  const btn = document.getElementById("importBtn");
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang đồng bộ...';
  try {
    const res  = await apiFetch("/import-from-folders", { method: "POST" });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) { alert("Lỗi: " + (data.detail || "Không xác định")); return; }
    alert(data.message + (data.errors?.length ? "\n\nLỗi:\n" + data.errors.join("\n") : ""));
    loadStudents();
  } catch {
    alert("Không kết nối được server");
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-rotate"></i> Đồng bộ lại';
  }
}

// ───────────────────────── Nhập danh sách Excel ─────────────────────────
const el = (id) => document.getElementById(id);
function openRoster() { el("rosterModal").classList.add("open"); document.body.classList.add("modal-open"); rosterReset(); }
function closeRoster() { el("rosterModal").classList.remove("open"); document.body.classList.remove("modal-open"); }
function rosterReset() { el("rosterResult").innerHTML = ""; el("rosterApplyBtn").style.display = "none"; }

const li = (items, fmt) => items.length ? `<div class="res-list">${items.map(fmt).join("<br>")}</div>` : "";

async function runRoster(apply) {
  const file = el("rosterFile").files[0];
  if (!file) { alert("Hãy chọn file Excel (.xlsx)"); return; }
  if (apply && !confirm("Áp dụng thay đổi vào danh sách học sinh?")) return;
  const fd = new FormData();
  fd.append("file", file);
  fd.append("apply", apply ? "true" : "false");
  fd.append("allow_move", el("rosterMove").checked ? "true" : "false");
  const box = el("rosterResult");
  box.innerHTML = "<p>Đang xử lý...</p>";
  try {
    const res = await apiFetch("/students/import-roster", { method: "POST", body: fd });
    const d = await res.json().catch(() => ({}));
    if (!res.ok) { box.innerHTML = `<p style="color:var(--danger)">${escapeHtml(d.detail || "Lỗi " + res.status)}</p>`; return; }
    const c = d.counts, move = el("rosterMove").checked;
    const nameOnly = d.updates.filter(u => !u.move);
    const moves = d.updates.filter(u => u.move);
    box.innerHTML = `
      <div class="res-sum">
        <span>${d.rows_in_file} dòng trong file</span>
        <span>${c.updates - d.moves} sửa tên có dấu</span>
        <span>${d.unchanged} đã đúng</span>
        <span class="${d.moves ? "warn" : ""}">${d.moves} đổi lớp${d.moves && !move ? " (chưa bật)" : ""}</span>
        <span class="${c.ambiguous ? "warn" : ""}">${c.ambiguous} cần xử lý tay</span>
        <span class="${c.not_found ? "warn" : ""}">${c.not_found} không có trong hệ thống</span>
        <span>${c.not_in_list} không có trong file</span>
      </div>
      ${apply ? `<p><b>Đã áp dụng ${d.applied_count} thay đổi.</b></p>` : ""}
      ${d.warnings.length ? `<div class="res-title">Cảnh báo</div>${li(d.warnings, escapeHtml)}` : ""}
      ${nameOnly.length ? `<div class="res-title">Sửa tên${c.updates - d.moves > nameOnly.length ? " (hiện 200 đầu)" : ""}</div>${li(nameOnly, u => `${escapeHtml(u.old_name)} → <b>${escapeHtml(u.new_name)}</b> (${escapeHtml(u.old_class)})`)}` : ""}
      ${moves.length ? `<div class="res-title">Đổi lớp</div>${li(moves, u => `${escapeHtml(u.new_name)}: ${escapeHtml(u.old_class)} → <b>${escapeHtml(u.new_class)}</b>`)}` : ""}
      ${c.ambiguous ? `<div class="res-title">Cần xử lý tay (trùng tên)</div>${li(d.ambiguous, a => `${escapeHtml(a.name)} (${escapeHtml(a.class_name)}) — ${escapeHtml(a.reason)}`)}` : ""}
      ${c.not_found ? `<div class="res-title">Có trong file, chưa có trong hệ thống</div>${li(d.not_found, a => `${escapeHtml(a.name)} (${escapeHtml(a.class_name)})`)}` : ""}
      ${c.not_in_list ? `<div class="res-title">Có trong hệ thống, không thấy trong file (cùng các lớp có trong file)</div>${li(d.not_in_list, a => `${escapeHtml(a.name)} (${escapeHtml(a.class_name)})`)}` : ""}`;
    el("rosterApplyBtn").style.display = !apply && (nameOnly.length || (move && moves.length)) ? "" : "none";
    if (apply) loadStudents();
  } catch { box.innerHTML = '<p style="color:var(--danger)">Không kết nối được server</p>'; }
}

// ───────────────────────── Chuyển năm học (admin) ─────────────────────────
if (getRole() === "admin") el("rolloverBtn").style.display = "";
function closeRollover() { el("rolloverModal").classList.remove("open"); document.body.classList.remove("modal-open"); }

async function openRollover() {
  el("rolloverModal").classList.add("open"); document.body.classList.add("modal-open");
  const body = el("rolloverBody");
  body.innerHTML = "<p>Đang tải bản xem trước...</p>";
  try {
    const res = await apiFetch("/rollover/preview");
    const d = await res.json().catch(() => ({}));
    if (!res.ok) { body.innerHTML = `<p style="color:var(--danger)">${escapeHtml(d.detail || "Lỗi " + res.status)}</p>`; return; }
    body.innerHTML = `
      <div class="info-box">
        Năm học hiện tại: <b>${escapeHtml(d.current)}</b> → chuyển sang <b>${escapeHtml(d.next)}</b>.<br>
        Lớp 10 lên 11, lớp 11 lên 12; lớp 12 <b>ra trường</b> (bị ẩn khỏi nhận diện và danh sách, lịch sử vi phạm vẫn được giữ).
        Hệ thống tự sao lưu dữ liệu trước khi chuyển và <b>không thể chạy lại</b> cho cùng một năm học.
      </div>
      <div class="res-sum">
        <span>${d.promote} em lên lớp</span>
        <span class="warn">${d.graduate} em ra trường</span>
        <span class="${d.skip ? "warn" : ""}">${d.skip} em giữ nguyên (tên lớp lạ)</span>
      </div>
      <div class="res-title">Lớp lên lớp</div>${li(d.class_map, m => `${escapeHtml(m.from)} → <b>${escapeHtml(m.to)}</b> (${m.students} em)`)}
      <div class="res-title">Lớp ra trường</div>${li(d.graduate_classes, g => `${escapeHtml(g[0])} (${g[1]} em)`)}
      ${d.skip_classes.length ? `<div class="res-title">Tên lớp không nhận ra</div>${li(d.skip_classes, escapeHtml)}` : ""}
      <div class="form-group" style="margin-top:14px">
        <label>Để xác nhận, gõ năm học mới: <b>${escapeHtml(d.next)}</b></label>
        <input type="text" id="rolloverConfirm" placeholder="${escapeHtml(d.next)}" autocomplete="off" />
      </div>
      <p style="font-size:12.5px;color:var(--gray-400)">Sau khi chuyển: thêm ảnh học sinh khối 10 mới vào thư mục known_faces, rồi bấm "Đồng bộ lại".</p>
      <button class="save-btn" id="rolloverRun" onclick="runRollover('${escapeHtml(d.next)}')">Chuyển sang năm học ${escapeHtml(d.next)}</button>`;
  } catch { body.innerHTML = '<p style="color:var(--danger)">Không kết nối được server</p>'; }
}

async function runRollover(next) {
  if (el("rolloverConfirm").value.trim() !== next) { alert("Chưa gõ đúng năm học mới: " + next); return; }
  const btn = el("rolloverRun");
  btn.disabled = true; btn.textContent = "Đang chuyển...";
  try {
    const fd = new FormData();
    fd.append("confirm_year", next);
    const res = await apiFetch("/rollover", { method: "POST", body: fd });
    const d = await res.json().catch(() => ({}));
    if (!res.ok) { alert(d.detail || "Chuyển năm học thất bại"); btn.disabled = false; btn.textContent = "Thử lại"; return; }
    el("rolloverBody").innerHTML = `<div class="info-box"><b>${escapeHtml(d.message)}</b><br>Bản sao lưu: ${escapeHtml(d.backup)}</div>`;
    loadStudents();
  } catch { alert("Không kết nối được server"); btn.disabled = false; btn.textContent = "Thử lại"; }
}
