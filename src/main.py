#!/usr/bin/env python3
"""SeenShow Downloader — entry point."""

import multiprocessing
import sys
from pathlib import Path


def main():
    multiprocessing.freeze_support()

    # Cleanup old exe from self-update
    from src.services.updater import cleanup_old_exe
    cleanup_old_exe()

    from src.app import App
    app = App()
    app.run()


if __name__ == "__main__":
    # When running from source, ensure the project root is on sys.path
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    main()
