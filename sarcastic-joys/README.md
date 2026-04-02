# Content Repurposing Agent

Turn long-form essays or articles into platform-specific content using your choice of AI backend.

Produces four pieces from any source text:
1. Instagram caption
2. Instagram carousel (slide-by-slide)
3. Substack/newsletter note — direct pull
4. Substack/newsletter note — fresh observation

---

## Backends

| Backend     | Cost          | Requires             | Default model              |
|-------------|---------------|----------------------|----------------------------|
| `anthropic` | Paid          | Anthropic API key    | claude-opus-4-5             |
| `groq`      | Free tier     | Groq API key         | llama-3.3-70b-versatile    |
| `ollama`    | Free/offline  | Ollama running locally | llama3.2                 |
| `openai`    | Paid          | OpenAI API key       | gpt-4o-mini                |

---

## Setup

```bash
pip install -r requirements.txt
```

### Ollama (fully offline)

1. Install Ollama from https://ollama.com
2. Pull a model:
   ```bash
   ollama pull llama3.2
   # or: ollama pull mistral, ollama pull qwen2.5:14b, etc.
   ```
3. Run with:
   ```bash
   python repurpose.py --backend ollama -i essay.txt
   ```

### Groq (free cloud)

1. Get a free API key at https://console.groq.com/keys
2. Save it:
   ```bash
   python repurpose.py --set-key groq
   ```
3. Run with:
   ```bash
   python repurpose.py --backend groq -i essay.txt
   ```

### Anthropic / OpenAI

```bash
python repurpose.py --set-key anthropic
python repurpose.py --set-key openai
```

Or pass keys via environment variables:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
export GROQ_API_KEY=gsk_...
export OPENAI_API_KEY=sk-...
```

---

## Usage

```bash
# Paste mode (interactive)
python repurpose.py

# Read from file
python repurpose.py -i my_essay.txt

# Specific backend
python repurpose.py --backend ollama -i my_essay.txt
python repurpose.py --backend groq -i my_essay.txt

# Specific model
python repurpose.py --backend ollama --model mistral -i my_essay.txt
python repurpose.py --backend groq --model mixtral-8x7b-32768 -i my_essay.txt

# Save output to a specific directory
python repurpose.py -i my_essay.txt -o ./repurposed

# Print to stdout only
python repurpose.py -i my_essay.txt --no-save

# Pipe from stdin
cat essay.txt | python repurpose.py --backend groq

# Show all backends
python repurpose.py --list-backends
```

---

## Custom System Prompts

```bash
# Export the default prompt to edit it
python repurpose.py --show-prompt > my_prompt.txt

# Save your edited version under a name
python repurpose.py --prompt-file my_prompt.txt --save-prompt my_brand

# Use it
python repurpose.py -i essay.txt --prompt my_brand

# List saved prompts
python repurpose.py --list-prompts
```

Saved prompts live in `~/.config/repurpose_agent/prompts/`.

---

## All Options

```
-i, --input FILE          Input file (default: interactive paste mode)
-o, --output-dir DIR      Directory to save output (default: ./output)
--no-save                 Print to stdout only
--backend BACKEND         anthropic | groq | ollama | openai (default: anthropic)
--model MODEL             Override the backend's default model
--ollama-url URL          Ollama base URL (default: http://localhost:11434/v1)
--prompt NAME             Use a saved custom prompt
--prompt-file FILE        Load system prompt from a file
--save-prompt NAME        Save the active prompt under NAME and exit
--list-prompts            List saved prompts and exit
--show-prompt             Print the active system prompt and exit
--list-backends           Show all backends with defaults and exit
--set-key BACKEND         Save an API key for a backend and exit
```
