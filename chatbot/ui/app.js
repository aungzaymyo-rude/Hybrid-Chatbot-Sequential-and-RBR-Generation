const messagesEl = document.getElementById("messages");
const formEl = document.getElementById("chat-form");
const inputEl = document.getElementById("message-input");
const clearEl = document.getElementById("clear-chat");
const statusEl = document.getElementById("api-status");
const templateEl = document.getElementById("message-template");

function appendMessage(role, text, meta = "") {
  const node = templateEl.content.firstElementChild.cloneNode(true);
  node.classList.add(role);
  node.querySelector(".bubble").textContent = text;
  const metaEl = node.querySelector(".meta");
  metaEl.textContent = meta;
  if (!meta) {
    metaEl.hidden = true;
  } else {
    metaEl.hidden = false;
  }
  messagesEl.appendChild(node);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function checkHealth() {
  try {
    const response = await fetch("/health");
    statusEl.textContent = response.ok ? "Online" : "Unavailable";
  } catch (error) {
    statusEl.textContent = "Offline";
  }
}

async function sendMessage(text) {
  appendMessage("user", text);
  appendMessage("bot", "Thinking...");

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });

    const pendingNode = messagesEl.lastElementChild;
    const metaEl = pendingNode.querySelector(".meta");
    if (!response.ok) {
      pendingNode.querySelector(".bubble").textContent = "The request failed. Check the API configuration and model files.";
      metaEl.hidden = false;
      metaEl.textContent = `HTTP ${response.status}`;
      return;
    }

    const payload = await response.json();
    const confidence = Number(payload.confidence);
    pendingNode.querySelector(".bubble").textContent = payload.response;
    metaEl.hidden = false;
    metaEl.textContent = `intent: ${payload.intent} | confidence: ${confidence.toFixed(3)} | lang: ${payload.lang}`;
  } catch (error) {
    const pendingNode = messagesEl.lastElementChild;
    const metaEl = pendingNode.querySelector(".meta");
    pendingNode.querySelector(".bubble").textContent = "The assistant is unavailable right now.";
    metaEl.hidden = false;
    metaEl.textContent = "Network or server error";
  }
}

formEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = inputEl.value.trim();
  if (!text) {
    return;
  }
  inputEl.value = "";
  await sendMessage(text);
});

clearEl.addEventListener("click", () => {
  messagesEl.innerHTML = "";
  appendMessage("bot", "I can help with CBC basics and sample collection questions. Ask in English.");
});

document.querySelectorAll(".prompt-chip").forEach((button) => {
  button.addEventListener("click", async () => {
    const prompt = button.dataset.prompt;
    await sendMessage(prompt);
  });
});

checkHealth();
