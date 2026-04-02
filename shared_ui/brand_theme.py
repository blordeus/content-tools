"""Shared brand theme tokens and UI font helpers for desktop apps."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

APPEARANCE_MODES = {
    "sarcastic_joys": "light",
    "elite_executive": "dark",
}

COLOR_TOKENS = {
    "primary": "#2C2C2C",
    "secondary": "#444444",
    "accent": "#B85C38",
    "accent_hover": "#A04F30",
    "surface": "#F5F0E8",
    "surface_alt": "#EDE8DC",
    "surface_input": "#FFFFFF",
    "border": "#D4CEC4",
    "text_primary": "#2C2C2C",
    "text_muted": "#8A8378",
    "text_inverse": "#FFFFFF",
    "hover_subtle": "#D4CEC4",
    "placeholder": "#8A8378",
}

FONT_TOKENS = {
    "heading": {"family": "Georgia", "size": 18, "weight": "bold"},
    "subheading": {"family": "Georgia", "size": 13, "weight": "bold"},
    "body": {"family": "Georgia", "size": 13},
    "mono": {"family": "Courier", "size": 12},
    "caption": {"family": "Georgia", "size": 11},
}

BRAND_OVERRIDES = {
    "sarcastic_joys": {
        "colors": {},
        "fonts": {},
    },
    "elite_executive": {
        "colors": {
            "primary": "#1A1F2E",
            "secondary": "#252B3B",
            "accent": "#C9A84C",
            "accent_hover": "#B8962E",
            "surface": "#1A1F2E",
            "surface_alt": "#2E3547",
            "surface_input": "#252B3B",
            "border": "#3A4055",
            "text_primary": "#E2DDD4",
            "text_muted": "#8892A4",
            "text_inverse": "#1A1F2E",
            "hover_subtle": "#2E3547",
            "placeholder": "#6B7280",
        },
        "fonts": {
            "heading": {"family": "Helvetica", "size": 16, "weight": "bold"},
            "subheading": {"family": "Helvetica", "size": 13, "weight": "bold"},
            "body": {"family": "Helvetica", "size": 13},
            "caption": {"family": "Helvetica", "size": 11},
        },
    },
}


def build_brand_theme(brand: str) -> dict[str, Any]:
    if brand not in BRAND_OVERRIDES:
        raise ValueError(f"Unknown brand '{brand}'.")

    colors = deepcopy(COLOR_TOKENS)
    fonts = deepcopy(FONT_TOKENS)

    colors.update(BRAND_OVERRIDES[brand]["colors"])
    for token, settings in BRAND_OVERRIDES[brand]["fonts"].items():
        merged = deepcopy(fonts.get(token, {}))
        merged.update(settings)
        fonts[token] = merged

    return {
        "appearance_mode": APPEARANCE_MODES[brand],
        "colors": colors,
        "fonts": fonts,
    }


def themed_font(ctk_module, theme: dict[str, Any], token: str, **overrides):
    settings = deepcopy(theme["fonts"][token])
    settings.update(overrides)
    return ctk_module.CTkFont(**settings)


def heading_font(ctk_module, theme: dict[str, Any], **overrides):
    return themed_font(ctk_module, theme, "heading", **overrides)


def subheading_font(ctk_module, theme: dict[str, Any], **overrides):
    return themed_font(ctk_module, theme, "subheading", **overrides)


def body_font(ctk_module, theme: dict[str, Any], **overrides):
    return themed_font(ctk_module, theme, "body", **overrides)


def mono_font(ctk_module, theme: dict[str, Any], **overrides):
    return themed_font(ctk_module, theme, "mono", **overrides)


def caption_font(ctk_module, theme: dict[str, Any], **overrides):
    return themed_font(ctk_module, theme, "caption", **overrides)


__all__ = [
    "APPEARANCE_MODES",
    "COLOR_TOKENS",
    "FONT_TOKENS",
    "BRAND_OVERRIDES",
    "build_brand_theme",
    "themed_font",
    "heading_font",
    "subheading_font",
    "body_font",
    "mono_font",
    "caption_font",
]
