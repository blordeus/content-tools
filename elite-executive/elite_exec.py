#!/usr/bin/env python3
"""
Elite Executive — Substack Notes Generator

Fetches newsletter URLs and generates two Substack notes per link:
  Note A — Click-driver: pulls a sharp hook from the content, ends with a CTA
  Note B — Standalone insight: a fresh observation triggered by the content

Supported backends: anthropic | groq | ollama | openai
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
from html.parser import HTMLParser

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.rule import Rule
    from rich.markdown import Markdown
    from rich.table import Table
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

console = Console() if HAS_RICH else None

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a content repurposing agent for Elite Executive, a Substack publication \
written for senior leaders, operators, and executives who think carefully about \
business, strategy, and the craft of leadership.

The voice is confident but conversational — the kind of person who has seen \
enough to have real opinions, doesn't need to perform certainty, and respects \
the reader's intelligence. No hype. No jargon for its own sake. No motivational \
filler. Write like someone who has been in the room.

You will be given the full text of a newsletter. From it, produce exactly two \
Substack notes.

---

## NOTE A — Click-Driver

Purpose: Pull the reader in and send them to the full newsletter.

Rules:
- Open with the single sharpest line from the newsletter — pulled verbatim
- Follow with 2–3 sentences of plain, direct context that earns that line
- End with this exact CTA: "Full issue linked below."
- No hashtags
- 80–120 words maximum
- Do not summarise the whole piece — tease one specific idea

---

## NOTE B — Standalone Insight

Purpose: A single observation worth reading on its own, with no link needed.

Rules:
- Written fresh — triggered by the newsletter's core idea, not copied from it
- 1–3 sentences maximum
- Aphoristic and understated — confident, not preachy
- No CTA, no setup, no reference to the newsletter
- Reads like something a sharp operator thought in the shower, not at a desk
- If it needs more than three sentences, cut until it doesn't

---

## OUTPUT FORMAT

Return your response in this exact structure, with no preamble:

### NOTE A — Click-Driver

[note text]

---

### NOTE B — Standalone Insight

[note text]

---

## QUALITY CHECK

Before responding, verify:
- Does Note A open with a verbatim line from the newsletter?
- Does Note B contain zero references to the newsletter?
- Is Note B genuinely fresh — not a paraphrase of something already on the page?
- Is there a single word of hype, filler, or motivational padding anywhere?

If any check fails, rewrite before outputting.
"""

# ── Backend config ────────────────────────────────────────────────────────────

BACKEND_DEFAULTS = {
    "anthropic": {
        "model": "claude-opus-4-5",
        "base_url": None,
        "env_key": "ANTHROPIC_API_KEY",
        "config_key": "anthropic_api_key",
        "label": "Anthropic (Claude)",
        "key_url": "https://console.anthropic.com/",
    },
    "groq": {
        "model": "llama-3.3-70b-versatile",
        "base_url": "https://api.groq.com/openai/v1",
        "env_key": "GROQ_API_KEY",
        "config_key": "groq_api_key",
        "label": "Groq (free tier)",
        "key_url": "https://console.groq.com/keys",
    },
    "ollama": {
        "model": "llama3.2",
        "base_url": "http://localhost:11434/v1",
        "env_key": None,
        "config_key": None,
        "label": "Ollama (local)",
        "key_url": None,
    },
    "openai": {
        "model": "gpt-4o-mini",
        "base_url": None,
        "env_key": "OPENAI_API_KEY",
        "config_key": "openai_api_key",
        "label": "OpenAI",
        "key_url": "https://platform.openai.com/api-keys",
    },
}

# ── Config ────────────────────────────────────────────────────────────────────

CONFIG_PATH = Path.home() / ".config" / "elite_exec" / "config.json"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}


def save_config(cfg: dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def _ask(prompt: str, password: bool = False) -> str:
    if HAS_RICH:
        return Prompt.ask(f"[bold yellow]{prompt}[/bold yellow]", password=password)
    if password:
        import getpass
        return getpass.getpass(f"{prompt}: ")
    return input(f"{prompt}: ").strip()


def _confirm(prompt: str) -> bool:
    if HAS_RICH:
        return Confirm.ask(prompt)
    return input(f"{prompt} (y/n): ").lower().startswith("y")


def get_api_key(cfg: dict, backend: str) -> str:
    meta = BACKEND_DEFAULTS[backend]
    if meta["env_key"] is None:
        return "ollama"
    key = os.environ.get(meta["env_key"], "") or cfg.get(meta["config_key"], "")
    if key:
        return key
    if meta["key_url"]:
        msg = f"Get one at {meta['key_url']}"
        console.print(f"[dim]{msg}[/dim]") if HAS_RICH else print(msg)
    key = _ask(f"{meta['label']} API key", password=True)
    if key and _confirm("Save key to config?"):
        cfg[meta["config_key"]] = key
        save_config(cfg)
    return key

# ── HTML → plain text ─────────────────────────────────────────────────────────

class _TextExtractor(HTMLParser):
    """Minimal HTML stripper that preserves paragraph breaks."""
    SKIP_TAGS = {"script", "style", "nav", "header", "footer", "noscript", "svg"}

    def __init__(self):
        super().__init__()
        self.chunks: list[str] = []
        self._skip_depth = 0
        self._block_tags = {
            "p", "h1", "h2", "h3", "h4", "h5", "h6",
            "li", "blockquote", "div", "section", "article",
        }

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
        if tag in self._block_tags and self.chunks and self.chunks[-1] != "\n\n":
            self.chunks.append("\n\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)

    def handle_data(self, data):
        if self._skip_depth == 0:
            text = data.strip()
            if text:
                self.chunks.append(text + " ")

    def get_text(self) -> str:
        import re
        text = "".join(self.chunks)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)
        return text.strip()


def fetch_url(url: str, timeout: int = 15) -> str:
    """Fetch a URL and return clean plain text. No third-party deps."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            charset = "utf-8"
            ct = resp.headers.get_content_charset()
            if ct:
                charset = ct
            html = raw.decode(charset, errors="replace")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} fetching {url}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach {url}: {e.reason}") from e

    parser = _TextExtractor()
    parser.feed(html)
    text = parser.get_text()

    # Truncate to ~6000 words to stay within context limits
    words = text.split()
    if len(words) > 6000:
        text = " ".join(words[:6000]) + "\n\n[truncated]"
    return text

# ── LLM callers ───────────────────────────────────────────────────────────────

def _call_anthropic(content: str, api_key: str, model: str) -> str:
    try:
        import anthropic
    except ImportError:
        print("Missing: pip install anthropic")
        sys.exit(1)
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model=model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )
    return msg.content[0].text


def _call_openai_compat(content: str, api_key: str, model: str, base_url: str | None) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        print("Missing: pip install openai")
        sys.exit(1)
    kwargs: dict = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    client = OpenAI(**kwargs)
    resp = client.chat.completions.create(
        model=model,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
    )
    return resp.choices[0].message.content


def generate_notes(
    newsletter_text: str, url: str, api_key: str, model: str, backend: str, base_url: str | None = None
) -> str:
    prompt = f"Newsletter URL: {url}\n\n---\n\n{newsletter_text}"
    if backend == "anthropic":
        return _call_anthropic(prompt, api_key, model)
    resolved_url = base_url or BACKEND_DEFAULTS[backend]["base_url"]
    return _call_openai_compat(prompt, api_key, model, resolved_url)

# ── I/O helpers ───────────────────────────────────────────────────────────────

def read_urls_interactive() -> list[str]:
    """Prompt the user to paste URLs one per line."""
    if HAS_RICH:
        console.print(Panel(
            "[dim]Paste newsletter URLs — one per line.\n"
            "Ctrl-D (macOS/Linux) or Ctrl-Z then Enter (Windows) when done.[/dim]",
            title="[bold]URL Input[/bold]",
            border_style="dim",
        ))
    else:
        print("Paste newsletter URLs, one per line. Ctrl-D when done:\n")
    lines = []
    try:
        while True:
            line = input().strip()
            if line:
                lines.append(line)
    except EOFError:
        pass
    return lines


def read_urls_from_file(path: str) -> list[str]:
    return [
        line.strip()
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def save_output(results: list[dict], output_dir: str | None) -> Path:
    out_dir = Path(output_dir) if output_dir else Path.cwd() / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"elite_exec_notes_{timestamp}.md"

    lines = [f"# Elite Executive — Substack Notes\n\nGenerated: {datetime.now():%B %d, %Y %H:%M}\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"---\n\n## Newsletter {i}\n\n**URL:** {r['url']}\n")
        if r.get("error"):
            lines.append(f"**Error:** {r['error']}\n")
        else:
            lines.append(r["notes"])
            lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def display_result(url: str, notes: str, index: int, total: int):
    if HAS_RICH:
        console.print(Rule(f"[bold]Newsletter {index}/{total}[/bold]"))
        console.print(f"[dim]{url}[/dim]\n")
        console.print(Markdown(notes))
    else:
        print(f"\n{'='*60}")
        print(f"Newsletter {index}/{total}: {url}")
        print("="*60)
        print(notes)

# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="elite_exec",
        description="Elite Executive — generate Substack notes from newsletter URLs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  elite_exec                              # paste URLs interactively
  elite_exec -i urls.txt                 # read URLs from file
  elite_exec --backend groq              # use Groq (free)
  elite_exec --backend ollama            # use Ollama (offline)
  elite_exec --set-key groq              # save a Groq API key
  elite_exec --list-backends             # show all backends
        """,
    )
    p.add_argument("-i", "--input", metavar="FILE",
                   help="Text file with one URL per line (default: interactive)")
    p.add_argument("-o", "--output-dir", metavar="DIR",
                   help="Directory to save output (default: ./output)")
    p.add_argument("--no-save", action="store_true",
                   help="Print to stdout only, don't save file")
    p.add_argument(
        "--backend",
        choices=list(BACKEND_DEFAULTS.keys()),
        default="anthropic",
        help="AI backend (default: anthropic)",
    )
    p.add_argument("--model", metavar="MODEL",
                   help="Override the backend's default model")
    p.add_argument("--ollama-url", metavar="URL", default=None,
                   help="Ollama base URL (default: http://localhost:11434/v1)")
    p.add_argument("--fetch-timeout", type=int, default=15, metavar="SECONDS",
                   help="URL fetch timeout in seconds (default: 15)")
    p.add_argument("--list-backends", action="store_true",
                   help="Show all backends and exit")
    p.add_argument("--set-key", metavar="BACKEND",
                   help="Save an API key for a backend and exit")
    return p


def cmd_list_backends():
    cost = {"anthropic": "paid", "groq": "free tier", "ollama": "free/offline", "openai": "paid"}
    if HAS_RICH:
        t = Table(title="Available Backends", show_lines=True)
        t.add_column("Backend", style="bold cyan")
        t.add_column("Label")
        t.add_column("Default Model")
        t.add_column("Cost")
        t.add_column("Key URL")
        for name, meta in BACKEND_DEFAULTS.items():
            t.add_row(name, meta["label"], meta["model"], cost[name], meta["key_url"] or "n/a")
        console.print(t)
    else:
        for name, meta in BACKEND_DEFAULTS.items():
            print(f"{name:12} {meta['label']:28} {meta['model']}")


def main():
    parser = build_parser()
    args = parser.parse_args()
    cfg = load_config()

    if args.list_backends:
        cmd_list_backends()
        return

    if args.set_key:
        target = args.set_key
        if target not in BACKEND_DEFAULTS:
            print(f"Unknown backend '{target}'. Choose from: {list(BACKEND_DEFAULTS)}")
            sys.exit(1)
        meta = BACKEND_DEFAULTS[target]
        if meta["config_key"] is None:
            print(f"{target} doesn't use an API key.")
            return
        key = _ask(f"{meta['label']} API key", password=True)
        cfg[meta["config_key"]] = key
        save_config(cfg)
        print(f"Saved {target} API key.")
        return

    # ── Resolve backend + model ───────────────────────────────────────────────

    backend = args.backend
    meta = BACKEND_DEFAULTS[backend]
    model = args.model or meta["model"]
    base_url_override = args.ollama_url if backend == "ollama" and args.ollama_url else None

    api_key = get_api_key(cfg, backend)
    if not api_key:
        print("No API key. Exiting.")
        sys.exit(1)

    # ── Collect URLs ──────────────────────────────────────────────────────────

    urls = read_urls_from_file(args.input) if args.input else read_urls_interactive()
    if not urls:
        print("No URLs provided. Exiting.")
        sys.exit(1)

    if HAS_RICH:
        console.print(f"\n[bold]Processing {len(urls)} newsletter(s) via {meta['label']} ({model})[/bold]\n")
    else:
        print(f"\nProcessing {len(urls)} newsletter(s) via {meta['label']} ({model})\n")

    # ── Process each URL ──────────────────────────────────────────────────────

    results = []
    for i, url in enumerate(urls, 1):
        result: dict = {"url": url}

        # Fetch
        fetch_label = f"Fetching {url}"
        if HAS_RICH:
            with console.status(f"[dim]{fetch_label}…[/dim]", spinner="dots"):
                try:
                    text = fetch_url(url, timeout=args.fetch_timeout)
                except RuntimeError as e:
                    result["error"] = str(e)
                    console.print(f"[red]  ✗ {e}[/red]")
                    results.append(result)
                    continue
        else:
            print(f"  Fetching {url}…")
            try:
                text = fetch_url(url, timeout=args.fetch_timeout)
            except RuntimeError as e:
                result["error"] = str(e)
                print(f"  Error: {e}")
                results.append(result)
                continue

        # Generate
        gen_label = f"Generating notes ({meta['label']}, {model})"
        if HAS_RICH:
            with console.status(f"[bold green]{gen_label}…[/bold green]", spinner="dots"):
                notes = generate_notes(text, url, api_key, model, backend, base_url_override)
        else:
            print(f"  Generating notes…")
            notes = generate_notes(text, url, api_key, model, backend, base_url_override)

        result["notes"] = notes
        results.append(result)
        display_result(url, notes, i, len(urls))

    # ── Save ──────────────────────────────────────────────────────────────────

    if not args.no_save:
        saved_path = save_output(results, args.output_dir)
        if HAS_RICH:
            console.print(f"\n[dim]Saved → {saved_path}[/dim]")
        else:
            print(f"\nSaved → {saved_path}")


if __name__ == "__main__":
    main()
