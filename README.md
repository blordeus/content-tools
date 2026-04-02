# Content Tools

Two desktop apps for repurposing content across publications.

---

## Tools

### Sarcastic Joys — Essay Repurposing (`sarcastic-joys/`)

Paste a finished essay, get four pieces back:

- Instagram caption
- Instagram carousel (slide-by-slide)
- Substack Note — direct pull from the essay
- Substack Note — fresh observation triggered by the essay

**Files:**
- `sj_gui.py` — desktop GUI
- `repurpose.py` — CLI version

### Elite Executive — Substack Notes (`elite-executive/`)

Paste 1–3 newsletter URLs, get two Substack notes per link:

- Note A — click-driver with a verbatim hook and CTA
- Note B — standalone aphoristic insight, no link needed

**Files:**
- `ee_gui.py` — desktop GUI
- `elite_exec.py` — CLI version

---

## Setup

**Requirements:** Python 3.10+, VS Code

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/content-tools.git
cd content-tools

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate.bat       # Windows CMD
.venv\Scripts\Activate.ps1       # Windows PowerShell

# Install dependencies
pip install anthropic openai customtkinter rich
```

**Run the apps:**

```bash
python sarcastic-joys/sj_gui.py
python elite-executive/ee_gui.py
```

---

## Shortcuts (Windows)

Two batch files handle venv activation and launch in one double-click:

- `launch_sj.bat` — launches Sarcastic Joys
- `launch_ee.bat` — launches Elite Executive

> If you move the project folder, update the path inside each `.bat` file.

---

## AI Backends

Both apps support four backends, switchable from the UI:

| Backend | Cost | Default Model |
|---|---|---|
| Anthropic (Claude) | Paid | claude-opus-4-5 |
| Groq | Free tier | llama-3.3-70b-versatile |
| Ollama | Free / offline | llama3.2 |
| OpenAI | Paid | gpt-4o-mini |

Anthropic produces the sharpest output. Groq is the best free option. Ollama runs fully offline with no API key.

---

## API Keys

Keys are saved to `~/.config/` on first use and persist across sessions. They are excluded from Git via `.gitignore`.

| Backend | Get a key |
|---|---|
| Anthropic | https://console.anthropic.com |
| Groq | https://console.groq.com/keys |
| OpenAI | https://platform.openai.com/api-keys |
| Ollama | No key needed — install from https://ollama.com |

Enter the key in the app's top bar and click **Save**. Or set it as an environment variable:

```bash
# Add to your shell profile or set in Windows System Environment Variables
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=sk-...
```

---

## Updating

```bash
git add .
git commit -m "your message"
git push
```
