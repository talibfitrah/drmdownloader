"""Shared colors and style constants."""

import sys

BG = "#1a1a2e"
BG_SECONDARY = "#16213e"
BG_CARD = "#1f2b47"
BG_INPUT = "#0f3460"
ACCENT = "#e94560"
ACCENT_HOVER = "#c73e54"
TEXT = "#f0f0f0"
TEXT_DIM = "#8899aa"
TEXT_SUCCESS = "#4ade80"
TEXT_ERROR = "#f87171"
TEXT_WARNING = "#fbbf24"
BORDER = "#2a3a5c"

if sys.platform == "darwin":
    FONT_FAMILY = "SF Pro"
elif sys.platform == "win32":
    FONT_FAMILY = "Segoe UI"
else:
    FONT_FAMILY = "DejaVu Sans"
FONT_SM = (FONT_FAMILY, 11)
FONT_MD = (FONT_FAMILY, 13)
FONT_LG = (FONT_FAMILY, 16, "bold")
FONT_XL = (FONT_FAMILY, 20, "bold")

WINDOW_WIDTH = 860
WINDOW_HEIGHT = 620
