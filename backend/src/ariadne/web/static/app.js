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

document.addEventListener("DOMContentLoaded", () => {
  checkHealth();
});
