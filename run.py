#!/usr/bin/env python3
"""Launch the app from source (for development/testing)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.app import App

if __name__ == "__main__":
    app = App()
    app.run()
