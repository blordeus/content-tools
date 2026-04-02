#!/usr/bin/env python3
"""
Elite Executive — Substack Notes Generator Desktop App
Sharp executive aesthetic: deep slate, gold accent, minimal chrome.
"""

import os
import sys
import json
import threading
import urllib.request
import urllib.error
from html.parser import HTMLParser
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from shared_theme import create_semantic_typography

try:
    import customtkinter as ctk
except ImportError:
    print("Missing: pip install customtkinter")
    sys.exit(1)

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

---

## OUTPUT FORMAT

### NOTE A — Click-Driver

[note text]

---

### NOTE B — Standalone Insight

[note text]

---

Respond only with the two formatted notes. No preamble. No explanation.
"""

# ── Backend config ────────────────────────────────────────────────────────────

BACKENDS = {
    "Anthropic (Claude)": {
        "key": "anthropic", "model": "claude-opus-4-5",
        "env_key": "ANTHROPIC_API_KEY", "config_key": "anthropic_api_key",
        "base_url": None,
    },
    "Groq (free)": {
        "key": "groq", "model": "llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY", "config_key": "groq_api_key",
        "base_url": "https://api.groq.com/openai/v1",
    },
    "Ollama (offline)": {
        "key": "ollama", "model": "llama3.2",
        "env_key": None, "config_key": None,
        "base_url": "http://localhost:11434/v1",
    },
    "OpenAI": {
        "key": "openai", "model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY", "config_key": "openai_api_key",
        "base_url": None,
    },
}

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

def get_api_key(cfg: dict, backend_label: str) -> str:
    meta = BACKENDS[backend_label]
    if meta["env_key"] is None:
        return "ollama"
    return os.environ.get(meta["env_key"], "") or cfg.get(meta["config_key"], "")

# ── HTML stripper ─────────────────────────────────────────────────────────────

class _TextExtractor(HTMLParser):
    SKIP_TAGS = {"script", "style", "nav", "header", "footer", "noscript", "svg"}
    BLOCK_TAGS = {"p","h1","h2","h3","h4","h5","h6","li","blockquote","div","section","article"}

    def __init__(self):
        super().__init__()
        self.chunks: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self._skip += 1
        if tag in self.BLOCK_TAGS and self.chunks and self.chunks[-1] != "\n\n":
            self.chunks.append("\n\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data):
        if not self._skip:
            t = data.strip()
            if t:
                self.chunks.append(t + " ")

    def get_text(self) -> str:
        import re
        text = "".join(self.chunks)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return re.sub(r" {2,}", " ", text).strip()

def fetch_url(url: str, timeout: int = 15) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            charset = r.headers.get_content_charset() or "utf-8"
            html = r.read().decode(charset, errors="replace")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach URL: {e.reason}") from e
    p = _TextExtractor()
    p.feed(html)
    text = p.get_text()
    words = text.split()
    return " ".join(words[:6000]) + ("\n\n[truncated]" if len(words) > 6000 else "")

# ── LLM caller ────────────────────────────────────────────────────────────────

def generate_notes(text: str, url: str, api_key: str, backend_label: str, model: str) -> str:
    meta = BACKENDS[backend_label]
    backend = meta["key"]
    base_url = meta["base_url"]
    prompt = f"Newsletter URL: {url}\n\n---\n\n{text}"

    if backend == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=model, max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text
    else:
        from openai import OpenAI
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        client = OpenAI(**kwargs)
        resp = client.chat.completions.create(
            model=model, max_tokens=1024,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content

def save_output(text: str) -> Path:
    out_dir = Path.cwd() / "output"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / f"ee_{datetime.now():%Y%m%d_%H%M%S}.md"
    path.write_text(text, encoding="utf-8")
    return path

# ── Palette ───────────────────────────────────────────────────────────────────

THEME = THEMES["elite_executive"]

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class EliteExecApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.title("Elite Executive — Substack Notes")
        self.geometry("1100x780")
        self.minsize(860, 620)
        self.configure(fg_color=SLATE)
        self.fonts = create_semantic_typography(
            ctk,
            display_family="Helvetica",
            title_family="Helvetica",
            body_family="Helvetica",
            mono_family="Courier",
        )
        self._build_ui()
        self._load_saved_key()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Header
        hdr = ctk.CTkFrame(self, fg_color=THEME["surface_header"], corner_radius=0, height=64)
        hdr.grid(row=0, column=0, columnspan=2, sticky="ew")
        hdr.grid_propagate(False)

        title_frame = ctk.CTkFrame(hdr, fg_color="transparent")
        title_frame.place(relx=0.04, rely=0.5, anchor="w")
        ctk.CTkLabel(
            title_frame, text="ELITE EXECUTIVE",
            font=ctk.CTkFont(family="Helvetica", size=16, weight="bold"),
            text_color=THEME["text_accent"], fg_color="transparent",
        ).pack(side="left")
        ctk.CTkLabel(
            title_frame, text="  ·  Substack Notes",
            font=ctk.CTkFont(family="Helvetica", size=12),
            text_color=THEME["text_muted_on_dark"], fg_color="transparent",
        ).pack(side="left")

        # Settings bar
        bar = ctk.CTkFrame(self, fg_color=THEME["surface_subtle"], corner_radius=0, height=52)
        bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(4, weight=1)

        def lbl(parent, text):
            return ctk.CTkLabel(parent, text=text, font=self.fonts.font_small,
                                text_color=TEXT_DIM, fg_color="transparent")

        lbl(bar, "Backend").grid(row=0, column=0, padx=(16, 4), pady=12)
        self.backend_var = ctk.StringVar(value="Anthropic (Claude)")
        ctk.CTkOptionMenu(
            bar, variable=self.backend_var, values=list(BACKENDS.keys()),
            command=self._on_backend_change,
            width=190, height=30,
            fg_color=SLATE_MID, button_color=GOLD, button_hover_color=GOLD_HOVER,
            text_color=TEXT_MAIN, font=self.fonts.font_body,
            dropdown_fg_color=SLATE_MID, dropdown_text_color=TEXT_MAIN,
            dropdown_hover_color=SLATE_LIGHT,
        ).grid(row=0, column=1, padx=(0, 16), pady=10)

        lbl(bar, "Model").grid(row=0, column=2, padx=(0, 4))
        self.model_var = ctk.StringVar(value="claude-opus-4-5")
        ctk.CTkEntry(
            bar, textvariable=self.model_var, width=200, height=30,
            fg_color=SLATE_MID, border_color=BORDER, text_color=TEXT_MAIN,
            font=self.fonts.font_body,
        ).grid(row=0, column=3, padx=(0, 16), pady=10)

        lbl(bar, "API Key").grid(row=0, column=5, padx=(0, 4))
        self.key_var = ctk.StringVar()
        ctk.CTkEntry(
            bar, textvariable=self.key_var, width=230, height=30, show="•",
            fg_color=SLATE_MID, border_color=BORDER, text_color=TEXT_MAIN,
            font=self.fonts.font_body, placeholder_text="paste key here",
            placeholder_text_color=MUTED,
        ).grid(row=0, column=6, padx=(0, 8), pady=10)

        ctk.CTkButton(
            bar, text="Save", width=56, height=30,
            fg_color=SLATE_MID, hover_color=BORDER, border_color=BORDER, border_width=1,
            text_color=TEXT_DIM, font=self.fonts.font_small,
            command=self._save_key,
        ).grid(row=0, column=7, padx=(0, 16), pady=10)

        # Left — URL input
        left = ctk.CTkFrame(self, fg_color=THEME["surface_app"], corner_radius=0)
        left.grid(row=2, column=0, sticky="nsew", padx=(16, 8), pady=16)
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        top_left = ctk.CTkFrame(left, fg_color="transparent")
        top_left.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        top_left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top_left, text="Newsletter URLs",
            font=self.fonts.font_section,
            text_color=OFF_WHITE, fg_color="transparent", anchor="w",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            top_left, text="one per line",
            font=self.fonts.font_small, text_color=TEXT_DIM,
            font=ctk.CTkFont(family="Helvetica", size=13, weight="bold"),
            text_color=THEME["text_primary"], fg_color="transparent", anchor="w",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            top_left, text="one per line",
            font=ctk.CTkFont(size=11), text_color=THEME["text_muted_on_dark"],
            fg_color="transparent",
        ).grid(row=0, column=1, sticky="e")

        self.url_box = ctk.CTkTextbox(
            left, font=self.fonts.font_mono,
            fg_color=SLATE_MID, border_color=BORDER, border_width=1,
            text_color=TEXT_MAIN, wrap="none",
            scrollbar_button_color=BORDER, scrollbar_button_hover_color=SLATE_LIGHT,
            left, font=ctk.CTkFont(family="Courier", size=12),
            fg_color=THEME["surface_header"], border_color=THEME["border"], border_width=1,
            text_color=THEME["text_primary"], wrap="none",
            scrollbar_button_color=THEME["border"], scrollbar_button_hover_color=THEME["surface_subtle"],
        )
        self.url_box.grid(row=1, column=0, sticky="nsew")

        self.run_btn = ctk.CTkButton(
            left, text="Generate Notes →", height=42,
            fg_color=GOLD, hover_color=GOLD_HOVER, text_color=SLATE,
            font=self.fonts.font_title,
            fg_color=THEME["action_bg"], hover_color=THEME["action_bg_hover"], text_color=THEME["action_text"],
            font=ctk.CTkFont(family="Helvetica", size=14, weight="bold"),
            command=self._on_run, corner_radius=3,
        )
        self.run_btn.grid(row=2, column=0, sticky="ew", pady=(12, 0))

        # Right — output
        right = ctk.CTkFrame(self, fg_color=THEME["surface_app"], corner_radius=0)
        right.grid(row=2, column=1, sticky="nsew", padx=(8, 16), pady=16)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        top_right = ctk.CTkFrame(right, fg_color="transparent")
        top_right.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        top_right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top_right, text="Generated Notes",
            font=self.fonts.font_section,
            text_color=OFF_WHITE, fg_color="transparent", anchor="w",
            font=ctk.CTkFont(family="Helvetica", size=13, weight="bold"),
            text_color=THEME["text_primary"], fg_color="transparent", anchor="w",
        ).grid(row=0, column=0, sticky="w")

        for col, (label, cmd) in enumerate([
            ("Copy", self._copy_output),
            ("Save .md", self._save_output),
        ], start=1):
            ctk.CTkButton(
                top_right, text=label, width=76, height=28,
                fg_color=SLATE_LIGHT, hover_color=BORDER,
                border_color=BORDER, border_width=1,
                text_color=TEXT_DIM, font=self.fonts.font_small,
                fg_color=THEME["surface_subtle"], hover_color=THEME["control_bg_hover"],
                border_color=THEME["border"], border_width=1,
                text_color=THEME["text_muted_on_dark"], font=ctk.CTkFont(size=11),
                command=cmd,
            ).grid(row=0, column=col, padx=(6, 0))

        self.output_box = ctk.CTkTextbox(
            right, font=ctk.CTkFont(family="Helvetica", size=13),
            fg_color=THEME["surface_header"], border_color=THEME["border"], border_width=1,
            text_color=THEME["text_primary"], wrap="word",
            scrollbar_button_color=THEME["border"], scrollbar_button_hover_color=THEME["surface_subtle"],
            state="disabled",
        )
        self.output_box.grid(row=1, column=0, sticky="nsew")

        # Status bar
        self.status_var = ctk.StringVar(value="Ready")
        ctk.CTkLabel(
            self, textvariable=self.status_var,
            font=self.fonts.font_small, text_color=TEXT_DIM,
            fg_color=SLATE_MID, anchor="w", corner_radius=0, height=28,
            font=ctk.CTkFont(size=11), text_color=THEME["text_muted_on_dark"],
            fg_color=THEME["surface_header"], anchor="w", corner_radius=0, height=28,
        ).grid(row=3, column=0, columnspan=2, sticky="ew")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _on_backend_change(self, label: str):
        self.model_var.set(BACKENDS[label]["model"])
        self._load_saved_key()

    def _load_saved_key(self):
        key = get_api_key(self.cfg, self.backend_var.get())
        if key and key != "ollama":
            self.key_var.set(key)

    def _save_key(self):
        meta = BACKENDS[self.backend_var.get()]
        if meta["config_key"] is None:
            self._set_status("Ollama doesn't use an API key.")
            return
        key = self.key_var.get().strip()
        if not key:
            self._set_status("No key entered.")
            return
        self.cfg[meta["config_key"]] = key
        save_config(self.cfg)
        self._set_status("API key saved.")

    def _set_status(self, msg: str):
        self.status_var.set(f"  {msg}")

    def _set_output(self, text: str):
        self.output_box.configure(state="normal")
        self.output_box.delete("1.0", "end")
        self.output_box.insert("1.0", text)
        self.output_box.configure(state="disabled")

    def _append_output(self, text: str):
        self.output_box.configure(state="normal")
        self.output_box.insert("end", text)
        self.output_box.configure(state="disabled")
        self.output_box.see("end")

    def _get_output(self) -> str:
        self.output_box.configure(state="normal")
        t = self.output_box.get("1.0", "end").strip()
        self.output_box.configure(state="disabled")
        return t

    def _copy_output(self):
        text = self._get_output()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._set_status("Copied to clipboard.")

    def _save_output(self):
        text = self._get_output()
        if not text:
            self._set_status("Nothing to save.")
            return
        path = save_output(text)
        self._set_status(f"Saved → {path}")

    # ── Run ───────────────────────────────────────────────────────────────────

    def _on_run(self):
        raw = self.url_box.get("1.0", "end")
        urls = [u.strip() for u in raw.splitlines() if u.strip() and not u.startswith("#")]
        if not urls:
            self._set_status("Paste at least one URL.")
            return

        backend_label = self.backend_var.get()
        model = self.model_var.get().strip()
        api_key = self.key_var.get().strip() or get_api_key(self.cfg, backend_label)

        if not api_key and BACKENDS[backend_label]["env_key"] is not None:
            self._set_status("No API key. Enter one in the bar above.")
            return

        self.run_btn.configure(state="disabled", text="Working…")
        self._set_output("")
        self._set_status(f"Processing {len(urls)} URL(s)…")

        def worker():
            all_output: list[str] = []
            for i, url in enumerate(urls, 1):
                self.after(0, lambda u=url, n=i: self._set_status(
                    f"[{n}/{len(urls)}] Fetching {u[:60]}…"
                ))
                try:
                    text = fetch_url(url)
                except RuntimeError as e:
                    entry = f"## Newsletter {i}\n**URL:** {url}\n**Error:** {e}\n\n---\n\n"
                    all_output.append(entry)
                    self.after(0, lambda e=entry: self._append_output(e))
                    continue

                self.after(0, lambda n=i: self._set_status(
                    f"[{n}/{len(urls)}] Generating notes…"
                ))
                try:
                    notes = generate_notes(text, url, api_key, backend_label, model)
                except Exception as e:
                    notes = f"Error generating notes: {e}"

                entry = f"## Newsletter {i}\n**URL:** {url}\n\n{notes}\n\n---\n\n"
                all_output.append(entry)
                self.after(0, lambda e=entry: self._append_output(e))

            self.after(0, lambda: self._on_done(len(urls)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_done(self, count: int):
        self.run_btn.configure(state="normal", text="Generate Notes →")
        self._set_status(f"Done — {count} newsletter(s) processed.")


if __name__ == "__main__":
    app = EliteExecApp()
    app.mainloop()
