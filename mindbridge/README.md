# MindBridge (Local-first mental health support)

MindBridge is a **local-first, privacy-preserving mental health support app** that runs Phi-3 locally via Ollama. **No API keys** are required and **no data leaves your machine**.

**Disclaimer:** MindBridge is not a substitute for professional mental health care.

## Setup

1. Install Ollama: https://ollama.com
2. Pull a model:

```bash
ollama pull phi3:mini
```

3. Install Python deps:

```bash
pip install -r requirements.txt
```

4. Create your env file:

```bash
cp .env.example .env
```

5. Run:

```bash
python app.py
```

6. Open `http://127.0.0.1:5000`

## Configuration

- `OLLAMA_BASE_URL`: Ollama server URL (default `http://localhost:11434`)
- `OLLAMA_MODEL`: default is `phi3:mini`; set any installed Ollama chat model if you want
- `MONGO_URI`: optional; when set, MindBridge uses MongoDB instead of SQLite

