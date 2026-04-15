const STORAGE_KEY = "hematology_chat_history_v3";
const SESSION_KEY = "hematology_chat_session_id_v1";
const DEFAULT_BOT_MESSAGE =
  "I can help with CBC basics, coagulation tests, blood smear workflow, platelet and white-cell terms, quality control, and critical-value reporting. Ask in English.";

const CARD_MAP = {
  cbc_info: {
    kicker: "Structured Answer Card",
    title: "CBC / Core Hematology",
    points: [
      "Use for CBC overview, indices, and high-level term explanation.",
      "Best for non-patient-specific hematology concepts.",
      "Reference ranges and interpretation should follow your local SOP.",
    ],
  },
  coag_test: {
    kicker: "Structured Answer Card",
    title: "Coagulation Workflow",
    points: [
      "Use for PT, aPTT, INR, citrate tube handling, and coag specimen rules.",
      "Collection quality strongly affects coagulation validity.",
      "Do not use this assistant for treatment or anticoagulation prescribing decisions.",
    ],
  },
  blood_smear: {
    kicker: "Structured Answer Card",
    title: "Blood Smear Review",
    points: [
      "Use for smear purpose, preparation, staining, and morphology workflow.",
      "Smear review supports analyzer verification and morphology assessment.",
      "Microscopic findings should be reported under laboratory SOP.",
    ],
  },
  quality_control: {
    kicker: "Structured Answer Card",
    title: "Quality Control",
    points: [
      "Use for analyzer QC, Westgard rules, Levy-Jennings charts, and troubleshooting.",
      "QC must be acceptable before patient results are released.",
      "Document corrective actions and rerun QC per SOP.",
    ],
  },
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
const sessionEl = document.getElementById("session-status");
const counterEl = document.getElementById("input-counter");
const sendButtonEl = document.getElementById("send-button");
const templateEl = document.getElementById("message-template");

function intentCategory(intent) {
  if (["unsafe_medical_request", "out_of_scope", "incomplete_query", "language_not_supported"].includes(intent)) {
    return "guardrail";
  }
  if (["greeting", "thanks", "goodbye", "capability_query", "clarification"].includes(intent)) {
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

function getCardConfig(intent) {
  return CARD_MAP[intent] || null;
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

function populateCard(node, intent) {
  const cardConfig = getCardConfig(intent);
  const cardEl = node.querySelector(".answer-card");
  const pointsEl = cardEl.querySelector(".card-points");
  pointsEl.innerHTML = "";

  if (!cardConfig) {
    cardEl.hidden = true;
    return;
  }

  cardEl.querySelector(".card-kicker").textContent = cardConfig.kicker;
  cardEl.querySelector(".card-title").textContent = cardConfig.title;
  cardConfig.points.forEach((point) => {
    const li = document.createElement("li");
    li.textContent = point;
    pointsEl.appendChild(li);
  });
  cardEl.hidden = false;
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
    populateCard(node, intent);
    populateSuggestions(node, intent);
  } else {
    node.querySelector(".answer-card").hidden = true;
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
  return `intent: ${payload.intent} | confidence: ${confidence.toFixed(3)} | lang: ${payload.lang}`;
}

async function sendMessage(text) {
  appendMessage("user", text, { category: "user" });
  const pendingNode = appendMessage("bot", "Thinking...", { category: "pending" });

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, session_id: getSessionId() }),
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
      pendingNode.querySelector(".answer-card").hidden = true;
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
    populateCard(pendingNode, payload.intent);
    populateSuggestions(pendingNode, payload.intent);

    const metaEl = pendingNode.querySelector(".meta");
    metaEl.hidden = false;
    metaEl.textContent = buildMeta(payload);
    saveConversation();
  } catch (error) {
    pendingNode.querySelector(".bubble").textContent = "The assistant is unavailable right now.";
    pendingNode.dataset.intent = "network_error";
    pendingNode.dataset.category = "system";
    pendingNode.querySelector(".intent-tag").textContent = "network_error | system";
    pendingNode.querySelector(".intent-tag").hidden = false;
    pendingNode.querySelector(".answer-card").hidden = true;
    pendingNode.querySelector(".followup-block").hidden = true;
    const metaEl = pendingNode.querySelector(".meta");
    metaEl.hidden = false;
    metaEl.textContent = "Network or server error";
    saveConversation();
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
