# PyInstaller runtime hook: pre-import all src modules so frozen bundles
# fail fast if a critical module was omitted from the archive.
import importlib

CRITICAL_MODULES = [
    "src.core.constants",
    "src.core.auth",
    "src.core.api",
    "src.core.drm",
    "src.core.downloader",
    "src.core.url_parser",
    "src.services.config",
    "src.services.binary_locator",
    "src.services.download_manager",
    "src.services.updater",
    "src.ui.theme",
    "src.ui.i18n",
    "src.app",
]

failures = []
for mod in CRITICAL_MODULES:
    try:
        importlib.import_module(mod)
    except Exception as exc:
        failures.append(f"{mod}: {exc.__class__.__name__}: {exc}")

if failures:
    raise RuntimeError(
        "Frozen bundle is missing or cannot import required modules:\n"
        + "\n".join(failures)
    )
