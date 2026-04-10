import json

import requests


API_URL = "https://api.us-west-2.modal.direct/v1/chat/completions"
MODELS_URL = "https://api.us-west-2.modal.direct/v1/models"
API_KEY = "modalresearch_hT-5ypZwMUiOiRt6fOaX1oTOf9JCCOQ2XwO49IAiaCU"
MODEL = "zai-org/GLM-5.1-FP8"
MAX_TOKENS = 500
TIMEOUT_SECONDS = 120


def request_headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }


def list_models() -> list[str]:
    response = requests.get(
        MODELS_URL,
        headers=request_headers(),
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    return sorted(item["id"] for item in payload.get("data", []))


def chat(messages: list[dict[str, str]], model: str) -> str:
    response = requests.post(
        API_URL,
        headers=request_headers(),
        json={
            "model": model,
            "messages": messages,
            "max_tokens": MAX_TOKENS,
        },
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    return payload["choices"][0]["message"]["content"]


def main() -> None:
    try:
        models = list_models()
    except requests.HTTPError as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        print(f"Failed to list models: {detail}")
        return
    except requests.RequestException as exc:
        print(f"Network error while listing models: {exc}")
        return
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"Unexpected model list format: {exc}")
        return

    if not models:
        print("No models returned by the API.")
        return

    print("Available models:")
    for index, model_id in enumerate(models, start=1):
        marker = " (default)" if model_id == MODEL else ""
        print(f"{index}. {model_id}{marker}")

    selected_model = MODEL if MODEL in models else models[0]
    raw_choice = input(f"Choose model [default: {selected_model}]: ").strip()
    if raw_choice:
        if raw_choice.isdigit():
            chosen_index = int(raw_choice) - 1
            if 0 <= chosen_index < len(models):
                selected_model = models[chosen_index]
            else:
                print("Invalid number, using default model.")
        elif raw_choice in models:
            selected_model = raw_choice
        else:
            print("Unknown model, using default model.")

    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": "You are a helpful assistant.",
        }
    ]

    print(f"Modal GLM chat started with model: {selected_model}")
    print("Type 'exit' to quit, 'clear' to reset history.")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("Bye.")
            break
        if user_input.lower() == "clear":
            messages = [messages[0]]
            print("History cleared.")
            continue

        messages.append({"role": "user", "content": user_input})

        try:
            reply = chat(messages, selected_model)
        except requests.HTTPError as exc:
            detail = exc.response.text if exc.response is not None else str(exc)
            print(f"Request failed: {detail}")
            messages.pop()
            continue
        except requests.RequestException as exc:
            print(f"Network error: {exc}")
            messages.pop()
            continue
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            print(f"Unexpected response format: {exc}")
            messages.pop()
            continue

        messages.append({"role": "assistant", "content": reply})
        print(f"Assistant: {reply}")


if __name__ == "__main__":
    main()
