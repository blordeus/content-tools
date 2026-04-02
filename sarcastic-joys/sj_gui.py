#!/usr/bin/env python3
"""
Sarcastic Joys — Content Repurposing Desktop App
Warm editorial aesthetic: cream/charcoal, readable, no chrome.
"""

import os
import sys
import json
import threading
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

# ── System prompt (same as CLI) ───────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a content repurposing agent for Sarcastic Joys, a Substack publication \
by Bryan targeting men who feel behind where they thought they'd be in life. \
The core mission is delivering honest, unsentimental writing.

Bryan's voice: warm but firm, direct, understated. Think C.S. Lewis. \
No motivational padding, no sentimentality.

## YOUR ONE RULE
Pull the best lines directly from the essay. Do not paraphrase. Do not improve. \
Do not reimagine. The only exception is Substack Note #2, which is triggered by \
the essay but written fresh.

## OUTPUT FORMAT

### 1. INSTAGRAM CAPTION
- Opening line: pulled verbatim from essay
- 2-3 sentences: plain, direct, no fluff
- CTA: "Full essay on Substack — link in bio."
- Hashtags: 2 maximum, only if genuinely relevant
- 100-150 words maximum

---

### 2. INSTAGRAM CAROUSEL
- Slide 1: Title slide
- Slides 2-6: One pulled line per slide. No commentary.
- Final slide: "Read the full essay on Substack — link in bio."
- Every line verbatim from the essay

---

### 3. SUBSTACK NOTE #1 — Direct Pull
- Single best aphoristic line from the essay
- 1-3 sentences max
- No context, no CTA

---

### 4. SUBSTACK NOTE #2 — Fresh Observation
- Core idea rewritten as a new thought
- 1-3 sentences max
- Aphoristic, no CTA, no reference to the essay

---

Respond only with the four formatted pieces. No preamble. No explanation.
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

def get_api_key(cfg: dict, backend_label: str) -> str:
    meta = BACKENDS[backend_label]
    if meta["env_key"] is None:
        return "ollama"
    return os.environ.get(meta["env_key"], "") or cfg.get(meta["config_key"], "")

def run_repurpose(text: str, api_key: str, backend_label: str, model: str) -> str:
    meta = BACKENDS[backend_label]
    backend = meta["key"]
    base_url = meta["base_url"]

    if backend == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=model, max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": text}],
        )
        return msg.content[0].text
    else:
        from openai import OpenAI
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        client = OpenAI(**kwargs)
        resp = client.chat.completions.create(
            model=model, max_tokens=2048,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )
        return resp.choices[0].message.content

def save_output(text: str) -> Path:
    out_dir = Path.cwd() / "output"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / f"sj_{datetime.now():%Y%m%d_%H%M%S}.md"
    path.write_text(text, encoding="utf-8")
    return path

# ── GUI ───────────────────────────────────────────────────────────────────────

# Warm editorial theme tokens
THEME = THEMES["sarcastic_joys"]

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

class SarcasticJoysApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.title("Sarcastic Joys — Content Repurposing")
        self.geometry("1020x760")
        self.minsize(800, 600)
        self.configure(fg_color=CREAM)
        self.fonts = create_semantic_typography(
            ctk,
            display_family="Georgia",
            title_family="Georgia",
            body_family="Georgia",
            mono_family="Courier",
        )
        self.configure(fg_color=THEME["surface_app"])
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
        ctk.CTkLabel(
            hdr, text="SARCASTIC JOYS",
            font=self.fonts.font_display,
            text_color=CREAM, fg_color="transparent",
        ).place(relx=0.04, rely=0.5, anchor="w")
        ctk.CTkLabel(
            hdr, text="Content Repurposing",
            font=self.fonts.font_body,
            text_color=WARM_GRAY, fg_color="transparent",
            font=ctk.CTkFont(family="Georgia", size=18, weight="bold"),
            text_color=THEME["action_text"], fg_color="transparent",
        ).place(relx=0.04, rely=0.5, anchor="w")
        ctk.CTkLabel(
            hdr, text="Content Repurposing",
            font=ctk.CTkFont(family="Georgia", size=12),
            text_color=THEME["text_muted_on_dark"], fg_color="transparent",
        ).place(relx=0.96, rely=0.5, anchor="e")

        # Settings bar
        bar = ctk.CTkFrame(self, fg_color=THEME["surface_subtle"], corner_radius=0, height=52)
        bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 0))
        bar.grid_propagate(False)
        bar.grid_columnconfigure(4, weight=1)

        ctk.CTkLabel(bar, text="Backend", font=self.fonts.font_small,
                     text_color=WARM_GRAY, fg_color="transparent"
        ctk.CTkLabel(bar, text="Backend", font=ctk.CTkFont(size=11),
                     text_color=THEME["text_muted_on_light"], fg_color="transparent"
                     ).grid(row=0, column=0, padx=(16, 4), pady=14)

        self.backend_var = ctk.StringVar(value="Anthropic (Claude)")
        self.backend_menu = ctk.CTkOptionMenu(
            bar, variable=self.backend_var,
            values=list(BACKENDS.keys()),
            command=self._on_backend_change,
            width=180, height=30,
            fg_color=WHITE, button_color=CHARCOAL_MID,
            button_hover_color=CHARCOAL, text_color=CHARCOAL,
            font=self.fonts.font_body,
        )
        self.backend_menu.grid(row=0, column=1, padx=(0, 16), pady=10)

        ctk.CTkLabel(bar, text="Model", font=self.fonts.font_small,
                     text_color=WARM_GRAY, fg_color="transparent"
            fg_color=THEME["surface_panel"], button_color=THEME["control_text"],
            button_hover_color=THEME["surface_header"], text_color=THEME["text_primary"],
            font=ctk.CTkFont(size=12),
        )
        self.backend_menu.grid(row=0, column=1, padx=(0, 16), pady=10)

        ctk.CTkLabel(bar, text="Model", font=ctk.CTkFont(size=11),
                     text_color=THEME["text_muted_on_light"], fg_color="transparent"
                     ).grid(row=0, column=2, padx=(0, 4), pady=14)

        self.model_var = ctk.StringVar(value="claude-opus-4-5")
        self.model_entry = ctk.CTkEntry(
            bar, textvariable=self.model_var, width=200, height=30,
            fg_color=WHITE, border_color=BORDER, text_color=CHARCOAL,
            font=self.fonts.font_body,
        )
        self.model_entry.grid(row=0, column=3, padx=(0, 16), pady=10)

        ctk.CTkLabel(bar, text="API Key", font=self.fonts.font_small,
                     text_color=WARM_GRAY, fg_color="transparent"
            fg_color=THEME["surface_panel"], border_color=THEME["border"], text_color=THEME["text_primary"],
            font=ctk.CTkFont(size=12),
        )
        self.model_entry.grid(row=0, column=3, padx=(0, 16), pady=10)

        ctk.CTkLabel(bar, text="API Key", font=ctk.CTkFont(size=11),
                     text_color=THEME["text_muted_on_light"], fg_color="transparent"
                     ).grid(row=0, column=5, padx=(0, 4), pady=14)

        self.key_var = ctk.StringVar()
        self.key_entry = ctk.CTkEntry(
            bar, textvariable=self.key_var, width=220, height=30, show="•",
            fg_color=WHITE, border_color=BORDER, text_color=CHARCOAL,
            font=self.fonts.font_body, placeholder_text="paste key here",
            fg_color=THEME["surface_panel"], border_color=THEME["border"], text_color=THEME["text_primary"],
            font=ctk.CTkFont(size=12), placeholder_text="paste key here",
        )
        self.key_entry.grid(row=0, column=6, padx=(0, 8), pady=10)

        self.save_key_btn = ctk.CTkButton(
            bar, text="Save", width=56, height=30,
            fg_color=CHARCOAL_MID, hover_color=CHARCOAL,
            text_color=CREAM, font=self.fonts.font_small,
            fg_color=THEME["control_text"], hover_color=THEME["surface_header"],
            text_color=THEME["action_text"], font=ctk.CTkFont(size=11),
            command=self._save_key,
        )
        self.save_key_btn.grid(row=0, column=7, padx=(0, 16), pady=10)

        # Left panel — input
        left = ctk.CTkFrame(self, fg_color=THEME["surface_app"], corner_radius=0)
        left.grid(row=2, column=0, sticky="nsew", padx=(16, 8), pady=16)
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            left, text="Essay",
            font=self.fonts.font_section,
            text_color=CHARCOAL, fg_color="transparent", anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.input_box = ctk.CTkTextbox(
            left, font=self.fonts.font_body,
            fg_color=WHITE, border_color=BORDER, border_width=1,
            text_color=CHARCOAL, wrap="word",
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=WARM_GRAY,
            font=ctk.CTkFont(family="Georgia", size=13, weight="bold"),
            text_color=THEME["text_primary"], fg_color="transparent", anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.input_box = ctk.CTkTextbox(
            left, font=ctk.CTkFont(family="Georgia", size=13),
            fg_color=THEME["surface_panel"], border_color=THEME["border"], border_width=1,
            text_color=THEME["text_primary"], wrap="word",
            scrollbar_button_color=THEME["border"],
            scrollbar_button_hover_color=THEME["text_muted_on_light"],
        )
        self.input_box.grid(row=1, column=0, sticky="nsew")

        self.run_btn = ctk.CTkButton(
            left, text="Repurpose →", height=40,
            fg_color=RUST, hover_color=RUST_HOVER, text_color=WHITE,
            font=self.fonts.font_title,
            fg_color=THEME["action_bg"], hover_color=THEME["action_bg_hover"], text_color=THEME["action_text"],
            font=ctk.CTkFont(family="Georgia", size=14, weight="bold"),
            command=self._on_run, corner_radius=4,
        )
        self.run_btn.grid(row=2, column=0, sticky="ew", pady=(12, 0))

        # Right panel — output
        right = ctk.CTkFrame(self, fg_color=THEME["surface_app"], corner_radius=0)
        right.grid(row=2, column=1, sticky="nsew", padx=(8, 16), pady=16)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        out_hdr = ctk.CTkFrame(right, fg_color="transparent")
        out_hdr.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        out_hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            out_hdr, text="Output",
            font=self.fonts.font_section,
            text_color=CHARCOAL, fg_color="transparent", anchor="w",
            font=ctk.CTkFont(family="Georgia", size=13, weight="bold"),
            text_color=THEME["text_primary"], fg_color="transparent", anchor="w",
        ).grid(row=0, column=0, sticky="w")

        self.copy_btn = ctk.CTkButton(
            out_hdr, text="Copy all", width=80, height=28,
            fg_color=THEME["surface_subtle"], hover_color=THEME["control_bg_hover"],
            text_color=THEME["control_text"], border_color=THEME["border"], border_width=1,
            font=ctk.CTkFont(size=11), command=self._copy_output,
        )
        self.copy_btn.grid(row=0, column=1, padx=(8, 0))

        self.save_btn = ctk.CTkButton(
            out_hdr, text="Save .md", width=80, height=28,
            fg_color=CREAM_DARK, hover_color=BORDER,
            text_color=CHARCOAL_MID, border_color=BORDER, border_width=1,
            font=self.fonts.font_small, command=self._save_output,
            fg_color=THEME["surface_subtle"], hover_color=THEME["control_bg_hover"],
            text_color=THEME["control_text"], border_color=THEME["border"], border_width=1,
            font=ctk.CTkFont(size=11), command=self._save_output,
        )
        self.save_btn.grid(row=0, column=2, padx=(6, 0))

        self.output_box = ctk.CTkTextbox(
            right, font=self.fonts.font_body,
            fg_color=WHITE, border_color=BORDER, border_width=1,
            text_color=CHARCOAL, wrap="word",
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=WARM_GRAY,
            right, font=ctk.CTkFont(family="Georgia", size=13),
            fg_color=THEME["surface_panel"], border_color=THEME["border"], border_width=1,
            text_color=THEME["text_primary"], wrap="word",
            scrollbar_button_color=THEME["border"],
            scrollbar_button_hover_color=THEME["text_muted_on_light"],
            state="disabled",
        )
        self.output_box.grid(row=1, column=0, sticky="nsew")

        # Status bar
        self.status_var = ctk.StringVar(value="  Ready")
        self.status_bar = ctk.CTkLabel(
            self, textvariable=self.status_var,
            font=self.fonts.font_small, text_color=WARM_GRAY,
            fg_color=CREAM_DARK, anchor="w", corner_radius=0, height=28,
            font=ctk.CTkFont(size=11), text_color=THEME["text_muted_on_light"],
            fg_color=THEME["surface_subtle"], anchor="w", corner_radius=0, height=28,
        )
        self.status_bar.grid(row=3, column=0, columnspan=2, sticky="ew")

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
        essay = self.input_box.get("1.0", "end").strip()
        if not essay:
            self._set_status("Paste an essay first.")
            return

        backend_label = self.backend_var.get()
        model = self.model_var.get().strip()
        api_key = self.key_var.get().strip() or get_api_key(self.cfg, backend_label)

        if not api_key and BACKENDS[backend_label]["env_key"] is not None:
            self._set_status("No API key. Enter one in the bar above.")
            return

        self.run_btn.configure(state="disabled", text="Working…")
        self._set_status(f"Running via {backend_label} ({model})…")
        self._set_output("")

        def worker():
            try:
                result = run_repurpose(essay, api_key, backend_label, model)
                self.after(0, lambda: self._on_done(result))
            except Exception as e:
                self.after(0, lambda: self._on_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_done(self, result: str):
        self._set_output(result)
        self.run_btn.configure(state="normal", text="Repurpose →")
        self._set_status("Done.")

    def _on_error(self, msg: str):
        self._set_output(f"Error:\n\n{msg}")
        self.run_btn.configure(state="normal", text="Repurpose →")
        self._set_status(f"Error: {msg[:80]}")


if __name__ == "__main__":
    app = SarcasticJoysApp()
    app.mainloop()
