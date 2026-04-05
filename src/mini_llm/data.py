import torch

from src.mini_llm.tokenizer import CharTokenizer


class LanguageModelingDataset:
    def __init__(self, text: str, tokenizer: CharTokenizer, block_size: int) -> None:
        self.tokenizer = tokenizer
        self.block_size = block_size
        self.tokens = torch.tensor(tokenizer.encode(text), dtype=torch.long)
        if len(self.tokens) <= block_size:
            raise ValueError("Corpus is too small for the chosen block_size.")

    def __len__(self) -> int:
        return len(self.tokens) - self.block_size

    def sample_batch(self, batch_size: int, device: str) -> tuple[torch.Tensor, torch.Tensor]:
        starts = torch.randint(0, len(self), (batch_size,))
        x = torch.stack([self.tokens[i : i + self.block_size] for i in starts])
        y = torch.stack([self.tokens[i + 1 : i + self.block_size + 1] for i in starts])
        return x.to(device), y.to(device)
