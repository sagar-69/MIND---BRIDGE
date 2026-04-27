const $ = (id) => document.getElementById(id);
const LS_KEY = "mindbridge_session_id";
const THEME_KEY = "mindbridge_theme";

let sessionId = localStorage.getItem(LS_KEY) || null;
let sending = false;
let sidebarCollapsed = false;

const themeToggle = $("themeToggle");

function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem(THEME_KEY, theme);
  if (!themeToggle) return;
  const icon = theme === "dark" ? "sun" : "moon";
  const label = theme === "dark" ? "Toggle light mode" : "Toggle dark mode";
  themeToggle.setAttribute("aria-label", label);
  const lucideNode = themeToggle.querySelector("i");
  if (lucideNode) lucideNode.setAttribute("data-lucide", icon);
  if (window.lucide) window.lucide.createIcons();
}

function initTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const theme = saved || (prefersDark ? "dark" : "light");
  setTheme(theme);
  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      setTheme(next);
    });
  }
}

function initLandingCard() {
  const heroCard = $("heroCard");
  if (!heroCard) return;
  heroCard.addEventListener("mousemove", (event) => {
    const rect = heroCard.getBoundingClientRect();
    const mx = ((event.clientX - rect.left) / rect.width) * 100;
    const my = ((event.clientY - rect.top) / rect.height) * 100;
    heroCard.style.setProperty("--mx", `${mx}%`);
    heroCard.style.setProperty("--my", `${my}%`);
  });
}

function initChatPage() {
  const thread = $("thread");
  if (!thread) return;

  const input = $("input");
  const sendBtn = $("sendBtn");
  const typing = $("typing");
  const sessionsList = $("sessionsList");
  const mobileSessionsList = $("mobileSessionsList");
  const newSessionBtn = $("newSessionBtn");
  const mobileNewSessionBtn = $("mobileNewSessionBtn");
  const helplineBtn = $("helplineBtn");
  const mobileHelplineBtn = $("mobileHelplineBtn");
  const crisisBanner = $("crisisBanner");
  const offlineBanner = $("offlineBanner");
  const offlinePill = $("offlinePill");
  const moodToast = $("moodToast");
  const scrollFab = $("scrollToBottomBtn");
  const chatShell = $("chatShell");
  const sidebarToggle = $("sidebarToggle");
  const drawerOverlay = $("drawerOverlay");
  const mobileDrawer = $("mobileDrawer");
  const sessionTitleBtn = $("sessionTitleBtn");
  const sessionTitleInput = $("sessionTitleInput");
  const sessionShortId = $("sessionShortId");
  const sendLabel = sendBtn?.querySelector(".send-label");

  const suggestedPrompts = [
    "I've been feeling anxious.",
    "I can't sleep lately.",
    "I need to vent.",
    "Work is overwhelming me.",
  ];

  function scrollToBottom() {
    thread.scrollTo({ top: thread.scrollHeight, behavior: "smooth" });
  }

  function showScrollFab() {
    const distanceFromBottom = thread.scrollHeight - thread.scrollTop - thread.clientHeight;
    scrollFab.classList.toggle("hidden", distanceFromBottom <= 60);
  }

  function createAgentLabel(streaming) {
    const label = document.createElement("div");
    label.className = "agent-label";
    label.textContent = "MindBridge · just now";
    if (streaming) {
      const dot = document.createElement("span");
      dot.className = "stream-dot";
      label.appendChild(dot);
    }
    return label;
  }

  function makeBubble(content, who, showLabel, isStreaming) {
    const wrap = document.createElement("div");
    wrap.className = "bubble-wrap";
    const bubble = document.createElement("div");
    bubble.className = `bubble ${who === "user" ? "bubble-user" : "bubble-ai"}`;
    bubble.textContent = content;
    wrap.appendChild(bubble);

    let label = null;
    if (who !== "user" && showLabel) {
      label = createAgentLabel(isStreaming);
      wrap.appendChild(label);
    }
    return { wrap, bubble, label };
  }

  function setOffline(isOffline) {
    offlineBanner.classList.toggle("hidden", !isOffline);
    if (offlinePill) offlinePill.classList.toggle("hidden", !isOffline);
    sendBtn.disabled = isOffline || sending;
    input.disabled = isOffline || sending;
  }

  async function checkHealth() {
    try {
      const res = await fetch("/health");
      const data = await res.json();
      setOffline(data.status !== "ok");
    } catch {
      setOffline(true);
    }
  }

  async function ensureSession() {
    if (sessionId) return sessionId;
    const res = await fetch("/session/new", { method: "POST" });
    const data = await res.json();
    sessionId = data.session_id;
    localStorage.setItem(LS_KEY, sessionId);
    updateSessionHeader();
    return sessionId;
  }

  function setActiveSessionItem(id) {
    document.querySelectorAll(".session-item").forEach((el) => {
      el.classList.toggle("active", el.dataset.id === id);
    });
  }

  function sessionTitleKey(id) {
    return `mindbridge_session_title_${id}`;
  }

  function updateSessionHeader() {
    if (!sessionId) {
      sessionShortId.textContent = "-";
      sessionTitleBtn.dataset.title = "";
      return;
    }
    const defaultTitle = `Session ${sessionId.slice(0, 8)}`;
    const saved = localStorage.getItem(sessionTitleKey(sessionId)) || defaultTitle;
    sessionShortId.textContent = saved.replace(/^Session\s+/i, "");
    sessionTitleBtn.dataset.title = saved;
  }

  function renderSessionItem(s) {
    const el = document.createElement("div");
    el.className = "session-item";
    el.dataset.id = s.id;
    const title = localStorage.getItem(sessionTitleKey(s.id)) || s.id.slice(0, 8);
    el.innerHTML = `<div><strong>${title}</strong></div>
      <div class="session-meta">${new Date(s.created_at).toLocaleString()}</div>`;
    el.addEventListener("click", async () => {
      sessionId = s.id;
      localStorage.setItem(LS_KEY, sessionId);
      setActiveSessionItem(sessionId);
      updateSessionHeader();
      await loadHistory(sessionId);
      closeDrawer();
    });
    return el;
  }

  async function loadSessions() {
    const res = await fetch("/session/list?limit=25");
    const data = await res.json();
    sessionsList.innerHTML = "";
    mobileSessionsList.innerHTML = "";

    for (const s of data.sessions || []) {
      sessionsList.appendChild(renderSessionItem(s));
      mobileSessionsList.appendChild(renderSessionItem(s));
    }

    if (sessionId) setActiveSessionItem(sessionId);
  }

  function renderEmptyState() {
    const state = document.createElement("div");
    state.id = "emptyState";
    state.className = "empty-state";
    state.innerHTML = `
      <article class="empty-card">
        <div class="empty-icon" aria-hidden="true">💙</div>
        <h3 class="empty-title">Start the conversation</h3>
        <p class="empty-subtitle">No judgment here — share what's on your mind</p>
        <div class="chip-row"></div>
      </article>
    `;

    const chipRow = state.querySelector(".chip-row");
    suggestedPrompts.forEach((prompt, index) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "suggestion-chip";
      chip.style.animationDelay = `${index * 0.1}s`;
      chip.setAttribute("aria-label", `Use suggested prompt: ${prompt}`);
      chip.textContent = prompt;
      chip.addEventListener("click", () => {
        input.value = prompt;
        input.focus();
        autoResize();
      });
      chipRow.appendChild(chip);
    });
    thread.appendChild(state);
  }

  async function loadHistory(id) {
    const res = await fetch(`/session/${encodeURIComponent(id)}/history`);
    const data = await res.json();

    thread.innerHTML = "";
    crisisBanner.classList.toggle("hidden", (data.risk_level || "low") !== "high");

    for (const m of data.messages || []) {
      const who = m.role === "user" ? "user" : "ai";
      const { wrap } = makeBubble(m.content, who, who !== "user", false);
      thread.appendChild(wrap);
    }

    if (thread.children.length === 0) renderEmptyState();
    updateSessionHeader();
    scrollToBottom();
  }

  function autoResize() {
    input.style.height = "auto";
    input.style.height = `${Math.min(160, input.scrollHeight)}px`;
  }

  function setSendState(state) {
    sendBtn.classList.remove("sending", "sent");
    if (state === "sending") {
      sendBtn.classList.add("sending");
      if (sendLabel) sendLabel.textContent = "Sending";
    } else if (state === "sent") {
      sendBtn.classList.add("sent");
      if (sendLabel) sendLabel.textContent = "✓";
    } else if (sendLabel) {
      sendLabel.textContent = "Send";
    }
  }

  function startStreamingDrip(targetBubble) {
    let renderedLength = 0;
    let finalText = "";
    let timer = null;

    const tick = () => {
      if (renderedLength >= finalText.length) {
        timer = null;
        return;
      }
      renderedLength += 1;
      targetBubble.textContent = finalText.slice(0, renderedLength);
      scrollToBottom();
      timer = window.setTimeout(tick, 11);
    };

    return {
      push(nextText) {
        finalText = nextText;
        if (!timer) tick();
      },
      done() {
        if (timer) {
          clearTimeout(timer);
          timer = null;
        }
        targetBubble.textContent = finalText;
      },
    };
  }

  async function sendMessage() {
    const text = input.value.trim();
    if (!text || sending) return;

    sending = true;
    sendBtn.disabled = true;
    input.disabled = true;
    typing.classList.remove("hidden");
    setSendState("sending");

    const id = await ensureSession();

    const emptyState = $("emptyState");
    if (emptyState) emptyState.remove();

    const userBubble = makeBubble(text, "user", false, false);
    thread.appendChild(userBubble.wrap);

    const aiBubble = makeBubble("", "ai", true, true);
    aiBubble.bubble.classList.add("streaming-cursor");
    thread.appendChild(aiBubble.wrap);
    scrollToBottom();

    input.value = "";
    autoResize();

    const drip = startStreamingDrip(aiBubble.bubble);
    let full = "";
    try {
      const res = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, session_id: id }),
      });

      if (!res.ok || !res.body) throw new Error("Bad response");

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";
        for (const part of parts) {
          const lines = part.split("\n").filter((line) => line.startsWith("data:"));
          for (const line of lines) {
            const payload = line.slice(5).replace(/^ /, "");
            full += JSON.parse(payload);
          }
        }
        drip.push(full);
      }
      drip.done();
      setSendState("sent");
      setTimeout(() => setSendState("idle"), 1500);
    } catch {
      full = "Sorry — I couldn’t reach the local model. Please start Ollama and try again.";
      drip.push(full);
      drip.done();
      setSendState("idle");
    } finally {
      aiBubble.bubble.classList.remove("streaming-cursor");
      if (aiBubble.label) {
        const dot = aiBubble.label.querySelector(".stream-dot");
        if (dot) dot.remove();
      }
      typing.classList.add("hidden");
      sending = false;
      await checkHealth();
      await loadSessions();
      await loadHistory(id);
    }
  }

  function openDrawer() {
    mobileDrawer.classList.add("open");
    drawerOverlay.classList.remove("hidden");
  }

  function closeDrawer() {
    mobileDrawer.classList.remove("open");
    drawerOverlay.classList.add("hidden");
  }

  function showMoodToast() {
    moodToast.classList.remove("hidden");
    moodToast.classList.remove("show");
    void moodToast.offsetWidth;
    moodToast.classList.add("show");
    setTimeout(() => moodToast.classList.add("hidden"), 2000);
  }

  function registerMoodButtons() {
    document.querySelectorAll(".mood").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const score = Number(btn.dataset.score || "0");
        const id = await ensureSession();
        await fetch(`/session/${encodeURIComponent(id)}/mood`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ score }),
        });
        document.querySelectorAll(`.mood[data-score="${score}"]`).forEach((peer) => {
          peer.classList.add("selected", "pop");
          setTimeout(() => peer.classList.remove("pop"), 280);
        });
        showMoodToast();
      });
    });
  }

  function showHelplineAlert() {
    alert(
      "If you might hurt yourself or feel unsafe, please reach out now:\n\n" +
        "iCall (India): 9152987821\n" +
        "Vandrevala Foundation (India): 1860-2662-345\n" +
        "Global: https://findahelpline.com\n\n" +
        "If you’re in immediate danger, call your local emergency number."
    );
  }

  function startSessionTitleEdit() {
    sessionTitleInput.classList.remove("hidden");
    sessionTitleBtn.classList.add("hidden");
    sessionTitleInput.value = sessionTitleBtn.dataset.title || `Session ${sessionId?.slice(0, 8) || ""}`;
    sessionTitleInput.focus();
    sessionTitleInput.select();
  }

  function saveSessionTitle() {
    if (!sessionId) return;
    const fallback = `Session ${sessionId.slice(0, 8)}`;
    const nextTitle = sessionTitleInput.value.trim() || fallback;
    localStorage.setItem(sessionTitleKey(sessionId), nextTitle);
    sessionTitleBtn.dataset.title = nextTitle;
    sessionShortId.textContent = nextTitle.replace(/^Session\s+/i, "");
    sessionTitleInput.classList.add("hidden");
    sessionTitleBtn.classList.remove("hidden");
    loadSessions();
  }

  async function resetSession() {
    sessionId = null;
    localStorage.removeItem(LS_KEY);
    await ensureSession();
    await loadSessions();
    await loadHistory(sessionId);
  }

  newSessionBtn.addEventListener("click", resetSession);
  if (mobileNewSessionBtn) mobileNewSessionBtn.addEventListener("click", resetSession);

  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("input", autoResize);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  helplineBtn.addEventListener("click", showHelplineAlert);
  if (mobileHelplineBtn) mobileHelplineBtn.addEventListener("click", showHelplineAlert);

  thread.addEventListener("scroll", showScrollFab);
  scrollFab.addEventListener("click", scrollToBottom);
  sidebarToggle?.addEventListener("click", () => {
    if (window.innerWidth <= 860) {
      const open = mobileDrawer.classList.contains("open");
      if (open) closeDrawer();
      else openDrawer();
      return;
    }
    sidebarCollapsed = !sidebarCollapsed;
    chatShell.classList.toggle("sidebar-collapsed", sidebarCollapsed);
  });
  drawerOverlay?.addEventListener("click", closeDrawer);

  sessionTitleBtn.addEventListener("click", startSessionTitleEdit);
  sessionTitleInput.addEventListener("blur", saveSessionTitle);
  sessionTitleInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      sessionTitleInput.blur();
    }
  });

  registerMoodButtons();

  (async function init() {
    await checkHealth();
    await ensureSession();
    await loadSessions();
    await loadHistory(sessionId);
    autoResize();
    showScrollFab();
  })();
}

initTheme();
initLandingCard();
initChatPage();
if (window.lucide) window.lucide.createIcons();

