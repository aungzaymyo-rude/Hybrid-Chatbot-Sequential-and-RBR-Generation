const STORAGE_KEY = "hematology_chat_history_v3";
const SESSION_KEY = "hematology_chat_session_id_v1";
const MODEL_PREF_KEY = "hematology_chat_model_pref_v1";
const DEFAULT_BOT_MESSAGE =
  "I can help with CBC basics, coagulation tests, blood smear workflow, platelet and white-cell terms, quality control, and critical-value reporting. Ask in English.";
const MODEL_LABELS = {
  general: "General Hematology",
  report: "Report Assistant",
};
const MODEL_HINTS = {
  general: "Best for workflow, sample handling, coagulation, smear, QC, and general hematology questions.",
  report: "Best for CBC report sections, parameter meanings, abnormal flags, and report-reading questions.",
};

const SUGGESTED_QUESTIONS = {
  cbc_info: [
    "What does MCV mean?",
    "What is platelet count?",
    "Which tube is used for CBC?",
  ],
  sample_collection: [
    "How many inversions are needed for an EDTA tube?",
    "How should I label a CBC specimen?",
    "What are the rejection criteria for a CBC sample?",
  ],
  coag_test: [
    "Which tube is used for coagulation tests?",
    "What happens if citrate tube is underfilled?",
    "What does INR mean?",
  ],
  blood_smear: [
    "How do you prepare a blood film?",
    "What stains are used for blood smear?",
    "Why is blood smear examination done?",
  ],
  quality_control: [
    "What should be done if QC fails?",
    "What is Westgard rule in simple terms?",
    "What is Levy Jennings chart in lab QC?",
  ],
  capability_query: [
    "What is a CBC?",
    "What is aPTT?",
    "What is hematology analyzer quality control?",
  ],
  small_talk: [
    "What can you do?",
    "What is a CBC?",
    "Which tube is used for CBC?",
  ],
  clarification: [
    "Can you explain that more simply?",
    "What does MCV mean?",
    "What is leukocytosis?",
  ],
  fallback: [
    "What is a CBC?",
    "Which tube is used for CBC?",
    "What kinds of hematology questions can you answer?",
  ],
  incomplete_query: [
    "What is platelet count?",
    "Which tube is used for coagulation tests?",
    "What is hematology analyzer quality control?",
  ],
  unsafe_medical_request: [
    "What is thrombocytopenia?",
    "What is a critical value in hematology?",
    "What kinds of hematology questions can you answer?",
  ],
};

const messagesEl = document.getElementById("messages");
const formEl = document.getElementById("chat-form");
const inputEl = document.getElementById("message-input");
const clearEl = document.getElementById("clear-chat");
const exportEl = document.getElementById("export-chat");
const statusEl = document.getElementById("api-status");
const modelStatusEl = document.getElementById("model-status");
const sessionEl = document.getElementById("session-status");
const counterEl = document.getElementById("input-counter");
const sendButtonEl = document.getElementById("send-button");
const templateEl = document.getElementById("message-template");
const modelSelectEl = document.getElementById("model-select");
const modelHintEl = document.getElementById("model-hint");

function intentCategory(intent) {
  if (["unsafe_medical_request", "out_of_scope", "incomplete_query", "language_not_supported"].includes(intent)) {
    return "guardrail";
  }
  if (["greeting", "small_talk", "thanks", "goodbye", "capability_query", "clarification"].includes(intent)) {
    return "conversation";
  }
  if (intent === "fallback") {
    return "fallback";
  }
  return "medical";
}

function messageRoleLabel(role) {
  return role === "user" ? "User" : "Assistant";
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function getSessionId() {
  const existing = window.localStorage.getItem(SESSION_KEY);
  if (existing) {
    return existing;
  }

  const generated = window.crypto?.randomUUID?.() || `session-${Date.now()}`;
  window.localStorage.setItem(SESSION_KEY, generated);
  return generated;
}

function friendlyModelLabel(modelKey) {
  return MODEL_LABELS[modelKey] || modelKey || "Unknown";
}

function updateModelUI(modelKey) {
  if (!modelKey) {
    modelStatusEl.textContent = "Unavailable";
    modelHintEl.textContent = "Model options are unavailable.";
    return;
  }
  modelStatusEl.textContent = friendlyModelLabel(modelKey);
  modelHintEl.textContent = MODEL_HINTS[modelKey] || `Using model: ${friendlyModelLabel(modelKey)}`;
}

function getSelectedModelKey() {
  return modelSelectEl.value || window.localStorage.getItem(MODEL_PREF_KEY) || "general";
}

function setSelectedModelKey(modelKey) {
  if (!modelKey) {
    return;
  }
  modelSelectEl.value = modelKey;
  window.localStorage.setItem(MODEL_PREF_KEY, modelKey);
  updateModelUI(modelKey);
}

function getSuggestedQuestions(intent) {
  return SUGGESTED_QUESTIONS[intent] || SUGGESTED_QUESTIONS.fallback;
}

function saveConversation() {
  const payload = Array.from(messagesEl.querySelectorAll(".message")).map((node) => ({
    role: node.dataset.role,
    text: node.querySelector(".bubble").textContent,
    meta: node.querySelector(".meta").hidden ? "" : node.querySelector(".meta").textContent,
    intent: node.dataset.intent || "",
    category: node.dataset.category || "",
  }));
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
}

function populateSuggestions(node, intent) {
  const followupEl = node.querySelector(".followup-block");
  const actionsEl = node.querySelector(".followup-actions");
  actionsEl.innerHTML = "";

  if (!intent || intent === "thanks" || intent === "goodbye") {
    followupEl.hidden = true;
    return;
  }

  getSuggestedQuestions(intent).forEach((prompt) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "prompt-chip followup-chip";
    button.textContent = prompt;
    button.addEventListener("click", async () => {
      setPendingState(true);
      await sendMessage(prompt);
      setPendingState(false);
    });
    actionsEl.appendChild(button);
  });
  followupEl.hidden = actionsEl.childElementCount === 0;
}

function createMessageNode(role, text, options = {}) {
  const { meta = "", intent = "", category = "" } = options;
  const node = templateEl.content.firstElementChild.cloneNode(true);
  node.classList.add(role);
  node.dataset.role = role;
  node.dataset.intent = intent;
  node.dataset.category = category;

  node.querySelector(".bubble").textContent = text;
  node.querySelector(".role-tag").textContent = messageRoleLabel(role);

  const intentTag = node.querySelector(".intent-tag");
  if (intent) {
    intentTag.textContent = category ? `${intent} | ${category}` : intent;
    intentTag.hidden = false;
  } else {
    intentTag.hidden = true;
  }

  const metaEl = node.querySelector(".meta");
  if (meta) {
    metaEl.textContent = meta;
    metaEl.hidden = false;
  } else {
    metaEl.hidden = true;
  }

  if (role === "bot") {
    populateSuggestions(node, intent);
  } else {
    node.querySelector(".followup-block").hidden = true;
  }

  return node;
}

function appendMessage(role, text, options = {}) {
  const node = createMessageNode(role, text, options);
  messagesEl.appendChild(node);
  scrollToBottom();
  saveConversation();
  return node;
}

function restoreConversation() {
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    appendMessage("bot", DEFAULT_BOT_MESSAGE, { intent: "capability_query", category: "conversation" });
    return;
  }

  try {
    const history = JSON.parse(raw);
    if (!Array.isArray(history) || history.length === 0) {
      appendMessage("bot", DEFAULT_BOT_MESSAGE, { intent: "capability_query", category: "conversation" });
      return;
    }

    history.forEach((item) => {
      const node = createMessageNode(item.role || "bot", item.text || "", {
        meta: item.meta || "",
        intent: item.intent || "",
        category: item.category || "",
      });
      messagesEl.appendChild(node);
    });
    scrollToBottom();
  } catch (error) {
    window.localStorage.removeItem(STORAGE_KEY);
    appendMessage("bot", DEFAULT_BOT_MESSAGE, { intent: "capability_query", category: "conversation" });
  }
}

function updateCounter() {
  counterEl.textContent = `${inputEl.value.length} / 400`;
}

function setPendingState(isPending) {
  sendButtonEl.disabled = isPending;
  sendButtonEl.textContent = isPending ? "Sending..." : "Send";
}

async function checkHealth() {
  try {
    const response = await fetch("/health");
    statusEl.textContent = response.ok ? "Online" : "Unavailable";
  } catch (error) {
    statusEl.textContent = "Offline";
  }
}

function buildMeta(payload) {
  const confidence = Number(payload.confidence || 0);
  const modelKey = payload.model_key ? ` | model: ${payload.model_key}` : "";
  const switched = payload.auto_switched && payload.requested_model_key && payload.model_key
    ? ` | auto-switched: ${payload.requested_model_key} -> ${payload.model_key}`
    : "";
  return `intent: ${payload.intent} | confidence: ${confidence.toFixed(3)} | lang: ${payload.lang}${modelKey}${switched}`;
}

async function sendMessage(text) {
  appendMessage("user", text, { category: "user" });
  const pendingNode = appendMessage("bot", "Thinking...", { category: "pending" });
  const modelKey = getSelectedModelKey();

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, session_id: getSessionId(), model_key: modelKey }),
    });

    if (!response.ok) {
      pendingNode.querySelector(".bubble").textContent =
        "The request failed. Check the API configuration and model files.";
      const metaEl = pendingNode.querySelector(".meta");
      metaEl.hidden = false;
      metaEl.textContent = `HTTP ${response.status}`;
      pendingNode.dataset.intent = "error";
      pendingNode.dataset.category = "system";
      pendingNode.querySelector(".intent-tag").textContent = "error | system";
      pendingNode.querySelector(".intent-tag").hidden = false;
      pendingNode.querySelector(".followup-block").hidden = true;
      saveConversation();
      return;
    }

    const payload = await response.json();
    const category = intentCategory(payload.intent);
    pendingNode.querySelector(".bubble").textContent = payload.response;
    pendingNode.dataset.intent = payload.intent;
    pendingNode.dataset.category = category;
    pendingNode.querySelector(".intent-tag").textContent = `${payload.intent} | ${category}`;
    pendingNode.querySelector(".intent-tag").hidden = false;
    populateSuggestions(pendingNode, payload.intent);

    const metaEl = pendingNode.querySelector(".meta");
    metaEl.hidden = false;
    metaEl.textContent = buildMeta(payload);
    if (payload.model_key && payload.model_key !== modelKey) {
      setSelectedModelKey(payload.model_key);
    }
    saveConversation();
  } catch (error) {
    pendingNode.querySelector(".bubble").textContent = "The assistant is unavailable right now.";
    pendingNode.dataset.intent = "network_error";
    pendingNode.dataset.category = "system";
    pendingNode.querySelector(".intent-tag").textContent = "network_error | system";
    pendingNode.querySelector(".intent-tag").hidden = false;
    pendingNode.querySelector(".followup-block").hidden = true;
    const metaEl = pendingNode.querySelector(".meta");
    metaEl.hidden = false;
    metaEl.textContent = "Network or server error";
    saveConversation();
  }
}

async function loadModels() {
  try {
    const response = await fetch("/models");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    const models = payload.models || {};
    modelSelectEl.innerHTML = "";
    Object.entries(models).forEach(([key, entry]) => {
      const option = document.createElement("option");
      const version = entry.version ? ` (${entry.version})` : "";
      option.value = key;
      option.textContent = `${friendlyModelLabel(key)}${version}`;
      modelSelectEl.appendChild(option);
    });

    const stored = window.localStorage.getItem(MODEL_PREF_KEY);
    const defaultKey = stored && models[stored] ? stored : (payload.default || Object.keys(models)[0] || "general");
    setSelectedModelKey(defaultKey);
  } catch (error) {
    modelSelectEl.innerHTML = '<option value="general">General Hematology</option><option value="report">Report Assistant</option>';
    setSelectedModelKey(window.localStorage.getItem(MODEL_PREF_KEY) || "general");
  }
}

function clearConversation() {
  messagesEl.innerHTML = "";
  window.localStorage.removeItem(STORAGE_KEY);
  appendMessage("bot", DEFAULT_BOT_MESSAGE, { intent: "capability_query", category: "conversation" });
}

function exportConversation() {
  const payload = Array.from(messagesEl.querySelectorAll(".message")).map((node) => ({
    role: node.dataset.role,
    intent: node.dataset.intent || "",
    category: node.dataset.category || "",
    text: node.querySelector(".bubble").textContent,
    meta: node.querySelector(".meta").hidden ? "" : node.querySelector(".meta").textContent,
  }));

  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "hematology-chat-transcript.json";
  anchor.click();
  URL.revokeObjectURL(url);
}

formEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = inputEl.value.trim();
  if (!text) {
    return;
  }

  inputEl.value = "";
  updateCounter();
  setPendingState(true);
  await sendMessage(text);
  setPendingState(false);
});

inputEl.addEventListener("input", updateCounter);

clearEl.addEventListener("click", clearConversation);
exportEl.addEventListener("click", exportConversation);
modelSelectEl.addEventListener("change", () => {
  setSelectedModelKey(modelSelectEl.value);
});

document.querySelectorAll(".prompt-chip").forEach((button) => {
  button.addEventListener("click", async () => {
    setPendingState(true);
    await sendMessage(button.dataset.prompt);
    setPendingState(false);
  });
});

sessionEl.textContent = "Local transcript enabled";
restoreConversation();
updateCounter();
checkHealth();
loadModels();
