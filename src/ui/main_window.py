import tkinter as tk

import customtkinter as ctk

from . import theme as T
from .login_frame import LoginFrame
from .download_frame import DownloadFrame
from .settings_frame import SettingsFrame
from ..core.constants import __version__


class MainWindow(ctk.CTk):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.i = app.i18n

        self.title(f"{self.i.t('app_title')} v{__version__}")
        self.geometry(f"{T.WINDOW_WIDTH}x{T.WINDOW_HEIGHT}")
        self.minsize(700, 500)
        self.configure(fg_color=T.BG)

        try:
            from pathlib import Path
            import sys
            if getattr(sys, "frozen", False):
                ico = Path(sys._MEIPASS) / "assets" / "icon.ico"
            else:
                ico = Path(__file__).parent.parent / "assets" / "icon.ico"
            if ico.exists():
                self.iconbitmap(str(ico))
        except Exception:
            pass

        # Outer plain tk frame — avoids CTkFrame canvas rendering issues
        self.outer = tk.Frame(self, bg=T.BG)
        self.outer.pack(fill="both", expand=True)

        self._build_header()

        self.container = tk.Frame(self.outer, bg=T.BG)
        self.container.pack(fill="both", expand=True)

        self.frames: dict[str, tk.Frame] = {}
        self.frames["login"] = LoginFrame(self.container, app)
        self.frames["download"] = DownloadFrame(self.container, app)
        self.frames["settings"] = SettingsFrame(self.container, app)

        self._current_frame: str | None = None

    def _build_header(self):
        if hasattr(self, "header") and self.header.winfo_exists():
            self.header.destroy()

        i = self.i
        start = i.start
        end = i.end

        self.header = tk.Frame(self.outer, bg=T.BG_SECONDARY, height=44)
        self.header.pack(fill="x", side="top")
        self.header.pack_propagate(False)

        tk.Label(
            self.header, text=f"  {i.t('app_title')}",
            font=(T.FONT_FAMILY, 14, "bold"), fg=T.ACCENT, bg=T.BG_SECONDARY,
        ).pack(side=start, padx=4)

        tk.Label(
            self.header, text=f"v{__version__}",
            font=T.FONT_SM, fg=T.TEXT_DIM, bg=T.BG_SECONDARY,
        ).pack(side=start, padx=(2, 0))

        self.settings_btn = ctk.CTkButton(
            self.header, text=i.t("settings"), width=80, height=28, font=T.FONT_SM,
            fg_color=T.BG_CARD, hover_color=T.BORDER, text_color=T.TEXT_DIM,
            command=lambda: self.app.show_frame("settings"),
        )

    def rebuild_all(self):
        self.i = self.app.i18n
        self.title(f"{self.i.t('app_title')} v{__version__}")

        current = self._current_frame
        if current and current in self.frames:
            self.frames[current].pack_forget()

        self._build_header()
        self.container.pack_forget()
        self.container.pack(fill="both", expand=True)

        for frame in self.frames.values():
            if hasattr(frame, "rebuild"):
                frame.rebuild()

        self._current_frame = None
        if current:
            self.show_frame(current)

    def show_frame(self, name: str):
        if self._current_frame == name:
            return
        if self._current_frame and self._current_frame in self.frames:
            self.frames[self._current_frame].pack_forget()
        self.frames[name].pack(fill="both", expand=True)
        self._current_frame = name

        # Settings button: hide on login, show otherwise
        self.settings_btn.pack_forget()
        if name != "login":
            self.settings_btn.pack(side=self.i.end, padx=10, pady=8)
