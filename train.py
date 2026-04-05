from pathlib import Path

import torch

from src.mini_llm.checkpoint import save_checkpoint
from src.mini_llm.config import TrainConfig
from src.mini_llm.data import LanguageModelingDataset
from src.mini_llm.model import MiniGPT
from src.mini_llm.tokenizer import CharTokenizer
from src.mini_llm.trainer import train_model


def main() -> None:
    config = TrainConfig()
    data_path = Path(config.data_path)
    text = data_path.read_text(encoding="utf-8")

    tokenizer = CharTokenizer.from_text(text)
    dataset = LanguageModelingDataset(
        text=text,
        tokenizer=tokenizer,
        block_size=config.block_size,
    )

    model = MiniGPT(
        vocab_size=tokenizer.vocab_size,
        block_size=config.block_size,
        n_layers=config.n_layers,
        n_heads=config.n_heads,
        n_embd=config.n_embd,
        dropout=config.dropout,
    )

    device = config.device if torch.cuda.is_available() or config.device == "cpu" else "cpu"
    model.to(device)

    print(f"Using device: {device}")
    print(f"Vocabulary size: {tokenizer.vocab_size}")
    print(f"Training samples: {len(dataset)}")

    train_model(
        model=model,
        dataset=dataset,
        config=config,
        device=device,
    )

    save_checkpoint(
        model=model,
        tokenizer=tokenizer,
        config=config,
        output_dir=Path(config.output_dir),
    )
    print(f"Checkpoint saved to: {config.output_dir}")


if __name__ == "__main__":
    main()
