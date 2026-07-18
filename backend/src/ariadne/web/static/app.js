"use strict";

/* ARIADNE web client
 * A dependency-free single-page app that talks to the bundled API and renders
 * the streaming RAG pipeline (retrieval progress, sources, tokens, citations).
 */

const state = {
  documents: [],
  conversations: [],
  conversationId: null,
  stream: null, // active AbortController while answering
};

const $ = (id) => document.getElementById(id);

function toast(message, kind = "info") {
  const el = $("toast");
  el.textContent = message;
  el.className = `toast show ${kind}`;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => (el.className = "toast"), 3200);
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const payload = await response.json();
      if (payload.error && payload.error.message) {
        message = payload.error.message;
      }
    } catch {
      /* non-JSON error body */
    }
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  if (response.status === 204) {
    return null;
  }
  return response.json();
}

async function checkHealth() {
  try {
    const data = await api("/health");
    $("api-status-text").textContent = data.status === "ok" ? "connected" : "degraded";
    $("api-status").classList.toggle("online", data.status === "ok");
    $("api-status").classList.toggle("offline", data.status !== "ok");
  } catch {
    $("api-status-text").textContent = "offline";
    $("api-status").classList.add("offline");
  }
}

function setSendBusy(busy) {
  const send = $("send-btn");
  const stop = $("stop-btn");
  send.disabled = busy;
  send.hidden = busy;
  stop.hidden = !busy;
  if (!busy) $("chat-input").focus();
}

/* ---------- Document library ---------- */

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value) {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

async function loadDocuments() {
  state.documents = await api("/documents");
  renderDocuments();
}

function renderDocuments() {
  const list = $("document-list");
  if (!state.documents.length) {
    list.innerHTML = `<li class="empty-hint">No documents yet — upload a file to begin indexing.</li>`;
    return;
  }
  list.innerHTML = "";
  for (const doc of state.documents) {
    const item = document.createElement("li");
    item.className = "document-item";
    item.dataset.id = doc.id;

    const main = document.createElement("div");
    main.className = "doc-main";
    main.innerHTML = `
      <span class="doc-name" title="${escapeHtml(doc.filename)}">${escapeHtml(doc.filename)}</span>
      <span class="badge ${escapeHtml(doc.status)}">${escapeHtml(doc.status)}</span>
    `;

    const meta = document.createElement("div");
    meta.className = "doc-meta";
    const info = document.createElement("span");
    info.textContent = `${formatBytes(doc.size_bytes)} · ${formatDate(doc.created_at)}`;
    const actions = document.createElement("span");
    actions.className = "doc-actions";
    actions.appendChild(makeIngestButton(doc));
    actions.appendChild(makeDeleteButton(doc.id));
    meta.append(info, actions);

    item.append(main, meta);
    list.appendChild(item);
  }
}

function makeIngestButton(doc) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "btn-link";
  button.textContent = doc.status === "ready" ? "reindex" : "index";
  button.title = "Run the ingestion pipeline";
  button.disabled = doc.status === "ingesting";
  button.addEventListener("click", () => ingestDocument(doc.id));
  return button;
}

function makeDeleteButton(id) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "btn-link danger";
  button.textContent = "delete";
  button.addEventListener("click", () => deleteDocument(id));
  return button;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

/* ---------- Document upload & lifecycle ---------- */

async function uploadDocuments(files) {
  if (!files.length) return;
  const form = new FormData();
  for (const file of files) {
    form.append("file", file);
  }
  const button = $("upload-btn");
  button.disabled = true;
  try {
    const result = await api("/documents", { method: "POST", body: form });
    toast(`Uploaded ${result.document.filename}`, "success");
    await loadDocuments();
  } finally {
    button.disabled = false;
  }
}

async function ingestDocument(id) {
  try {
    const result = await api(`/documents/${encodeURIComponent(id)}/ingest`, { method: "POST" });
    toast(`${result.chunks} chunks indexed`, "success");
    await loadDocuments();
  } catch (error) {
    toast(error.message, "error");
    await loadDocuments();
  }
}

async function deleteDocument(id) {
  const item = document.querySelector(`.document-item[data-id="${id}"]`);
  const name = item ? item.querySelector(".doc-name").textContent : "document";
  if (!window.confirm(`Delete "${name}"? This removes its index and graph data.`)) return;
  try {
    await api(`/documents/${encodeURIComponent(id)}`, { method: "DELETE" });
    toast("Document deleted", "success");
    await loadDocuments();
  } catch (error) {
    toast(error.message, "error");
  }
}

/* ---------- Streaming chat ---------- */

function scrollToBottom() {
  const list = $("message-list");
  list.scrollTop = list.scrollHeight;
}

function appendMessage(role, content) {
  const list = $("message-list");
  const el = document.createElement("div");
  el.className = `message ${role}`;
  const text = document.createElement("div");
  text.className = "msg-text";
  text.textContent = content;
  if (role === "assistant") {
    const label = document.createElement("span");
    label.className = "msg-role";
    label.textContent = "ARIADNE";
    el.append(label, text);
  } else {
    el.appendChild(text);
  }
  list.appendChild(el);
  scrollToBottom();
  return el;
}

function setAssistantText(el, text) {
  const textEl = el.querySelector(".msg-text");
  if (textEl) textEl.textContent = text;
}

function showProgress(el, text) {
  clearProgress(el);
  const progress = document.createElement("div");
  progress.className = "msg-progress";
  const spinner = document.createElement("span");
  spinner.className = "spinner";
  const caption = document.createElement("span");
  caption.textContent = text;
  progress.append(spinner, caption);
  el.appendChild(progress);
  scrollToBottom();
}

function clearProgress(el) {
  const progress = el.querySelector(".msg-progress");
  if (progress) progress.remove();
}

function parseSseEvent(raw, onEvent) {
  let event = "message";
  const dataLines = [];
  for (const line of raw.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).replace(/^ /, ""));
    }
  }
  if (!dataLines.length) return;
  let data = {};
  try {
    data = JSON.parse(dataLines.join("\n"));
  } catch {
    /* ignore malformed payloads */
  }
  onEvent(event, data);
}

async function runStream(question, assistantEl) {
  const controller = new AbortController();
  state.stream = controller;
  let answer = "";
  try {
    const response = await fetch("/query/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({ question, conversation_id: state.conversationId }),
      signal: controller.signal,
    });
    if (!response.ok || !response.body) {
      throw new Error(`Stream request failed (${response.status})`);
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    const handleEvent = (event, data) => {
      switch (event) {
        case "retrieval_started":
          showProgress(assistantEl, "Retrieving sources…");
          break;
        case "retrieval_completed":
          showProgress(assistantEl, `Found ${data.retrieved} candidate passages`);
          break;
        case "sources_found":
          showProgress(assistantEl, `${data.sources.length} sources identified`);
          break;
        case "generation_started":
          clearProgress(assistantEl);
          assistantEl.classList.add("answering");
          break;
        case "token":
          answer += data.token || "";
          setAssistantText(assistantEl, answer);
          scrollToBottom();
          break;
        case "generation_completed":
          if (data.conversation_id) state.conversationId = data.conversation_id;
          answer = data.answer || answer;
          setAssistantText(assistantEl, answer);
          break;
        case "done":
          assistantEl.classList.remove("streaming", "answering");
          break;
        case "error":
          throw new Error(data.message || "Query failed");
      }
    };

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let boundary;
      while ((boundary = buffer.indexOf("\n\n")) !== -1) {
        const raw = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        parseSseEvent(raw, handleEvent);
      }
    }
  } catch (error) {
    assistantEl.classList.add("error");
    if (error.name === "AbortError") {
      setAssistantText(assistantEl, answer || "Response interrupted.");
      toast("Streaming stopped", "info");
    } else {
      setAssistantText(assistantEl, `Error: ${error.message}`);
      toast(error.message, "error");
    }
  } finally {
    assistantEl.classList.remove("streaming", "answering");
    clearProgress(assistantEl);
    state.stream = null;
  }
}

async function sendQuestion() {
  const input = $("chat-input");
  const question = input.value.trim();
  if (!question || state.stream) return;
  input.value = "";
  autosize();
  appendMessage("user", question);
  const assistantEl = appendMessage("assistant", "");
  assistantEl.classList.add("streaming");
  setSendBusy(true);
  await runStream(question, assistantEl);
  setSendBusy(false);
}

function autosize() {
  const input = $("chat-input");
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 160)}px`;
}

document.addEventListener("DOMContentLoaded", () => {
  checkHealth();
  loadDocuments().catch((error) => toast(error.message, "error"));
  $("refresh-docs").addEventListener("click", () => {
    loadDocuments().catch((error) => toast(error.message, "error"));
  });

  const fileInput = $("file-input");
  const fileLabel = $("file-label");
  fileInput.addEventListener("change", () => {
    const names = Array.from(fileInput.files).map((file) => file.name);
    fileLabel.textContent = names.length
      ? names.length === 1
        ? names[0]
        : `${names.length} files selected`
      : "Choose files…";
    $("upload-btn").disabled = names.length === 0;
  });
  $("upload-form").addEventListener("submit", (event) => {
    event.preventDefault();
    uploadDocuments(Array.from(fileInput.files)).catch((error) => toast(error.message, "error"));
    fileInput.value = "";
    fileLabel.textContent = "Choose files…";
    $("upload-btn").disabled = true;
  });

  const chatInput = $("chat-input");
  chatInput.addEventListener("input", autosize);
  chatInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      $("chat-form").requestSubmit();
    }
  });
  $("chat-form").addEventListener("submit", (event) => {
    event.preventDefault();
    sendQuestion().catch((error) => toast(error.message, "error"));
  });
});
