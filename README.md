# Mini LLM Web Chat

This project is a from-scratch educational language model repo with a browser chat interface.

## Features

- Small GPT-style decoder-only transformer
- Character tokenizer with unknown-character fallback
- Local training script
- Flask backend for browser chat
- Simple frontend built with HTML, CSS, and JavaScript

## Files

```text
.
|-- app.py
|-- train.py
|-- requirements.txt
|-- data/
|   `-- sample_corpus.txt
|-- templates/
|   `-- index.html
|-- static/
|   |-- app.js
|   `-- style.css
`-- src/
    `-- mini_llm/
        |-- chat.py
        |-- checkpoint.py
        |-- config.py
        |-- data.py
        |-- generation.py
        |-- model.py
        |-- tokenizer.py
        `-- trainer.py
```

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Train

```bash
python train.py
```

Training creates files in `artifacts/`.

## Start the web app

```bash
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

## Notes

- This is a teaching project, not a production LLM stack.
- The browser app expects a trained checkpoint.
- The sample corpus includes a few dialogue-style lines for the chat prompt format.
- You can extend it later with BPE, streaming, richer datasets, and persistent chat history.
