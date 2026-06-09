// dashboard.js — Trang dashboard dành cho giáo viên/admin
requireAuth();

// Chỉ giáo viên và admin mới vào được
const role = localStorage.getItem("role");
if (role === "security") {
  window.location.href = "scan.html";
}

// Hiện thông tin user
document.getElementById("usernameDisplay").textContent = localStorage.getItem("username") || "---";
const roleBadge = document.getElementById("roleBadge");
if (roleBadge) {
  roleBadge.textContent = role === "admin" ? "Admin" : "Giáo viên";
  roleBadge.style.cssText = `
    font-size:11px;font-weight:700;padding:2px 8px;border-radius:20px;margin-left:8px;
    background:${role === "admin" ? "#fef3c7" : "#eff6ff"};
    color:${role === "admin" ? "#92400e" : "#1e40af"};
  `;
}

// Hiện ngày tháng
const dateEl = document.getElementById("dateDisplay");
if (dateEl) {
  const now = new Date();
  dateEl.textContent = now.toLocaleDateString("vi-VN", {
    weekday: "long", year: "numeric", month: "long", day: "numeric"
  });
}

function escHtml(s) {
  if (!s) return "—";
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString("vi-VN") + " " +
    d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
}

// ── Load summary stats ────────────────────────────────────────
async function loadSummary() {
  try {
    const res  = await apiFetch("/stats/summary");
    if (!res.ok) return;
    const data = await res.json();
    document.getElementById("statStudents").textContent = data.total_students;
    document.getElementById("statToday").textContent    = data.today_violations;
    document.getElementById("statWeek").textContent     = data.week_violations;
    document.getElementById("statMonth").textContent    = data.month_violations;
  } catch(e) {
    console.warn("Không load được stats:", e);
  }
}

// ── Load top violators ────────────────────────────────────────
async function loadTopViolators() {
  const el = document.getElementById("topViolators");
  try {
    const res  = await apiFetch("/stats/top-violators?limit=5");
    if (!res.ok) { el.innerHTML = "<p style='color:#9ca3af'>Không tải được</p>"; return; }
    const data = await res.json();
    if (!data.length) { el.innerHTML = "<p style='color:#9ca3af;text-align:center;padding:16px'>Chưa có dữ liệu</p>"; return; }

    el.innerHTML = data.map((v, i) => `
      <div style="display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid #f3f4f6">
        <div style="
          width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;
          font-size:12px;font-weight:800;flex-shrink:0;
          background:${i === 0 ? "#fef3c7" : i === 1 ? "#f1f5f9" : "#f9fafb"};
          color:${i === 0 ? "#92400e" : "#6b7280"};
        ">${i + 1}</div>
        <div style="flex:1;min-width:0">
          <div style="font-weight:700;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
            ${escHtml(v.full_name)}
          </div>
          <div style="font-size:12px;color:#9ca3af">${escHtml(v.class_name)} · ${escHtml(v.student_code)}</div>
        </div>
        <div style="
          background:#fef2f2;color:#dc2626;
          padding:4px 10px;border-radius:20px;
          font-size:13px;font-weight:700;flex-shrink:0
        ">${v.count} lần</div>
      </div>
    `).join("");
  } catch(e) {
    el.innerHTML = "<p style='color:#9ca3af'>Lỗi kết nối</p>";
  }
}

// ── Load violation types ──────────────────────────────────────
const TYPE_COLOR = {
  "Không đồng phục": "#f59e0b",
  "Đi trễ":          "#ef4444",
  "Dùng điện thoại": "#ef4444",
  "Không đeo thẻ":   "#f59e0b",
  "Không đội mũ bảo hiểm": "#ef4444",
  "Gây mất trật tự": "#ef4444",
  "Khác":            "#6b7280",
};

async function loadViolationTypes() {
  const el = document.getElementById("violationTypes");
  try {
    const res  = await apiFetch("/stats/by-type");
    if (!res.ok) { el.innerHTML = "<p style='color:#9ca3af'>Không tải được</p>"; return; }
    const data = await res.json();
    if (!data.length) { el.innerHTML = "<p style='color:#9ca3af;text-align:center;padding:16px'>Chưa có dữ liệu</p>"; return; }

    const total = data.reduce((s, d) => s + d.count, 0);
    el.innerHTML = data.sort((a,b) => b.count - a.count).map(d => {
      const pct   = total > 0 ? Math.round(d.count / total * 100) : 0;
      const color = TYPE_COLOR[d.type] || "#6b7280";
      return `
        <div style="margin-bottom:12px">
          <div style="display:flex;justify-content:space-between;margin-bottom:5px;font-size:13px">
            <span style="font-weight:600">${escHtml(d.type)}</span>
            <span style="color:#6b7280">${d.count} lần (${pct}%)</span>
          </div>
          <div style="background:#f3f4f6;border-radius:6px;height:8px;overflow:hidden">
            <div style="height:100%;width:${pct}%;background:${color};border-radius:6px;transition:width 0.6s ease"></div>
          </div>
        </div>
      `;
    }).join("");
  } catch(e) {
    el.innerHTML = "<p style='color:#9ca3af'>Lỗi kết nối</p>";
  }
}

// ── Load recent violations ────────────────────────────────────
const BADGE_COLOR = {
  "Không đồng phục": "badge-amber",
  "Đi trễ":          "badge-red",
  "Dùng điện thoại": "badge-red",
  "Không đeo thẻ":   "badge-amber",
  "Không đội mũ bảo hiểm": "badge-red",
  "Gây mất trật tự": "badge-red",
  "Khác":            "badge-blue",
};

async function loadRecentViolations() {
  const tbody = document.getElementById("recentViolations");
  try {
    const res  = await apiFetch("/violations?limit=10");
    if (!res.ok) { tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:24px;color:#9ca3af">Không tải được</td></tr>`; return; }
    const data = await res.json();
    if (!data.length) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:24px;color:#9ca3af">Chưa có vi phạm nào</td></tr>`;
      return;
    }
    tbody.innerHTML = data.map(v => `
      <tr>
        <td>
          <strong>${escHtml(v.student_name)}</strong>
          <br><small style="color:#9ca3af">${escHtml(v.student_code)}</small>
        </td>
        <td>${escHtml(v.class_name)}</td>
        <td><span class="badge ${BADGE_COLOR[v.violation_type] || "badge-blue"}">${escHtml(v.violation_type)}</span></td>
        <td style="font-size:13px;color:#6b7280">${escHtml(v.note) || "—"}</td>
        <td style="font-size:13px;color:#9ca3af;white-space:nowrap">${formatDate(v.created_at)}</td>
      </tr>
    `).join("");
  } catch(e) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:24px;color:#9ca3af">Lỗi kết nối</td></tr>`;
  }
}

// ── Init ─────────────────────────────────────────────────────
loadSummary();
loadTopViolators();
loadViolationTypes();
loadRecentViolations();
