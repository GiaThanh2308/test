// chatbot.js — giao diện chatbot AI (escapeHtml, apiFetch… lấy từ api.js)

requireAuth();
requireTeacher();
renderNav("chatbot");

const chatHistory = []; // lịch sử hội thoại gửi lên backend
const GREETING_HTML = document.getElementById("chatMessages").innerHTML; // lời chào có sẵn trong HTML, dùng lại khi xoá hội thoại

async function sendMessage() {
  const input   = document.getElementById("chatInput");
  const sendBtn = document.getElementById("sendBtn");
  const text    = input.value.trim();
  if (!text) return;

  appendMsg(text, "user");
  chatHistory.push({ role: "user", content: text });
  input.value      = "";
  sendBtn.disabled = true;

  const typingEl = appendTyping();

  try {
    const res = await apiFetch("/chatbot", {
      method: "POST",
      body:   JSON.stringify({ messages: chatHistory }),
    });

    typingEl.remove();

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      appendMsg("❌ Lỗi: " + (err.detail || "Server lỗi"), "bot");
      chatHistory.pop(); // bỏ câu hỏi chưa được trả lời để lượt sau không bị 2 tin "user" liên tiếp
      return;
    }

    const data  = await res.json();
    const reply = data.reply || "(không có phản hồi)";
    appendMsg(reply, "bot");
    chatHistory.push({ role: "assistant", content: reply });

  } catch (e) {
    typingEl.remove();
    appendMsg("❌ Không kết nối được server", "bot");
    chatHistory.pop();
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}

/** Tin của bot render markdown đơn giản; tin của người dùng được escape. */
function appendMsg(text, cls) {
  const box = document.getElementById("chatMessages");
  const el  = document.createElement("div");
  el.className = "msg " + cls;

  const avatarIcon = cls === "bot"
    ? '<i class="fa-solid fa-robot"></i>'
    : '<i class="fa-solid fa-user"></i>';

  const bubbleContent = cls === "bot"
    ? markdownToHtml(text)
    : escapeHtml(text);

  el.innerHTML = `
    <div class="msg-avatar">${avatarIcon}</div>
    <div class="msg-bubble">${bubbleContent}</div>`;

  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
  return el;
}

/**
 * Chuyển markdown đơn giản sang HTML:
 * - **text** → <strong>text</strong>
 * - `code` → <code>code</code>
 * - Dòng bắt đầu bằng • hoặc - → <ul><li>...</li></ul>
 * - Dòng trắng → ngắt đoạn
 */
function markdownToHtml(text) {
  // Escape HTML trước để tránh XSS
  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  // Inline code
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

  // Xử lý bullet list: gom các dòng bắt đầu bằng - hoặc •
  const lines = html.split("\n");
  const result = [];
  let inList = false;

  for (const line of lines) {
    const bulletMatch = line.match(/^[\s]*[-•]\s+(.+)/);
    if (bulletMatch) {
      if (!inList) { result.push("<ul>"); inList = true; }
      result.push(`<li>${bulletMatch[1]}</li>`);
    } else {
      if (inList) { result.push("</ul>"); inList = false; }
      result.push(line === "" ? "<br>" : `<p>${line}</p>`);
    }
  }
  if (inList) result.push("</ul>");

  // Bỏ <p></p> rỗng
  return result.join("").replace(/<p><\/p>/g, "");
}

function appendTyping() {
  const box = document.getElementById("chatMessages");
  const el  = document.createElement("div");
  el.className = "msg bot";
  el.innerHTML = `
    <div class="msg-avatar"><i class="fa-solid fa-robot"></i></div>
    <div class="msg-bubble">
      <div class="typing">
        <span></span><span></span><span></span>
      </div>
    </div>`;
  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
  return el;
}

function clearChat() {
  chatHistory.length = 0;
  document.getElementById("chatMessages").innerHTML = GREETING_HTML;
}

function quickAsk(text) {
  document.getElementById("chatInput").value = text;
  sendMessage();
}

/** Tra cứu học sinh theo mã/tên: lấy thẳng từ DB (không qua AI) nên luôn đúng học sinh và đúng lỗi. */
async function searchStudent() {
  const input = document.getElementById("studentSearch");
  const q = input.value.trim();
  if (!q) return;

  appendMsg(`Tra cứu học sinh: ${q}`, "user");
  const typingEl = appendTyping();
  try {
    const res = await apiFetch(`/chatbot/lookup?q=${encodeURIComponent(q)}`);
    typingEl.remove();
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      appendMsg("❌ Lỗi: " + (err.detail || "Server lỗi"), "bot");
      return;
    }
    const data = await res.json();
    appendMsg(data.reply, "bot");
    // đưa kết quả vào lịch sử để hỏi tiếp ("em này vi phạm gần nhất khi nào?") AI vẫn có ngữ cảnh
    chatHistory.push({ role: "user", content: `Tra cứu học sinh: ${q}` });
    chatHistory.push({ role: "assistant", content: data.reply });
    input.value = "";
  } catch {
    typingEl.remove();
    appendMsg("❌ Không kết nối được server", "bot");
  }
}

// Load context badge
(async function loadContextBadge() {
  if (!isTeacher()) return;
  try {
    const res = await apiFetch("/stats/summary");
    if (!res.ok) return;
    const data = await res.json();
    const badge = document.getElementById("contextBadge");
    if (badge) {
      badge.textContent = `${data.total_students} học sinh · ${data.total_violations} vi phạm`;
    }
  } catch {
    /* không có số liệu thì thôi, không ảnh hưởng chat */
  }
})();
