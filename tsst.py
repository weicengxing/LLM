import json
import re
from pathlib import Path
from threading import Lock
from typing import Any, Iterator

from flask import Flask, Response, jsonify, render_template_string, request, stream_with_context
from openai import OpenAI

BASE_URL = "http://8.nat0.cn:49347/v1"
HOST = "127.0.0.1"
PORT = 8000
TOKEN_FILE_CANDIDATES = ("autg.txt", "auth.txt")
TOKEN_PATTERN = re.compile(r"(sk-[A-Za-z0-9]+)")
QUOTA_HINTS = (
    "insufficient_quota",
    "quota",
    "棰濆害",
    "浣欓",
    "credit",
    "billing",
    "rate limit",
    "429",
)

INDEX_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>模型问答</title>
    <style>
      :root {
        --bg: #f4efe8;
        --panel: rgba(255, 250, 246, 0.88);
        --line: rgba(108, 89, 76, 0.14);
        --ink: #2d241f;
        --muted: #77675d;
        --accent: #c96f3b;
        --accent-strong: #a85324;
        --assistant: #f6eee7;
        --user: #d86e34;
        --user-ink: #fff7f2;
      }

      * { box-sizing: border-box; }
      body {
        margin: 0;
        min-height: 100vh;
        font-family: "Microsoft YaHei", sans-serif;
        color: var(--ink);
        background:
          radial-gradient(circle at top left, rgba(201, 111, 59, 0.12), transparent 25%),
          radial-gradient(circle at bottom right, rgba(139, 102, 77, 0.12), transparent 22%),
          linear-gradient(160deg, #fbf6f1 0%, #f0e3d7 100%);
      }
      .shell {
        max-width: 1200px;
        margin: 0 auto;
        padding: 24px;
        display: grid;
        grid-template-columns: 320px 1fr;
        gap: 20px;
        min-height: 100vh;
      }
      .panel {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 24px;
        backdrop-filter: blur(14px);
        box-shadow: 0 18px 48px rgba(75, 56, 45, 0.08);
      }
      .sidebar {
        padding: 20px;
        display: flex;
        flex-direction: column;
        gap: 16px;
      }
      .title { margin: 0; font-size: 28px; }
      .subtitle, .meta, .empty, .hint { color: var(--muted); line-height: 1.5; }
      .card {
        padding: 16px;
        border: 1px solid var(--line);
        border-radius: 18px;
        background: rgba(255, 255, 255, 0.5);
      }
      .field {
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin-top: 12px;
      }
      select, textarea, button { font: inherit; }
      select, textarea {
        width: 100%;
        border: 1px solid rgba(108, 89, 76, 0.18);
        border-radius: 16px;
        padding: 12px 14px;
        background: rgba(255, 255, 255, 0.88);
        color: var(--ink);
      }
      textarea {
        min-height: 92px;
        resize: vertical;
      }
      button {
        border: 0;
        border-radius: 999px;
        padding: 12px 18px;
        background: linear-gradient(180deg, var(--accent), var(--accent-strong));
        color: white;
        cursor: pointer;
      }
      button:disabled { opacity: 0.6; cursor: wait; }
      .session-list {
        display: flex;
        flex-direction: column;
        gap: 10px;
        max-height: 45vh;
        overflow-y: auto;
      }
      .session-item {
        text-align: left;
        padding: 12px 14px;
        border-radius: 16px;
        border: 1px solid var(--line);
        background: rgba(255, 255, 255, 0.72);
        color: var(--ink);
      }
      .session-item.active {
        border-color: rgba(201, 111, 59, 0.45);
        background: rgba(238, 201, 177, 0.45);
      }
      .session-item strong, .session-item span { display: block; }
      .session-item span {
        margin-top: 4px;
        color: var(--muted);
        font-size: 13px;
      }
      .chat {
        display: grid;
        grid-template-rows: auto 1fr auto;
        min-height: 0;
      }
      .chat-header, .composer {
        padding: 20px 22px;
        border-bottom: 1px solid var(--line);
      }
      .composer {
        border-bottom: 0;
        border-top: 1px solid var(--line);
      }
      .chat-log {
        padding: 20px 22px;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        gap: 14px;
        min-height: 420px;
      }
      .message { display: flex; }
      .message.user { justify-content: flex-end; }
      .bubble {
        max-width: 82%;
        border-radius: 18px;
        padding: 12px 16px;
        line-height: 1.5;
        white-space: pre-wrap;
        word-break: break-word;
      }
      .message.assistant .bubble { background: var(--assistant); }
      .message.user .bubble {
        background: var(--user);
        color: var(--user-ink);
      }
      .row {
        display: flex;
        gap: 10px;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
      }
      .composer-actions {
        display: flex;
        justify-content: space-between;
        gap: 12px;
        margin-top: 12px;
        align-items: center;
      }
      @media (max-width: 920px) {
        .shell { grid-template-columns: 1fr; }
        .bubble { max-width: 100%; }
      }
    </style>
  </head>
  <body>
    <div class="shell">
      <aside class="panel sidebar">
        <div>
          <h1 class="title">模型问答</h1>
          <p class="subtitle">前端可以新建对话，但每次只会把当前输入发给模型，不携带历史上下文。</p>
        </div>

        <div class="card">
          <div class="row">
            <strong>当前状态</strong>
            <span id="statusText" class="meta">初始化中</span>
          </div>
          <div class="field">
            <label for="modelSelect">模型选择</label>
            <select id="modelSelect">
              <option value="">正在加载模型...</option>
            </select>
          </div>
          <p id="tokenInfo" class="meta">正在读取 token...</p>
        </div>

        <div class="card">
          <div class="row">
            <strong>对话列表</strong>
            <button id="newChatButton" type="button">新建对话</button>
          </div>
          <p class="hint">新建对话只影响前端显示和分组，不会把历史内容发给模型。</p>
          <div id="sessionList" class="session-list"></div>
        </div>
      </aside>

      <main class="panel chat">
        <div class="chat-header">
          <div class="row">
            <div>
              <strong id="chatTitle">未选择对话</strong>
              <div id="chatMeta" class="meta">先创建一个对话，然后选择模型开始提问。</div>
            </div>
          </div>
        </div>

        <div id="chatLog" class="chat-log">
          <div class="message assistant">
            <div class="bubble">点击“新建对话”开始。每次发送都只会提交你当前输入的内容。</div>
          </div>
        </div>

        <form id="chatForm" class="composer">
          <textarea id="messageInput" placeholder="输入你的问题，Enter 发送，Shift+Enter 换行"></textarea>
          <div class="composer-actions">
            <span class="hint" id="requestHint">未发送请求</span>
            <button id="sendButton" type="submit">发送</button>
          </div>
        </form>
      </main>
    </div>

    <script>
      const modelSelect = document.getElementById("modelSelect");
      const statusText = document.getElementById("statusText");
      const tokenInfo = document.getElementById("tokenInfo");
      const sessionList = document.getElementById("sessionList");
      const newChatButton = document.getElementById("newChatButton");
      const chatTitle = document.getElementById("chatTitle");
      const chatMeta = document.getElementById("chatMeta");
      const chatLog = document.getElementById("chatLog");
      const chatForm = document.getElementById("chatForm");
      const messageInput = document.getElementById("messageInput");
      const sendButton = document.getElementById("sendButton");
      const requestHint = document.getElementById("requestHint");

      let sessions = [];
      let activeSessionId = null;

      function makeSessionTitle() {
        return `新对话 ${sessions.length + 1}`;
      }

      function createSession() {
        const id = crypto.randomUUID();
        const session = { id, title: makeSessionTitle(), messages: [] };
        sessions.unshift(session);
        activeSessionId = id;
        renderSessions();
        renderActiveSession();
      }

      function getActiveSession() {
        return sessions.find((item) => item.id === activeSessionId) || null;
      }

      function appendMessage(role, content) {
        const wrapper = document.createElement("div");
        wrapper.className = `message ${role}`;
        const bubble = document.createElement("div");
        bubble.className = "bubble";
        bubble.textContent = content;
        wrapper.appendChild(bubble);
        chatLog.appendChild(wrapper);
        chatLog.scrollTop = chatLog.scrollHeight;
      }

      function createMessageElement(role, content = "") {
        const wrapper = document.createElement("div");
        wrapper.className = `message ${role}`;
        const bubble = document.createElement("div");
        bubble.className = "bubble";
        bubble.textContent = content;
        wrapper.appendChild(bubble);
        chatLog.appendChild(wrapper);
        chatLog.scrollTop = chatLog.scrollHeight;
        return bubble;
      }

      function renderMessages(messages) {
        chatLog.innerHTML = "";
        if (!messages.length) {
          appendMessage("assistant", "这个对话还是空的，发一条消息试试。");
          return;
        }
        for (const item of messages) {
          appendMessage(item.role, item.content);
        }
      }

      function renderSessions() {
        sessionList.innerHTML = "";
        if (!sessions.length) {
          sessionList.innerHTML = '<div class="empty">还没有对话，先新建一个。</div>';
          return;
        }
        for (const session of sessions) {
          const button = document.createElement("button");
          button.type = "button";
          button.className = "session-item" + (session.id === activeSessionId ? " active" : "");
          const preview = session.messages.length
            ? session.messages[session.messages.length - 1].content.slice(0, 36)
            : "暂无消息";
          button.innerHTML = `<strong>${session.title}</strong><span>${preview}</span>`;
          button.addEventListener("click", () => {
            activeSessionId = session.id;
            renderSessions();
            renderActiveSession();
          });
          sessionList.appendChild(button);
        }
      }

      function renderActiveSession() {
        const session = getActiveSession();
        if (!session) {
          chatTitle.textContent = "未选择对话";
          chatMeta.textContent = "先创建一个对话，然后选择模型开始提问。";
          renderMessages([]);
          return;
        }
        chatTitle.textContent = session.title;
        chatMeta.textContent = `当前对话显示 ${session.messages.length} 条消息，但发给模型时只会提交本次输入。`;
        renderMessages(session.messages);
      }

      function setLoading(loading) {
        sendButton.disabled = loading;
        sendButton.textContent = loading ? "发送中..." : "发送";
      }

      async function loadModels() {
        statusText.textContent = "加载模型中...";
        const response = await fetch("/api/models");
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.error || "模型加载失败");
        }

        modelSelect.innerHTML = "";
        for (const modelId of data.models) {
          const option = document.createElement("option");
          option.value = modelId;
          option.textContent = modelId;
          modelSelect.appendChild(option);
        }

        if (data.models.length === 0) {
          const option = document.createElement("option");
          option.value = "";
          option.textContent = "没有可用模型";
          modelSelect.appendChild(option);
        }

        statusText.textContent = "就绪";
        tokenInfo.textContent = `已加载 ${data.token_count} 个 token，当前使用第 ${data.active_token_index + 1} 个。`;
      }

      async function readChatStream(response, bubble, session) {
        if (!response.body) {
          throw new Error("当前环境不支持流式响应");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let reply = "";
        let doneEvent = null;

        while (true) {
          const { value, done } = await reader.read();
          if (done) {
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.trim()) {
              continue;
            }

            const event = JSON.parse(line);
            if (event.type === "delta") {
              reply += event.content;
              bubble.textContent = reply;
              chatLog.scrollTop = chatLog.scrollHeight;
            } else if (event.type === "done") {
              doneEvent = event;
            } else if (event.type === "error") {
              throw new Error(event.error || "请求失败");
            }
          }
        }

        buffer += decoder.decode();
        if (buffer.trim()) {
          const event = JSON.parse(buffer);
          if (event.type === "delta") {
            reply += event.content;
            bubble.textContent = reply;
          } else if (event.type === "done") {
            doneEvent = event;
          } else if (event.type === "error") {
            throw new Error(event.error || "请求失败");
          }
        }

        session.messages.push({ role: "assistant", content: reply });
        renderSessions();
        renderActiveSession();
        return doneEvent;
      }

      chatForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const session = getActiveSession();
        const message = messageInput.value.trim();
        const model = modelSelect.value;

        if (!session) {
          window.alert("请先新建对话");
          return;
        }
        if (!model) {
          window.alert("请先选择模型");
          return;
        }
        if (!message) {
          return;
        }

        session.messages.push({ role: "user", content: message });
        renderActiveSession();
        messageInput.value = "";
        setLoading(true);
        requestHint.textContent = "正在请求模型...";
        const assistantBubble = createMessageElement("assistant", "");

        try {
          const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ model, message })
          });

          if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || "请求失败");
          }

          const doneEvent = await readChatStream(response, assistantBubble, session);
          if (doneEvent) {
            requestHint.textContent = `已完成，本次使用 token #${doneEvent.token_index + 1}`;
            tokenInfo.textContent = `已加载 ${doneEvent.token_count} 个 token，当前使用第 ${doneEvent.token_index + 1} 个。`;
          } else {
            requestHint.textContent = "已完成，但未收到结束状态";
          }
        } catch (error) {
          const errorText = `请求失败：${error.message}`;
          assistantBubble.textContent = errorText;
          session.messages.push({ role: "assistant", content: errorText });
          renderActiveSession();
          requestHint.textContent = "请求失败";
        } finally {
          setLoading(false);
        }
      });

      messageInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          chatForm.requestSubmit();
        }
      });

      newChatButton.addEventListener("click", () => {
        createSession();
      });

      async function bootstrap() {
        try {
          await loadModels();
        } catch (error) {
          statusText.textContent = "异常";
          tokenInfo.textContent = error.message;
        }
        createSession();
      }

      bootstrap();
    </script>
  </body>
</html>
"""


class TokenPool:
    def __init__(self, tokens: list[str]) -> None:
        if not tokens:
            raise ValueError("No API tokens found in auth file.")
        self.tokens = tokens
        self.index = 0
        self.lock = Lock()

    def current_token(self) -> tuple[int, str]:
        with self.lock:
            return self.index, self.tokens[self.index]

    def rotate(self) -> tuple[int, str]:
        with self.lock:
            self.index = (self.index + 1) % len(self.tokens)
            return self.index, self.tokens[self.index]

    def snapshot(self) -> dict[str, int]:
        with self.lock:
            return {"token_count": len(self.tokens), "active_token_index": self.index}


def find_token_file() -> Path:
    for candidate in TOKEN_FILE_CANDIDATES:
        path = Path(candidate)
        if path.exists():
            return path
    raise FileNotFoundError("Missing autg.txt/auth.txt token file.")


def load_tokens() -> list[str]:
    content = find_token_file().read_text(encoding="utf-8")
    tokens = TOKEN_PATTERN.findall(content)
    unique_tokens = list(dict.fromkeys(token.strip() for token in tokens if token.strip()))
    if not unique_tokens:
        raise ValueError("No usable token found in autg.txt/auth.txt.")
    return unique_tokens


def make_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=BASE_URL)


def list_model_ids(pool: TokenPool) -> list[str]:
    last_error = None
    for _ in range(len(pool.tokens)):
        _token_index, token = pool.current_token()
        try:
            models = make_client(token).models.list()
            return sorted({model.id for model in models.data})
        except Exception as exc:
            last_error = exc
            if not should_rotate_token(exc):
                raise
            pool.rotate()
    raise RuntimeError(f"Unable to list models with available tokens: {last_error}")


def should_rotate_token(error: Exception) -> bool:
    status_code = getattr(error, "status_code", None)
    if status_code in {401, 402, 403, 429}:
        return True
    message = str(error).lower()
    return any(hint in message for hint in QUOTA_HINTS)


def request_completion(pool: TokenPool, model: str, message: str) -> dict[str, Any]:
    last_error = None
    for _ in range(len(pool.tokens)):
        token_index, token = pool.current_token()
        try:
            completion = make_client(token).chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": message}],
            )
            reply = completion.choices[0].message.content or ""
            return {
                "reply": reply,
                "token_index": token_index,
                "token_count": len(pool.tokens),
            }
        except Exception as exc:
            last_error = exc
            if not should_rotate_token(exc):
                raise
            pool.rotate()
    raise RuntimeError(f"All tokens failed: {last_error}")


def stream_completion(pool: TokenPool, model: str, message: str) -> Iterator[dict[str, Any]]:
    last_error = None
    for _ in range(len(pool.tokens)):
        token_index, token = pool.current_token()
        try:
            stream = make_client(token).chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": message}],
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    yield {"type": "delta", "content": delta}
            yield {
                "type": "done",
                "token_index": token_index,
                "token_count": len(pool.tokens),
            }
            return
        except Exception as exc:
            last_error = exc
            if not should_rotate_token(exc):
                raise
            pool.rotate()
    raise RuntimeError(f"All tokens failed: {last_error}")


app = Flask(__name__)
token_pool = TokenPool(load_tokens())


@app.get("/")
def index() -> str:
    return render_template_string(INDEX_HTML)


@app.get("/api/models")
def api_models():
    try:
        models = list_model_ids(token_pool)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    payload = token_pool.snapshot()
    payload["models"] = models
    return jsonify(payload)


@app.post("/api/chat")
def api_chat():
    payload = request.get_json(silent=True) or {}
    model = str(payload.get("model", "")).strip()
    message = str(payload.get("message", "")).strip()
    if not model:
        return jsonify({"error": "model is required"}), 400
    if not message:
        return jsonify({"error": "message is required"}), 400

    def generate():
        try:
            for event in stream_completion(token_pool, model, message):
                yield json.dumps(event, ensure_ascii=False) + "\n"
        except Exception as exc:
            yield json.dumps({"type": "error", "error": str(exc)}, ensure_ascii=False) + "\n"

    return Response(stream_with_context(generate()), mimetype="application/x-ndjson")


if __name__ == "__main__":
    print(f"Loaded {len(token_pool.tokens)} tokens from {find_token_file().name}")
    print(f"Open http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=True)
