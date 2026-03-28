#!/usr/bin/env python3
"""SeenShow Downloader — entry point."""

import logging
import multiprocessing
import sys
import traceback
from pathlib import Path


def setup_logging():
    """Set up file logging in %APPDATA%/SeenShowDL/logs/."""
    from src.services.config import APP_DATA_DIR
    log_dir = APP_DATA_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "seenshow.log"

    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Also log to stderr if console is available
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    logging.getLogger().addHandler(console)

    return log_file


def main():
    multiprocessing.freeze_support()

    log_file = setup_logging()
    logger = logging.getLogger("seenshow")
    logger.info("Starting SeenShow Downloader")

    try:
        from src.services.updater import cleanup_old_exe
        cleanup_old_exe()

        from src.app import App
        app = App()
        app.run()
    except Exception:
        error = traceback.format_exc()
        logger.critical(f"Fatal error:\n{error}")

        # Show error dialog if possible
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "SeenShow Downloader — Error",
                f"An unexpected error occurred.\n\n{error}\n\nLog file: {log_file}",
            )
            root.destroy()
        except Exception:
            print(f"FATAL: {error}", file=sys.stderr)

        sys.exit(1)


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    main()
