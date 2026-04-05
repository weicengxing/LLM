from dataclasses import dataclass


@dataclass
class TrainConfig:
    data_path: str = "data/sample_corpus.txt"
    output_dir: str = "artifacts"
    batch_size: int = 16
    block_size: int = 64
    max_steps: int = 600
    eval_interval: int = 100
    learning_rate: float = 3e-4
    weight_decay: float = 0.01
    n_layers: int = 4
    n_heads: int = 4
    n_embd: int = 128
    dropout: float = 0.1
    device: str = "cpu"
    seed: int = 42
