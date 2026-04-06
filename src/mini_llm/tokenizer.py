import json
from dataclasses import dataclass
from pathlib import Path

UNK_TOKEN = "<UNK>"


@dataclass
class CharTokenizer:
    stoi: dict[str, int]
    itos: dict[int, str]

    @classmethod
    def from_text(cls, text: str) -> "CharTokenizer":
        vocab = [UNK_TOKEN] + sorted(set(text))
        stoi = {ch: idx for idx, ch in enumerate(vocab)}
        itos = {idx: ch for ch, idx in stoi.items()}
        return cls(stoi=stoi, itos=itos)

    @property
    def vocab_size(self) -> int:
        return len(self.stoi)

    def encode(self, text: str) -> list[int]:
        unk_id = self.stoi[UNK_TOKEN]
        return [self.stoi.get(ch, unk_id) for ch in text]

    def decode(self, token_ids: list[int]) -> str:
        chars = []
        for token_id in token_ids:
            token = self.itos[token_id]
            chars.append("[?]" if token == UNK_TOKEN else token)
        return "".join(chars)

    def save(self, path: Path) -> None:
        path.write_text(
            json.dumps({"stoi": self.stoi}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> "CharTokenizer":
        payload = json.loads(path.read_text(encoding="utf-8"))
        stoi = {k: int(v) for k, v in payload["stoi"].items()}
        itos = {idx: ch for ch, idx in stoi.items()}
        return cls(stoi=stoi, itos=itos)
