#!/usr/bin/env python3
"""
Content Repurposing Agent
Turns long-form essays/articles into platform-specific content.

Supported backends:
  anthropic  — Claude via Anthropic API (paid)
  groq       — Llama/Mixtral via Groq API (free tier)
  ollama     — Any model running locally via Ollama (free, offline)
  openai     — OpenAI-compatible endpoint (generic fallback)
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.rule import Rule
    from rich.markdown import Markdown
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

console = Console() if HAS_RICH else None

# ── Default system prompt ─────────────────────────────────────────────────────

DEFAULT_SYSTEM_PROMPT = """\
You are a content repurposing agent. Your job is to take a finished long-form \
piece of writing and extract platform-specific content from it with minimal \
reinvention. You are a curator, not a rewriter.

## YOUR ONE RULE
Pull the best lines directly from the source text. Do not paraphrase. Do not \
improve. Do not reimagine. The writing has already been edited to the author's \
standard — your job is to identify what is already strong and reformat it for \
each platform.

The only exception is Note #2, which is triggered by the source but written \
fresh as a standalone aphoristic observation.

## VOICE AND TONE
- Match the tone of the source text
- No hype, no hashtag spam, no calls to action beyond a single soft CTA on \
Instagram captions
- Direct and understated — zero sentimentality
- Never add motivational framing the original text did not have

## OUTPUT FORMAT

Produce the following four content pieces in order:

---

### 1. INSTAGRAM CAPTION

**Source:** Pull the single strongest line from the text as the opening. \
End with one soft CTA.

**Format:**
- Opening line: pulled verbatim from source
- 2-3 sentences: plain, direct, no fluff
- CTA: "Full essay on Substack — link in bio." (always this exact phrasing)
- Hashtags: 2 maximum, only if genuinely relevant. Never generic.

**Length:** 100-150 words maximum

---

### 2. INSTAGRAM CAROUSEL

**Source:** Pull 5-7 of the sharpest, most standalone lines.

**Format:**
- Slide 1: Title slide — source title or a reframed version of it
- Slides 2-6: One pulled line per slide. No added commentary.
- Final slide: "Read the full essay on Substack — link in bio."

**Rules:**
- Every line must be pulled verbatim from the source
- No slide should require the previous slide to make sense
- Prioritise lines that hit hardest out of context

---

### 3. NOTE #1 — Direct Pull

**Source:** The single best aphoristic line from the text.

**Format:**
- One to three sentences maximum
- No context, no setup, no CTA
- It lands and leaves

---

### 4. NOTE #2 — Fresh Observation

**Source:** The text's core idea — but written as a new thought the text \
triggered, not a summary of it.

**Format:**
- One to three sentences maximum
- Aphoristic, understated
- Sounds like something the author thought after finishing writing, not during
- No CTA, no setup, no reference to the source text
- Think: the kind of thing you screenshot and save without knowing why

---

## QUALITY FILTER

Before outputting, check:
- Does every pulled line appear verbatim in the source?
- Is Note #2 genuinely fresh — or just a paraphrase of something already there?
- Is there a single word of hype, filler, or motivational padding anywhere?

Respond only with the four formatted pieces. No preamble. No explanation. \
Just the output.
"""

# ── Backend defaults ──────────────────────────────────────────────────────────

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

CONFIG_PATH = Path.home() / ".config" / "repurpose_agent" / "config.json"


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
    """Return the API key for the given backend, prompting + saving if needed."""
    meta = BACKEND_DEFAULTS[backend]

    # Ollama needs no key
    if meta["env_key"] is None:
        return "ollama"

    # Check env first, then config
    key = os.environ.get(meta["env_key"], "") or cfg.get(meta["config_key"], "")
    if key:
        return key

    # Prompt user
    if meta["key_url"]:
        hint = f"Get one at {meta['key_url']}"
        if HAS_RICH:
            console.print(f"[dim]{hint}[/dim]")
        else:
            print(hint)

    key = _ask(f"{meta['label']} API key", password=True)
    if key and _confirm("Save key to config?"):
        cfg[meta["config_key"]] = key
        save_config(cfg)
    return key

# ── Backend callers ───────────────────────────────────────────────────────────

def _call_anthropic(text: str, system_prompt: str, api_key: str, model: str) -> str:
    try:
        import anthropic
    except ImportError:
        print("Missing: pip install anthropic")
        sys.exit(1)
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model=model,
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": text}],
    )
    return msg.content[0].text


def _call_openai_compat(
    text: str, system_prompt: str, api_key: str, model: str, base_url: str | None
) -> str:
    """Shared caller for OpenAI, Groq, and Ollama — all speak the OpenAI Chat API."""
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
        max_tokens=2048,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
    )
    return resp.choices[0].message.content


def repurpose(
    text: str, system_prompt: str, api_key: str, model: str, backend: str, base_url: str | None = None
) -> str:
    if backend == "anthropic":
        return _call_anthropic(text, system_prompt, api_key, model)
    else:
        resolved_url = base_url or BACKEND_DEFAULTS[backend]["base_url"]
        return _call_openai_compat(text, system_prompt, api_key, model, resolved_url)

# ── I/O helpers ───────────────────────────────────────────────────────────────

def read_input(path: str | None) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    if HAS_RICH:
        console.print(Panel(
            "[dim]Paste your essay below. "
            "Ctrl-D (macOS/Linux) or Ctrl-Z then Enter (Windows) to finish.[/dim]",
            title="[bold]Paste Mode[/bold]",
            border_style="dim",
        ))
    else:
        print("Paste your essay. Ctrl-D (or Ctrl-Z on Windows) when done:\n")
    lines = []
    try:
        while True:
            lines.append(input())
    except EOFError:
        pass
    return "\n".join(lines)


def save_output(output: str, source_path: str | None, output_dir: str | None) -> Path:
    stem = (
        Path(source_path).stem
        if source_path
        else f"repurposed_{datetime.now():%Y%m%d_%H%M%S}"
    )
    out_dir = Path(output_dir) if output_dir else Path.cwd() / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{stem}_repurposed.md"
    out_path.write_text(output, encoding="utf-8")
    return out_path


def display_output(output: str):
    if HAS_RICH:
        console.print(Rule("[bold]Repurposed Content[/bold]"))
        console.print(Markdown(output))
        console.print(Rule())
    else:
        print("\n" + "=" * 60)
        print(output)
        print("=" * 60)

# ── Prompt management ─────────────────────────────────────────────────────────

PROMPTS_DIR = Path.home() / ".config" / "repurpose_agent" / "prompts"


def list_prompts() -> list[str]:
    if not PROMPTS_DIR.exists():
        return []
    return [p.stem for p in PROMPTS_DIR.glob("*.txt")]


def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(
            f"Prompt '{name}' not found. Available: {list_prompts()}"
        )
    return path.read_text(encoding="utf-8")


def save_prompt(name: str, content: str):
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    (PROMPTS_DIR / f"{name}.txt").write_text(content, encoding="utf-8")
    print(f"Saved prompt '{name}'.")

# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="repurpose",
        description="Turn long-form writing into platform-specific content.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
backends:
  anthropic   Claude via Anthropic API       (paid)         default: claude-opus-4-5
  groq        Llama 3.3 via Groq API         (free tier)    default: llama-3.3-70b-versatile
  ollama      Local model via Ollama         (free/offline) default: llama3.2
  openai      OpenAI API                     (paid)         default: gpt-4o-mini

examples:
  repurpose                                    # paste mode, anthropic backend
  repurpose --backend ollama -i essay.txt      # fully offline with Ollama
  repurpose --backend groq -i essay.txt        # free cloud via Groq
  repurpose --backend ollama --model mistral   # specific local model
  repurpose --list-backends                    # show all backend info
  repurpose --set-key groq                     # save a Groq API key
  repurpose --prompt my_brand -i essay.txt     # use a saved custom prompt
        """,
    )
    p.add_argument("-i", "--input", metavar="FILE",
                   help="Input file (default: stdin or paste mode)")
    p.add_argument("-o", "--output-dir", metavar="DIR",
                   help="Directory to save output (default: ./output)")
    p.add_argument("--no-save", action="store_true",
                   help="Print to stdout only, don't save file")
    p.add_argument(
        "--backend",
        choices=list(BACKEND_DEFAULTS.keys()),
        default="anthropic",
        help="AI backend to use (default: anthropic)",
    )
    p.add_argument("--model", metavar="MODEL",
                   help="Model name — overrides the backend default")
    p.add_argument(
        "--ollama-url",
        metavar="URL",
        default=None,
        help="Ollama base URL (default: http://localhost:11434/v1)",
    )
    p.add_argument("--prompt", metavar="NAME",
                   help="Use a saved custom system prompt by name")
    p.add_argument("--prompt-file", metavar="FILE",
                   help="Load system prompt from a file")
    p.add_argument("--save-prompt", metavar="NAME",
                   help="Save the active system prompt under NAME and exit")
    p.add_argument("--list-prompts", action="store_true",
                   help="List saved prompts and exit")
    p.add_argument("--show-prompt", action="store_true",
                   help="Print the active system prompt and exit")
    p.add_argument("--list-backends", action="store_true",
                   help="Show all backends with their defaults and exit")
    p.add_argument("--set-key", metavar="BACKEND",
                   help="Save an API key for a backend (e.g. --set-key groq)")
    return p


def cmd_list_backends():
    cost_label = {
        "anthropic": "paid",
        "groq": "free tier",
        "ollama": "free / offline",
        "openai": "paid",
    }
    if HAS_RICH:
        from rich.table import Table
        t = Table(title="Available Backends", show_lines=True)
        t.add_column("Backend", style="bold cyan")
        t.add_column("Label")
        t.add_column("Default Model")
        t.add_column("Cost")
        t.add_column("Key URL")
        for name, meta in BACKEND_DEFAULTS.items():
            t.add_row(
                name,
                meta["label"],
                meta["model"],
                cost_label[name],
                meta["key_url"] or "n/a",
            )
        console.print(t)
    else:
        for name, meta in BACKEND_DEFAULTS.items():
            print(f"{name:12} {meta['label']:30} default: {meta['model']}")
            if meta["key_url"]:
                print(f"             {meta['key_url']}")


def main():
    parser = build_parser()
    args = parser.parse_args()
    cfg = load_config()

    # ── Utility-only commands ─────────────────────────────────────────────────

    if args.list_backends:
        cmd_list_backends()
        return

    if args.list_prompts:
        prompts = list_prompts()
        print(
            "Saved prompts:\n  " + "\n  ".join(prompts)
            if prompts
            else "No saved prompts yet. Use --save-prompt <name> to create one."
        )
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

    # ── Resolve system prompt ─────────────────────────────────────────────────

    if args.prompt:
        system_prompt = load_prompt(args.prompt)
    elif args.prompt_file:
        system_prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    else:
        system_prompt = DEFAULT_SYSTEM_PROMPT

    if args.save_prompt:
        save_prompt(args.save_prompt, system_prompt)
        return

    if args.show_prompt:
        print(system_prompt)
        return

    # ── Resolve backend + model ───────────────────────────────────────────────

    backend = args.backend
    meta = BACKEND_DEFAULTS[backend]
    model = args.model or meta["model"]

    # Allow --ollama-url to override the Ollama base URL at runtime
    base_url_override = args.ollama_url if backend == "ollama" and args.ollama_url else None

    # ── API key ───────────────────────────────────────────────────────────────

    api_key = get_api_key(cfg, backend)
    if not api_key:
        print("No API key provided. Exiting.")
        sys.exit(1)

    # ── Run ───────────────────────────────────────────────────────────────────

    essay = read_input(args.input)
    if not essay.strip():
        print("No input text. Exiting.")
        sys.exit(1)

    status_msg = f"Repurposing via {meta['label']} ({model})…"
    if HAS_RICH:
        with console.status(f"[bold green]{status_msg}[/bold green]", spinner="dots"):
            output = repurpose(essay, system_prompt, api_key, model, backend, base_url_override)
    else:
        print(status_msg)
        output = repurpose(essay, system_prompt, api_key, model, backend, base_url_override)

    display_output(output)

    if not args.no_save:
        saved_path = save_output(output, args.input, args.output_dir)
        if HAS_RICH:
            console.print(f"\n[dim]Saved → {saved_path}[/dim]")
        else:
            print(f"\nSaved → {saved_path}")


if __name__ == "__main__":
    main()
