# Elite Executive — Substack Notes Generator

Fetches your newsletter URLs and generates two Substack notes per issue:

- **Note A — Click-Driver**: Opens with a sharp verbatim line from the newsletter, adds 2–3 sentences of context, ends with "Full issue linked below."
- **Note B — Standalone Insight**: A fresh aphoristic observation triggered by the newsletter — no link needed, no setup required.

---

## Setup

```bash
pip install -r requirements.txt
```

Save your API key once:
```bash
python elite_exec.py --set-key anthropic   # paid, best quality
python elite_exec.py --set-key groq        # free tier
```

Or via environment variable:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
export GROQ_API_KEY=gsk_...
```

For fully offline use, install [Ollama](https://ollama.com) and pull a model:
```bash
ollama pull llama3.2
```

---

## Usage

```bash
# Paste URLs interactively (1–3 URLs, one per line, Ctrl-D to finish)
python elite_exec.py

# Read URLs from a file
python elite_exec.py -i urls.txt

# Use a specific backend
python elite_exec.py --backend groq
python elite_exec.py --backend ollama

# Save output to a specific directory
python elite_exec.py -o ./notes

# Print only, don't save
python elite_exec.py --no-save
```

**urls.txt format** (one URL per line, # for comments):
```
# Week 12 newsletters
https://newsletter.example.com/p/issue-42
https://newsletter.example.com/p/issue-43
```

---

## Output

Each run saves a timestamped Markdown file to `./output/` containing all generated notes, organized by URL. The notes are also printed to the terminal as they complete.

---

## Options

```
-i, --input FILE        Text file with one URL per line
-o, --output-dir DIR    Directory to save output (default: ./output)
--no-save               Print to stdout only
--backend BACKEND       anthropic | groq | ollama | openai (default: anthropic)
--model MODEL           Override the backend's default model
--ollama-url URL        Ollama base URL (default: http://localhost:11434/v1)
--fetch-timeout SECS    URL fetch timeout (default: 15)
--list-backends         Show all backends and exit
--set-key BACKEND       Save an API key and exit
```
