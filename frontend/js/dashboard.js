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
  // Đảm bảo parse đúng UTC → chuyển sang giờ địa phương
  const str = iso && !iso.endsWith("Z") && !iso.includes("+") ? iso + "Z" : iso;
  const d = new Date(str);
  return d.toLocaleDateString("vi-VN") + " " +
    d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
}

// ── Load summary stats ────────────────────────────────────────
async function loadSummary() {
  try {
    const res  = await apiFetch("/stats/summary");
    if (!res.ok) return;
    const data = await res.json();
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

// ── Load điểm trừ theo lớp trong tuần (mỗi vi phạm = -1 điểm) ─
async function loadClassScores() {
  const el = document.getElementById("classScores");
  try {
    // Lấy tất cả vi phạm trong tuần này
    const res = await apiFetch("/violations?limit=200");
    if (!res.ok) { el.innerHTML = "<p style='color:#9ca3af'>Không tải được</p>"; return; }
    const data = await res.json();

    // Tính đầu tuần (thứ Hai)
    const now       = new Date();
    const dayOfWeek = now.getDay(); // 0=CN, 1=T2...
    const diffToMon = (dayOfWeek === 0 ? -6 : 1 - dayOfWeek);
    const weekStart = new Date(now);
    weekStart.setDate(now.getDate() + diffToMon);
    weekStart.setHours(0, 0, 0, 0);

    // Lọc vi phạm trong tuần và đếm theo lớp
    const classMap = {};
    data.forEach(v => {
      const d = new Date(v.created_at);
      if (d >= weekStart && v.class_name) {
        classMap[v.class_name] = (classMap[v.class_name] || 0) + 1;
      }
    });

    if (!Object.keys(classMap).length) {
      el.innerHTML = "<p style='color:#9ca3af;text-align:center;padding:16px'>Tuần này chưa có vi phạm</p>";
      return;
    }

    // Sắp xếp theo số vi phạm giảm dần
    const sorted = Object.entries(classMap).sort((a, b) => b[1] - a[1]);
    const maxCount = sorted[0][1];

    el.innerHTML = `
      <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <thead style="position:sticky;top:0;background:#fff;z-index:1;">
          <tr>
            <th style="text-align:left;padding:8px 10px;color:#6b7280;font-weight:600;font-size:12px;text-transform:uppercase;border-bottom:2px solid #f3f4f6;">Lớp</th>
            <th style="text-align:center;padding:8px 10px;color:#6b7280;font-weight:600;font-size:12px;text-transform:uppercase;border-bottom:2px solid #f3f4f6;">Vi phạm</th>
            <th style="text-align:right;padding:8px 10px;color:#ef4444;font-weight:700;font-size:12px;text-transform:uppercase;border-bottom:2px solid #f3f4f6;">Điểm trừ</th>
          </tr>
        </thead>
        <tbody>
          ${sorted.map(([cls, count], i) => {
            const points = -count;
            const barWidth = maxCount > 0 ? Math.round(count / maxCount * 100) : 0;
            const isWorst = i === 0;
            return `
              <tr style="border-bottom:1px solid #f9fafb;">
                <td style="padding:10px 10px;">
                  <span style="
                    font-weight:700;font-size:14px;
                    color:${isWorst ? "#dc2626" : "#1f2937"};
                  ">${escHtml(cls)}</span>
                  <div style="margin-top:4px;background:#f3f4f6;border-radius:4px;height:5px;overflow:hidden;">
                    <div style="height:100%;width:${barWidth}%;background:${isWorst ? "#ef4444" : "#f59e0b"};border-radius:4px;"></div>
                  </div>
                </td>
                <td style="text-align:center;padding:10px;">
                  <span style="
                    background:#fef2f2;color:#dc2626;
                    padding:3px 9px;border-radius:20px;
                    font-size:13px;font-weight:700;
                  ">${count} lần</span>
                </td>
                <td style="text-align:right;padding:10px;">
                  <span style="
                    background:#fef2f2;color:#b91c1c;
                    padding:4px 10px;border-radius:8px;
                    font-size:14px;font-weight:800;
                    letter-spacing:0.5px;
                  ">${points} điểm</span>
                </td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    `;
  } catch(e) {
    el.innerHTML = "<p style='color:#9ca3af'>Lỗi kết nối</p>";
  }
}

// ── Load recent violations (bỏ cột ghi chú, thêm cột điểm trừ) ─
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
        <td style="text-align:center;">
          <span style="
            background:#fef2f2;color:#b91c1c;
            padding:3px 10px;border-radius:8px;
            font-size:13px;font-weight:800;
          ">−1 điểm</span>
        </td>
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
loadClassScores();
loadRecentViolations();


