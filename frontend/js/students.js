requireAuth();

const usernameEl = document.getElementById("usernameDisplay");
if (usernameEl) usernameEl.textContent = localStorage.getItem("username");

let allStudents = [];

async function loadStudents() {
  try {
    const res = await apiFetch("/students");
    if (!res.ok) {
      showError("Không tải được danh sách học sinh (lỗi " + res.status + ")");
      return;
    }
    allStudents = await res.json();

    const classes  = new Set(allStudents.map((s) => s.class_name).filter(Boolean));
    const withFace = allStudents.filter((s) => s.face_label).length;

    document.getElementById("studentCount").textContent = allStudents.length;
    document.getElementById("classCount").textContent   = classes.size;
    document.getElementById("faceCount").textContent    = withFace;

    renderTable(allStudents);
  } catch (err) {
    showError("Không kết nối được server");
  }
}

function showError(msg) {
  const tbody = document.getElementById("studentTable");
  if (tbody) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:var(--danger);padding:32px">${escapeHtml(msg)}</td></tr>`;
  }
}

function escapeHtml(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderTable(students) {
  const tbody = document.getElementById("studentTable");
  if (!students.length) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:var(--gray-400);padding:32px">Chưa có học sinh nào</td></tr>`;
    return;
  }

  tbody.innerHTML = students
    .map(
      (s, i) => `
    <tr>
      <td style="color:var(--gray-400)">${i + 1}</td>
      <td><span class="badge badge-blue">${escapeHtml(s.student_code)}</span></td>
      <td><strong>${escapeHtml(s.full_name)}</strong></td>
      <td>${escapeHtml(s.class_name)}</td>
      <td style="font-size:13px">${escapeHtml(s.phone) || "—"}</td>
      <td style="font-size:13px">${escapeHtml(s.parent_phone) || "—"}</td>
      <td>
        <div class="action-btns">
          <button class="btn-sm btn-ghost"  onclick="openEdit(${s.id})"><i class="fa-solid fa-pen"></i></button>
          <button class="btn-sm btn-danger" onclick="deleteStudent(${s.id})"><i class="fa-solid fa-trash"></i></button>
        </div>
      </td>
    </tr>
  `,
    )
    .join("");
}

function filterStudents() {
  const q = document.getElementById("searchInput").value.toLowerCase();
  // FIX: thêm || "" để tránh crash TypeError khi field là null/undefined
  const filtered = allStudents.filter(
    (s) =>
      (s.full_name    || "").toLowerCase().includes(q) ||
      (s.student_code || "").toLowerCase().includes(q) ||
      (s.class_name   || "").toLowerCase().includes(q),
  );
  renderTable(filtered);
}

function openModal() {
  document.getElementById("modalTitle").textContent = "Thêm học sinh";
  document.getElementById("editingId").value = "";
  ["studentCode", "fullName", "className", "faceLabel", "phone", "parentPhone"].forEach((id) => {
    document.getElementById(id).value = "";
  });
  document.getElementById("studentModal").classList.add("open");
}

function openEdit(id) {
  const s = allStudents.find((x) => x.id === id);
  if (!s) return;
  document.getElementById("modalTitle").textContent   = "Chỉnh sửa học sinh";
  document.getElementById("editingId").value          = id;
  document.getElementById("studentCode").value        = s.student_code;
  document.getElementById("fullName").value           = s.full_name;
  document.getElementById("className").value          = s.class_name;
  document.getElementById("faceLabel").value          = s.face_label || "";
  document.getElementById("phone").value              = s.phone || "";
  document.getElementById("parentPhone").value        = s.parent_phone || "";
  document.getElementById("studentModal").classList.add("open");
}

function closeModal() {
  document.getElementById("studentModal").classList.remove("open");
}

// FIX: đổi tên hàm thành saveStudent để khớp với onclick trong students.html
// (HTML đang gọi createStudent() — cần cập nhật HTML hoặc đặt alias)
async function saveStudent() {
  const id   = document.getElementById("editingId").value;
  const body = {
    student_code: document.getElementById("studentCode").value.trim(),
    full_name:    document.getElementById("fullName").value.trim(),
    class_name:   document.getElementById("className").value.trim(),
    face_label:   document.getElementById("faceLabel").value.trim() || null,
    phone:        document.getElementById("phone").value.trim(),
    parent_phone: document.getElementById("parentPhone").value.trim(),
  };

  if (!body.student_code || !body.full_name || !body.class_name) {
    alert("Vui lòng điền đầy đủ thông tin bắt buộc (*)");
    return;
  }

  const url    = id ? `/students/${id}` : "/students";
  const method = id ? "PUT" : "POST";

  try {
    const res = await apiFetch(url, {
      method,
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(err.detail || "Lỗi khi lưu học sinh");
      return;
    }

    closeModal();
    loadStudents();
  } catch (err) {
    alert("Lỗi kết nối server");
  }
}

// Alias để tương thích với nút "Lưu học sinh" trong students.html đang gọi createStudent()
const createStudent = saveStudent;

async function deleteStudent(id) {
  const s = allStudents.find((x) => x.id === id);
  const name = s ? s.full_name : `ID ${id}`;

  if (!confirm(`Xóa học sinh "${name}"? Tất cả vi phạm liên quan cũng sẽ bị xóa.`)) return;

  try {
    const res = await apiFetch(`/students/${id}`, { method: "DELETE" });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(err.detail || "Xóa thất bại");
      return;
    }

    loadStudents();
  } catch (err) {
    alert("Lỗi kết nối server");
  }
}

loadStudents();
