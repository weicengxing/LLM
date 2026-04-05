from dataclasses import asdict
from pathlib import Path

import torch

from src.mini_llm.config import TrainConfig
from src.mini_llm.model import MiniGPT
from src.mini_llm.tokenizer import CharTokenizer


def save_checkpoint(
    model: MiniGPT,
    tokenizer: CharTokenizer,
    config: TrainConfig,
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "config": asdict(config),
            "vocab_size": tokenizer.vocab_size,
        },
        output_dir / "model.pt",
    )
    tokenizer.save(output_dir / "tokenizer.json")


def load_checkpoint(output_dir: Path, device: str) -> tuple[MiniGPT, CharTokenizer, TrainConfig]:
    checkpoint = torch.load(output_dir / "model.pt", map_location=device)
    config = TrainConfig(**checkpoint["config"])
    tokenizer = CharTokenizer.load(output_dir / "tokenizer.json")

    model = MiniGPT(
        vocab_size=checkpoint["vocab_size"],
        block_size=config.block_size,
        n_layers=config.n_layers,
        n_heads=config.n_heads,
        n_embd=config.n_embd,
        dropout=config.dropout,
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    return model, tokenizer, config
