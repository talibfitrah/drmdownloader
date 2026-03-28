"""Application controller — glues UI, config, and core logic together."""

import customtkinter as ctk

from .core.api import SeenAPI
from .services.config import Config
from .ui.i18n import I18n
from .ui.main_window import MainWindow


class App:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.config = Config()
        self.access_token: str | None = None
        self._api: SeenAPI | None = None
        self._current_user_email: str | None = None

        saved_lang = self.config.get("language", "en")
        self.i18n = I18n(saved_lang)

        self.window = MainWindow(self)

        user, pw = self.config.get_credentials()
        if user and pw:
            self.window.frames["login"].prefill(user, pw, True)

        self.show_frame("login")

    def show_frame(self, name: str):
        self.window.show_frame(name)
        if name == "settings":
            display_email = self._current_user_email
            if not display_email:
                display_email, _ = self.config.get_credentials()
            sf = self.window.frames["settings"]
            sf.account_label.configure(
                text=display_email or self.i18n.t("not_signed_in"),
            )
            sf.output_var.set(self.config.get("output_dir", ""))

    def set_language(self, lang: str):
        self.i18n.lang = lang
        self.config.set("language", lang)
        self.window.rebuild_all()

    def on_login_success(self, token: str, email: str, password: str, remember: bool):
        self.access_token = token
        self._api = SeenAPI(token)
        self._current_user_email = email
        if remember:
            self.config.save_credentials(email, password)
            self.config.set("remember_credentials", True)
        else:
            self.config.clear_credentials()
            self.config.set("remember_credentials", False)
        self.show_frame("download")

    def sign_out(self):
        """Full session cleanup."""
        # Cancel any running downloads
        dl_frame = self.window.frames.get("download")
        if dl_frame:
            dl_frame.reset_state()

        # Clear auth state
        self.access_token = None
        self._api = None
        self._current_user_email = None
        self.config.clear_credentials()

        self.show_frame("login")

    def get_api(self) -> SeenAPI:
        if not self._api:
            raise RuntimeError("Not authenticated")
        return self._api

    def run(self):
        self.window.mainloop()
