"""Shared semantic typography helpers for CustomTkinter apps."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SemanticTypography:
    font_display: object
    font_title: object
    font_section: object
    font_body: object
    font_small: object
    font_mono: object


def create_semantic_typography(
    ctk,
    *,
    display_family: str,
    title_family: str | None = None,
    body_family: str | None = None,
    mono_family: str = "Courier",
) -> SemanticTypography:
    """Return a consistent semantic typography object used across app UIs."""
    title_family = title_family or display_family
    body_family = body_family or title_family

    return SemanticTypography(
        font_display=ctk.CTkFont(family=display_family, size=18, weight="bold"),
        font_title=ctk.CTkFont(family=title_family, size=14, weight="bold"),
        font_section=ctk.CTkFont(family=title_family, size=13, weight="bold"),
        font_body=ctk.CTkFont(family=body_family, size=12),
        font_small=ctk.CTkFont(family=body_family, size=11),
        font_mono=ctk.CTkFont(family=mono_family, size=12),
    )
