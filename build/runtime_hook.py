# PyInstaller runtime hook: pre-import all src modules so deferred
# imports work in the frozen bundle.
import importlib

for mod in [
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
]:
    try:
        importlib.import_module(mod)
    except Exception:
        pass
