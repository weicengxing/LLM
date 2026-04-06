const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");
const modelStatus = document.getElementById("model-status");
const statusDetail = document.getElementById("status-detail");
const sessionList = document.getElementById("session-list");
const sessionTitle = document.getElementById("session-title");
const newSessionButton = document.getElementById("new-session-button");

let currentSessionId = null;

function appendMessage(role, content) {
  const article = document.createElement("article");
  article.className = `message ${role}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = content;

  article.appendChild(bubble);
  chatLog.appendChild(article);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function setLoadingState(loading) {
  sendButton.disabled = loading;
  sendButton.textContent = loading ? "思考中..." : "发送";
}

function clearMessages() {
  chatLog.innerHTML = "";
}

function renderMessages(messages) {
  clearMessages();
  if (messages.length === 0) {
    appendMessage("assistant", "这个会话还是空的，先发第一条消息吧。");
    return;
  }

  for (const message of messages) {
    appendMessage(message.role, message.content);
  }
}

function renderSessions(sessions) {
  sessionList.innerHTML = "";
  if (sessions.length === 0) {
    sessionList.innerHTML = "<p class=\"sessions-subtitle\">还没有会话。</p>";
    sessionTitle.textContent = "请先新建一个会话";
    currentSessionId = null;
    clearMessages();
    appendMessage("assistant", "请先在左侧新建一个会话，然后再开始聊天。");
    return;
  }

  for (const session of sessions) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "session-item";
    if (session.id === currentSessionId) {
      button.classList.add("active");
    }
    button.innerHTML = `
      <span class="session-item-row">
        <span class="session-item-title">${session.title}</span>
        <span class="session-delete" data-delete-id="${session.id}">删除</span>
      </span>
      <span class="session-item-preview">${session.last_message || "暂无消息"}</span>
      <span class="session-item-meta">${session.message_count ?? 0} 条消息</span>
    `;
    button.addEventListener("click", (event) => {
      const deleteTarget = event.target.closest("[data-delete-id]");
      if (deleteTarget) {
        event.preventDefault();
        event.stopPropagation();
        deleteSession(session.id);
        return;
      }
      openSession(session.id, session.title);
    });
    sessionList.appendChild(button);
  }
}

async function loadSessions(preferredSessionId = null) {
  const response = await fetch("/api/sessions");
  const data = await response.json();
  const sessions = data.sessions || [];

  if (preferredSessionId !== null) {
    currentSessionId = preferredSessionId;
  } else if (currentSessionId === null && sessions.length > 0) {
    currentSessionId = sessions[0].id;
  }

  renderSessions(sessions);

  if (currentSessionId !== null) {
    const active = sessions.find((session) => session.id === currentSessionId);
    if (active) {
      await openSession(active.id, active.title, false);
    }
  }
}

async function openSession(sessionId, title = "Session", rerender = true) {
  currentSessionId = sessionId;
  sessionTitle.textContent = title;

  const response = await fetch(`/api/sessions/${sessionId}/messages`);
  const data = await response.json();
  renderMessages(data.messages || []);

  if (rerender) {
    await loadSessions(sessionId);
  }
}

async function refreshStatus() {
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    modelStatus.textContent = data.ready ? "已就绪" : "未训练";
    statusDetail.textContent = data.ready
      ? `运行设备：${data.device}，模型目录：${data.checkpoint_dir}`
      : "请先运行 python train.py 生成模型权重";
    renderSessions(data.sessions || []);
  } catch (error) {
    modelStatus.textContent = "服务异常";
    statusDetail.textContent = "无法连接本地后端服务";
  }
}

async function createSession() {
  const title = window.prompt("请输入会话标题：", "新会话");
  if (title === null) {
    return;
  }
  const response = await fetch("/api/sessions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ title }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "创建会话失败");
  }

  currentSessionId = data.session.id;
  sessionTitle.textContent = data.session.title;
  await loadSessions(currentSessionId);
  renderMessages([]);
}

async function deleteSession(sessionId) {
  const confirmed = window.confirm("确定删除这个会话吗？这会同时删除该会话下的所有消息。");
  if (!confirmed) {
    return;
  }

  const response = await fetch(`/api/sessions/${sessionId}`, {
    method: "DELETE",
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "删除会话失败");
  }

  if (currentSessionId === sessionId) {
    currentSessionId = null;
  }
  await loadSessions();
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = messageInput.value.trim();
  if (!message) {
    return;
  }
  if (currentSessionId === null) {
    appendMessage("assistant", "请先创建一个会话。");
    return;
  }

  appendMessage("user", message);
  messageInput.value = "";
  setLoadingState(true);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
        session_id: currentSessionId,
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "请求失败");
    }

    appendMessage("assistant", data.assistant_message.content);
    sessionTitle.textContent = data.session.title;
    await loadSessions(currentSessionId);
  } catch (error) {
    appendMessage("assistant", `回复失败：${error.message}`);
  } finally {
    setLoadingState(false);
  }
});

messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

newSessionButton.addEventListener("click", async () => {
  try {
    await createSession();
  } catch (error) {
    appendMessage("assistant", `创建会话失败：${error.message}`);
  }
});

async function bootstrap() {
  await refreshStatus();
  await loadSessions();
}

bootstrap();
