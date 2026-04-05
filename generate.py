import argparse
from pathlib import Path

import torch

from src.mini_llm.checkpoint import load_checkpoint
from src.mini_llm.generation import generate_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate text with the trained Mini LLM.")
    parser.add_argument("--prompt", type=str, default="语言模型", help="Generation prompt.")
    parser.add_argument("--max-new-tokens", type=int, default=120, help="Maximum tokens to generate.")
    parser.add_argument("--temperature", type=float, default=0.8, help="Sampling temperature.")
    parser.add_argument("--top-k", type=int, default=20, help="Top-k sampling.")
    parser.add_argument("--checkpoint-dir", type=str, default="artifacts", help="Checkpoint directory.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    device = "cuda" if torch.cuda.is_available() else "cpu"

    model, tokenizer, _ = load_checkpoint(Path(args.checkpoint_dir), device=device)
    model.eval()

    output = generate_text(
        model=model,
        tokenizer=tokenizer,
        prompt=args.prompt,
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
        top_k=args.top_k,
        device=device,
    )
    print(output)


if __name__ == "__main__":
    main()
