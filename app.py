from flask import Flask, jsonify, render_template, request

from src.mini_llm.chat import ChatService
from src.mini_llm.database import DatabaseManager
from src.mini_llm.repository import ChatRepository

app = Flask(__name__)
database_manager = DatabaseManager()
database_manager.ensure_schema()
chat_service = ChatService(repository=ChatRepository(database_manager))


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/health")
def health():
    payload = chat_service.status()
    payload["sessions"] = chat_service.list_sessions()
    return jsonify(payload)


@app.get("/api/sessions")
def list_sessions():
    return jsonify({"sessions": chat_service.list_sessions()})


@app.post("/api/sessions")
def create_session():
    payload = request.get_json(silent=True) or {}
    title = str(payload.get("title", "")).strip() or None
    session = chat_service.create_session(title=title)
    return jsonify({"session": session}), 201


@app.delete("/api/sessions/<int:session_id>")
def delete_session(session_id: int):
    try:
        chat_service.delete_session(session_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify({"ok": True})


@app.get("/api/sessions/<int:session_id>/messages")
def list_messages(session_id: int):
    if chat_service.repository.get_session(session_id) is None:
        return jsonify({"error": "session not found"}), 404
    return jsonify({"messages": chat_service.get_session_messages(session_id)})


@app.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message", "")).strip()
    session_id = payload.get("session_id")

    if not message:
        return jsonify({"error": "message is required"}), 400
    if session_id is None:
        return jsonify({"error": "session_id is required"}), 400

    try:
        result = chat_service.chat(session_id=int(session_id), message=message)
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 503
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": f"generation failed: {exc}"}), 500

    return jsonify(result)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
