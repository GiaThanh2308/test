requireAuth();

const chatHistory = []; // lưu lịch sử hội thoại để gửi lên backend

async function sendMessage() {
  const input   = document.getElementById("chatInput");
  const sendBtn = document.getElementById("sendBtn");
  const text    = input.value.trim();
  if (!text) return;

  // Hiện tin nhắn user
  appendMsg(text, "user");
  chatHistory.push({ role: "user", content: text });
  input.value = "";
  sendBtn.disabled = true;

  // Hiện typing indicator
  const typingEl = appendMsg("Đang suy nghĩ...", "bot typing", "typing-indicator");

  try {
    const res = await apiFetch("/chatbot", {
      method: "POST",
      body: JSON.stringify({ messages: chatHistory }),
    });

    typingEl.remove();

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      appendMsg("❌ Lỗi: " + (err.detail || "Server lỗi"), "bot");
      return;
    }

    const data = await res.json();
    const reply = data.reply || "(không có phản hồi)";
    appendMsg(reply, "bot");
    chatHistory.push({ role: "assistant", content: reply });

  } catch (e) {
    typingEl.remove();
    appendMsg("❌ Không kết nối được server", "bot");
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}

function appendMsg(text, cls, id = "") {
  const box = document.getElementById("chatMessages");
  const el  = document.createElement("div");
  el.className = "msg " + cls;
  el.textContent = text;
  if (id) el.id = id;
  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
  return el;
}


