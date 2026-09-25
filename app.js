const API = "";

const messagesEl = document.getElementById("messages");
const chatForm = document.getElementById("chatForm");
const chatText = document.getElementById("chatText");
const fileInput = document.getElementById("fileInput");
const uploadBtn = document.getElementById("uploadBtn");
const uploadStatus = document.getElementById("uploadStatus");
const textInput = document.getElementById("textInput");
const pasteBtn = document.getElementById("pasteBtn");
const actionsList = document.getElementById("actionsList");
const resetBtn = document.getElementById("resetBtn");

function addMessage(role, html) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.innerHTML = html;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = chatText.value.trim();
  if (!question) return;
  addMessage("user", `<p>${escapeHtml(question)}</p>`);
  chatText.value = "";

  const thinking = document.createElement("div");
  thinking.className = "msg agent";
  thinking.innerHTML = "<p>Thinking…</p>";
  messagesEl.appendChild(thinking);
  messagesEl.scrollTop = messagesEl.scrollHeight;

  try {
    const res = await fetch(`${API}/api/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();
    thinking.remove();

    let sourcesHtml = "";
    if (data.sources && data.sources.length) {
      sourcesHtml = `<div class="sources">${data.sources
        .map(
          (s, i) =>
            `<div class="src">[${i + 1}] <b>${escapeHtml(s.source_type)}</b> — ${escapeHtml(
              s.source_name
            )}${s.doc_date ? " · " + escapeHtml(s.doc_date) : ""}</div>`
        )
        .join("")}</div>`;
    }

    let actionHtml = "";
    if (data.action) {
      actionHtml = `<p>✅ Action taken: <b>${escapeHtml(data.action.type)}</b></p>`;
      refreshActions();
    }

    addMessage("agent", `<p>${escapeHtml(data.answer)}</p>${actionHtml}${sourcesHtml}`);
  } catch (err) {
    thinking.remove();
    addMessage("agent", `<p>Error reaching the backend: ${escapeHtml(String(err))}</p>`);
  }
});

uploadBtn.addEventListener("click", async () => {
  if (!fileInput.files.length) return;
  uploadStatus.textContent = "Uploading...";
  for (const file of fileInput.files) {
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch(`${API}/api/ingest`, { method: "POST", body: formData });
      const data = await res.json();
      uploadStatus.textContent = `Added ${data.chunks_added} chunk(s) from ${data.filename}`;
    } catch (err) {
      uploadStatus.textContent = `Failed: ${err}`;
    }
  }
  fileInput.value = "";
});

pasteBtn.addEventListener("click", async () => {
  const text = textInput.value.trim();
  if (!text) return;
  const res = await fetch(`${API}/api/ingest/text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, source_type: "note", source_name: "manual entry" }),
  });
  const data = await res.json();
  uploadStatus.textContent = `Added ${data.chunks_added} chunk(s) from note`;
  textInput.value = "";
});

resetBtn.addEventListener("click", async () => {
  if (!confirm("Clear all memory and actions?")) return;
  await fetch(`${API}/api/reset`, { method: "POST" });
  uploadStatus.textContent = "Memory cleared.";
  refreshActions();
});

async function refreshActions() {
  const res = await fetch(`${API}/api/actions`);
  const data = await res.json();
  if (!data.length) {
    actionsList.innerHTML = `<li class="empty">None yet</li>`;
    return;
  }
  actionsList.innerHTML = data
    .map((a) => `<li><b>${escapeHtml(a.action_type)}</b>: ${escapeHtml(JSON.parse(a.payload).summary || JSON.stringify(JSON.parse(a.payload)))}</li>`)
    .join("");
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

refreshActions();
