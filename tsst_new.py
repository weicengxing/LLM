import os

import modal


# Temporary local fallbacks for quick verification.
# Replace or remove these after testing to avoid keeping secrets in code.
HARDCODED_CUSTOM = "sk-custom"

image = modal.Image.debian_slim().pip_install("openai")
app = modal.App("secret-check-and-openai", image=image)


@app.function(secrets=[modal.Secret.from_name("custom-secret")])
def show_custom_value() -> str:
    return os.getenv("custom", HARDCODED_CUSTOM)


@app.function(
    secrets=[
        modal.Secret.from_name("custom-secret"),
        modal.Secret.from_name("openai"),
    ]
)
def complete_text(
    prompt: str = "The easiest way to deploy a serverless GPU function in Python is ",
) -> str:
    from openai import OpenAI

    api_key = (
        os.getenv("OPENAI_API_KEY")
        or os.getenv("openai")
        or os.getenv("custom")
    )
    if not api_key:
        available_keys = ", ".join(
            key for key in ("OPENAI_API_KEY", "openai", "custom") if os.getenv(key)
        ) or "none"
        raise RuntimeError(
            "No OpenAI API key found in remote env. Expected one of: "
            "OPENAI_API_KEY, openai, custom. "
            f"Available populated keys: {available_keys}"
        )
    client = OpenAI(api_key=api_key)
    completion = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
    )
    return completion.choices[0].message.content or ""


@app.local_entrypoint()
def main(prompt: str = "The easiest way to deploy a serverless GPU function in Python is "):
    print(f"custom={show_custom_value.remote()}")
    print(complete_text.remote(prompt))
