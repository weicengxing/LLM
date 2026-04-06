from pathlib import Path

import torch

from src.mini_llm.checkpoint import load_checkpoint
from src.mini_llm.generation import generate_text
from src.mini_llm.repository import ChatRepository


class ChatService:
    def __init__(self, repository: ChatRepository, checkpoint_dir: str = "artifacts") -> None:
        self.repository = repository
        self.checkpoint_dir = Path(checkpoint_dir)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.tokenizer = None
        self.config = None

    def status(self) -> dict[str, object]:
        ready = (self.checkpoint_dir / "model.pt").exists() and (
            self.checkpoint_dir / "tokenizer.json"
        ).exists()
        return {
            "ready": ready,
            "device": self.device,
            "checkpoint_dir": str(self.checkpoint_dir),
        }

    def _ensure_loaded(self) -> None:
        if self.model is not None and self.tokenizer is not None:
            return

        if not (self.checkpoint_dir / "model.pt").exists():
            raise FileNotFoundError(
                "Model checkpoint not found. Please run `python train.py` first."
            )

        self.model, self.tokenizer, self.config = load_checkpoint(
            self.checkpoint_dir,
            device=self.device,
        )
        self.model.eval()

    def _build_prompt(self, message: str, history: list[dict]) -> str:
        turns = [
            "系统：你是一个友好、简洁的中文助手。",
            "系统：请直接回答用户问题，不要续写角色标签，不要伪造新的用户发言。",
        ]
        for item in history[-6:]:
            role = str(item.get("role", "user"))
            content = str(item.get("content", "")).strip()
            if not content:
                continue
            if role == "assistant":
                turns.append(f"助手：{content}")
            else:
                turns.append(f"用户：{content}")

        turns.append(f"用户：{message}")
        turns.append("助手：")
        return "\n".join(turns)

    def _clean_reply(self, text: str) -> str:
        cleaned = text.strip()
        for prefix in ("助手：", "Assistant:", "assistant:", "答："):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix) :].strip()
        for stop_marker in ("用户：", "\n用户：", "\nAssistant:", "\nassistant:"):
            if stop_marker in cleaned:
                cleaned = cleaned.split(stop_marker)[0].strip()
        return cleaned

    def reply(self, message: str, history: list[dict] | None = None) -> str:
        self._ensure_loaded()
        prompt = self._build_prompt(message=message, history=history or [])
        output = generate_text(
            model=self.model,
            tokenizer=self.tokenizer,
            prompt=prompt,
            max_new_tokens=120,
            temperature=0.8,
            top_k=20,
            device=self.device,
        )

        completion = output[len(prompt) :]
        cleaned = self._clean_reply(completion)
        if not cleaned:
            cleaned = "我收到了你的消息，不过当前这个小模型还需要更多训练数据，回答才会更稳定。"
        return cleaned

    def create_session(self, title: str | None = None) -> dict:
        session = self.repository.create_session(title=title or "新会话")
        return self._serialize_session(session)

    def list_sessions(self) -> list[dict]:
        sessions = self.repository.list_sessions()
        return [self._serialize_session(item) for item in sessions]

    def get_session_messages(self, session_id: int) -> list[dict]:
        messages = self.repository.list_messages(session_id)
        return [self._serialize_message(item) for item in messages]

    def delete_session(self, session_id: int) -> None:
        deleted = self.repository.delete_session(session_id)
        if deleted == 0:
            raise ValueError("session not found")

    def chat(self, session_id: int, message: str) -> dict:
        session = self.repository.get_session(session_id)
        if session is None:
            raise ValueError("session not found")

        history = self.repository.list_messages(session_id)
        user_message = self.repository.add_message(session_id, "user", message)

        reply_text = self.reply(
            message=message,
            history=[{"role": item["role"], "content": item["content"]} for item in history],
        )
        assistant_message = self.repository.add_message(session_id, "assistant", reply_text)

        if session["title"] == "新会话":
            title = message[:40].strip() or "新会话"
            self.repository.update_session_title(session_id, title)

        self.repository.touch_session(session_id)
        return {
            "session": self._serialize_session(self.repository.get_session(session_id)),
            "user_message": self._serialize_message(user_message),
            "assistant_message": self._serialize_message(assistant_message),
        }

    def _serialize_session(self, session: dict | None) -> dict | None:
        if session is None:
            return None
        payload = {
            "id": session["id"],
            "title": session["title"],
            "created_at": session["created_at"].isoformat(),
            "updated_at": session["updated_at"].isoformat(),
        }
        if "message_count" in session:
            payload["message_count"] = int(session["message_count"])
        if "last_message" in session:
            payload["last_message"] = session["last_message"] or ""
        return payload

    def _serialize_message(self, message: dict) -> dict:
        return {
            "id": message["id"],
            "session_id": message["session_id"],
            "role": message["role"],
            "content": message["content"],
            "created_at": message["created_at"].isoformat(),
        }
