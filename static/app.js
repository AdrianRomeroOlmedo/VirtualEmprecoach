const form = document.querySelector("#chat-form");
const question = document.querySelector("#question");
const messages = document.querySelector("#messages");
const error = document.querySelector("#error");
const send = document.querySelector("#send");
const clear = document.querySelector("#clear");
let history = [];
let currentRequest = null;
let generation = 0;

function message(role, text, sources = [], notice = "") {
  const welcome = messages.querySelector(".welcome");
  if (welcome) welcome.remove();
  const wrapper = document.createElement("article");
  wrapper.className = `message ${role}`;
  const label = document.createElement("strong");
  label.textContent = role === "user" ? "Tú" : "EmpreCoach";
  const content = document.createElement("p");
  content.textContent = text;
  wrapper.append(label, content);
  if (notice) {
    const warning = document.createElement("p");
    warning.className = "source-notice";
    warning.textContent = notice;
    wrapper.append(warning);
  }
  if (sources.length) {
    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = "Consultar fuentes seleccionadas";
    details.append(summary);
    for (const source of sources) {
      const item = document.createElement("div");
      item.className = "source";
      const name = document.createElement("strong");
      name.textContent = `[${source.id}] ${source.name}${source.page ? ` · página ${source.page}` : ""}`;
      const excerpt = document.createElement("p");
      excerpt.textContent = source.excerpt;
      item.append(name, excerpt);
      details.append(item);
    }
    wrapper.append(details);
  }
  messages.append(wrapper);
  messages.scrollTop = messages.scrollHeight;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = question.value.trim();
  if (!text || currentRequest) return;
  error.hidden = true;
  const requestGeneration = generation;
  const controller = new AbortController();
  currentRequest = controller;
  send.disabled = true;
  send.textContent = "Consultando…";
  message("user", text);
  question.value = "";
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: text, history: history.slice(-6) }),
      signal: controller.signal,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "No se pudo completar la consulta.");
    if (requestGeneration !== generation) return;
    message("assistant", data.answer, data.sources, data.notice);
    history.push({ role: "user", content: text }, { role: "assistant", content: data.answer.slice(0, 3000) });
    history = history.slice(-6);
  } catch (exception) {
    if (exception.name !== "AbortError" && requestGeneration === generation) {
      error.textContent = exception.message || "No se pudo conectar con el servidor.";
      error.hidden = false;
      question.value = text;
    }
  } finally {
    if (currentRequest === controller) {
      currentRequest = null;
      send.disabled = false;
      send.textContent = "Enviar ↗";
    }
  }
});

clear.addEventListener("click", () => {
  generation += 1;
  if (currentRequest) currentRequest.abort();
  history = [];
  messages.replaceChildren();
  error.hidden = true;
  question.value = "";
  question.focus();
});
