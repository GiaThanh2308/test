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
    const img = s.face_image_url || "";
    return `
    <tr>
      <td style="color:var(--gray-400)">${start + i + 1}</td>
      <td><span class="badge badge-blue">${escapeHtml(s.student_code)}</span></td>
      <td>
        <div class="stu-cell">
          <span class="stu-thumb">${escapeHtml(initials(s.full_name))}${img ? `<img decoding="async" data-auth-src="${escapeHtml(img)}" alt="">` : ""}</span>
          <strong>${escapeHtml(s.full_name)}</strong>
        </div>
      </td>
      <td>${escapeHtml(s.class_name)}</td>
      <td style="font-size:13px">${escapeHtml(s.phone) || "—"}</td>
      <td>
        <div class="action-btns">
          <button class="btn-sm edit-btn" title="Sửa" aria-label="Sửa ${escapeHtml(s.full_name)}"   onclick="openEdit(${s.id})"><i class="fa-solid fa-pen"></i></button>
          <button class="btn-sm delete-btn" title="Xóa" aria-label="Xóa ${escapeHtml(s.full_name)}" onclick="deleteStudent(${s.id})"><i class="fa-solid fa-trash"></i></button>
        </div>
      </td>
    </tr>`;
  }).join("");
  hydrateAuthImages(tbody);
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
    toast("Vui lòng điền Họ tên và Lớp", true); return;
  }

  try {
    const res = await apiFetch(id ? `/students/${id}` : "/students", {
      method: id ? "PUT" : "POST",
      body:   JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      toast(err.detail || "Lỗi khi lưu học sinh", true); return;
    }
    closeModal();
    toast("Đã lưu học sinh");
    loadStudents();
  } catch { toast("Lỗi kết nối server", true); }
}

async function deleteStudent(id) {
  const s    = allStudents.find(x => x.id === id);
  const name = s ? s.full_name : `ID ${id}`;
  const ok = await confirmDialog({
    title: "Xóa học sinh",
    message: `Xóa "${name}"? Toàn bộ vi phạm của học sinh này cũng bị xóa, và hồ sơ sẽ không tự tạo lại khi đồng bộ.`,
    okText: "Xóa", danger: true,
  });
  if (!ok) return;
  try {
    const res = await apiFetch(`/students/${id}`, { method: "DELETE" });
    if (!res.ok) { const err = await res.json().catch(() => ({})); toast(err.detail || "Xóa thất bại", true); return; }
    toast("Đã xóa học sinh");
    loadStudents();
  } catch { toast("Lỗi kết nối server", true); }
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
    if (!res.ok) { toast("Lỗi: " + (data.detail || "Không xác định"), true, 6000); return; }
    toast(data.message, !!data.errors?.length, 7000);
    if (data.errors?.length) console.error(data.errors);
    loadStudents();
  } catch {
    toast("Không kết nối được server", true);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-rotate"></i> Đồng bộ lại';
  }
}
// Esc hoặc bấm nền tối để đóng hộp thoại thêm/sửa
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });
document.getElementById("studentModal").addEventListener("mousedown", (e) => { if (e.target.id === "studentModal") closeModal(); });
