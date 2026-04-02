"""Centralized color tokens for both desktop apps.

Each token includes intended usage to avoid low-contrast combinations.
"""

THEMES = {
    "sarcastic_joys": {
        # App shell backgrounds (light mode surfaces).
        "surface_app": "#F5F0E8",
        "surface_subtle": "#EDE8DC",
        "surface_panel": "#FFFFFF",

        # Header band uses a dark surface.
        "surface_header": "#2C2C2C",

        # Primary text for light surfaces and text inputs.
        "text_primary": "#2C2C2C",

        # Muted text only on light surfaces (settings/status labels).
        "text_muted_on_light": "#5F584E",

        # Muted text only on dark surfaces (header subtitle/metadata).
        "text_muted_on_dark": "#D6CEC2",

        # Header title text only on dark header background.
        "text_header": "#F5F0E8",

        # Accent button background + hover; keep white button text.
        "action_bg": "#B85C38",
        "action_bg_hover": "#9B4A2E",
        "action_text": "#FFFFFF",

        # Neutral control colors for outlined/secondary buttons.
        "control_bg": "#EDE8DC",
        "control_bg_hover": "#D4CEC4",
        "control_text": "#444444",

        # Borders and scrollbar accents on light surfaces.
        "border": "#D4CEC4",
    },

    "elite_executive": {
        # App shell backgrounds (dark mode surfaces).
        "surface_app": "#1A1F2E",
        "surface_header": "#252B3B",
        "surface_subtle": "#2E3547",

        # Input/text panel background in dark mode.
        "surface_panel": "#252B3B",

        # Primary text for body copy on dark surfaces.
        "text_primary": "#E2DDD4",

        # Muted text only on dark surfaces (helper labels/status/meta).
        "text_muted_on_dark": "#A7B1C2",

        # Placeholder text only inside input fields on dark surfaces.
        "text_placeholder": "#8F98AB",

        # Brand/accent text in header and CTA button colors.
        "text_accent": "#C9A84C",
        "action_bg": "#C9A84C",
        "action_bg_hover": "#B08A2A",

        # Dark text only on gold accent backgrounds.
        "action_text": "#1A1F2E",

        # Neutral controls and borders in dark UI.
        "control_bg": "#2E3547",
        "control_bg_hover": "#3A4055",
        "control_text": "#C2CBD9",
        "border": "#3A4055",
    },
}
