from pathlib import Path
import random

import torch

from src.mini_llm.config import TrainConfig
from src.mini_llm.data import LanguageModelingDataset


def set_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def train_model(
    model: torch.nn.Module,
    dataset: LanguageModelingDataset,
    config: TrainConfig,
    device: str,
) -> None:
    set_seed(config.seed)
    Path(config.output_dir).mkdir(parents=True, exist_ok=True)

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )

    model.train()
    for step in range(1, config.max_steps + 1):
        x, y = dataset.sample_batch(batch_size=config.batch_size, device=device)
        _, loss = model(x, y)

        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

        if step % config.eval_interval == 0 or step == 1 or step == config.max_steps:
            print(f"step={step:04d} loss={loss.item():.4f}")
