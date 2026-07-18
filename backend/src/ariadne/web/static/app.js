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

document.addEventListener("DOMContentLoaded", () => {
  checkHealth();
  loadDocuments().catch((error) => toast(error.message, "error"));
  $("refresh-docs").addEventListener("click", () => {
    loadDocuments().catch((error) => toast(error.message, "error"));
  });
});
