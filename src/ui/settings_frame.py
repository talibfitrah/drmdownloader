"""Settings frame: output dir, language, account, updates."""

import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from . import theme as T
from .i18n import shape_if_arabic
from ..core.constants import __version__
from ..services.updater import UpdateStatus


class SettingsFrame(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=T.BG)
        self.app = app
        self.i = app.i18n
        self._build()

    def _build(self):
        for w in self.winfo_children():
            w.destroy()

        i = self.i
        start = i.start
        end = i.end
        anchor = i.anchor_start

        # Header
        header = tk.Frame(self, bg=T.BG)
        header.pack(fill="x", padx=20, pady=(16, 8))
        tk.Label(header, text=i.t("settings"), font=T.FONT_LG, fg=T.TEXT, bg=T.BG).pack(side=start)
        ctk.CTkButton(
            header, text=i.t("back"), width=70, height=30, font=T.FONT_SM,
            fg_color=T.BG_CARD, hover_color=T.BORDER, text_color=T.TEXT,
            command=lambda: self.app.show_frame("download"),
        ).pack(side=end)

        # ── Language ──
        self._section(i.t("language"), 20, 20)
        lang_row = tk.Frame(self, bg=T.BG)
        lang_row.pack(fill="x", padx=20, pady=(2, 12))
        self.lang_var = tk.StringVar(value=i.lang)
        ctk.CTkSegmentedButton(
            lang_row, values=["en", "ar"], variable=self.lang_var,
            font=T.FONT_SM, fg_color=T.BG_CARD,
            selected_color=T.ACCENT, selected_hover_color=T.ACCENT_HOVER,
            unselected_color=T.BG_INPUT, unselected_hover_color=T.BORDER,
            text_color=T.TEXT, command=self._on_lang_change,
        ).pack(side=start)
        tk.Label(
            lang_row, text=f"English / {shape_if_arabic('العربية')}",
            font=T.FONT_SM, fg=T.TEXT_DIM, bg=T.BG,
        ).pack(side=start, padx=10)

        # ── Output directory ──
        self._section(i.t("output_dir"), 20, 4)
        out_row = tk.Frame(self, bg=T.BG)
        out_row.pack(fill="x", padx=20, pady=(2, 12))
        self.output_var = tk.StringVar(value=self.app.config.get("output_dir", ""))
        ctk.CTkEntry(
            out_row, textvariable=self.output_var, height=34,
            fg_color=T.BG_INPUT, border_color=T.BORDER, text_color=T.TEXT,
        ).pack(side=start, fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(
            out_row, text=i.t("browse"), width=70, height=34, font=T.FONT_SM,
            fg_color=T.BG_CARD, hover_color=T.BORDER, text_color=T.TEXT,
            command=self._browse_output,
        ).pack(side=start)

        # ── Account ──
        self._section(i.t("account"), 20, 4)
        acc_row = tk.Frame(self, bg=T.BG)
        acc_row.pack(fill="x", padx=20, pady=(2, 12))
        user, _ = self.app.config.get_credentials()
        self.account_label = tk.Label(
            acc_row, text=user or i.t("not_signed_in"),
            font=T.FONT_SM, fg=T.TEXT, bg=T.BG, anchor=anchor,
        )
        self.account_label.pack(side=start)
        ctk.CTkButton(
            acc_row, text=i.t("sign_out"), width=100, height=30, font=T.FONT_SM,
            fg_color="#7f1d1d", hover_color="#991b1b", text_color=T.TEXT,
            command=self._sign_out,
        ).pack(side=end)

        # ── Save ──
        ctk.CTkButton(
            self, text=i.t("save_settings"), width=160, height=36, font=T.FONT_MD,
            fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER, command=self._save,
        ).pack(padx=20, pady=(8, 4), anchor=anchor)
        self.save_status = tk.Label(self, text="", font=T.FONT_SM, fg=T.TEXT_SUCCESS, bg=T.BG)
        self.save_status.pack(padx=20, anchor=anchor)

        # ── Spacer + Version ──
        tk.Frame(self, bg=T.BG).pack(fill="both", expand=True)
        bottom = tk.Frame(self, bg=T.BG)
        bottom.pack(fill="x", padx=20, pady=(0, 16))
        tk.Label(
            bottom, text=f"{i.t('app_title')} v{__version__}",
            font=T.FONT_SM, fg=T.TEXT_DIM, bg=T.BG,
        ).pack(side=start)

        self.update_btn = ctk.CTkButton(
            bottom, text=i.t("check_updates"), width=150, height=30, font=T.FONT_SM,
            fg_color=T.BG_CARD, hover_color=T.BORDER, text_color=T.TEXT,
            command=self._check_update,
        )
        self.update_btn.pack(side=end)
        self.update_label = tk.Label(bottom, text="", font=T.FONT_SM, fg=T.TEXT_DIM, bg=T.BG)
        self.update_label.pack(side=end, padx=8)

    def rebuild(self):
        self.i = self.app.i18n
        self._build()

    def _section(self, text, padx, pady):
        tk.Label(
            self, text=text, font=T.FONT_SM, fg=T.TEXT_DIM, bg=T.BG,
            anchor=self.i.anchor_start,
        ).pack(fill="x", padx=padx, pady=(pady, 0))

    def _browse_output(self):
        d = filedialog.askdirectory(title=self.i.t("select_output_folder"))
        if d:
            self.output_var.set(d)

    def _save(self):
        self.app.config.set("output_dir", self.output_var.get())
        self.save_status.configure(text=self.i.t("settings_saved"))
        self.after(3000, lambda: self.save_status.configure(text=""))

    def _sign_out(self):
        self.app.sign_out()

    def _on_lang_change(self, value):
        self.app.set_language(value)

    # ── Update flow ──

    def _check_update(self):
        self.update_btn.configure(state="disabled", text=self.i.t("checking"))
        self.update_label.configure(text="", fg=T.TEXT_DIM)
        threading.Thread(target=self._do_check_update, daemon=True).start()

    def _do_check_update(self):
        from ..services.updater import check_for_update, UpdateCheckResult
        try:
            result = check_for_update()
        except Exception as e:
            result = UpdateCheckResult(
                UpdateStatus.ERROR, error_message=str(e),
            )
        self.after(0, lambda: self._handle_update_result(result))

    def _handle_update_result(self, result):
        self.update_btn.configure(state="normal", text=self.i.t("check_updates"))

        if result.status == UpdateStatus.AVAILABLE:
            self.update_label.configure(
                text=self.i.t("update_available", result.latest_version),
                fg=T.TEXT_SUCCESS,
            )
            if messagebox.askyesno(
                self.i.t("app_title"),
                self.i.t("update_confirm", result.latest_version),
            ):
                self._do_download_update(result.download_url, result.sha256)
        elif result.status == UpdateStatus.UP_TO_DATE:
            self.update_label.configure(text=self.i.t("up_to_date"), fg=T.TEXT_DIM)
            self.after(3000, lambda: self.update_label.configure(text=""))
        elif result.status == UpdateStatus.ERROR:
            self.update_label.configure(
                text=result.error_message or self.i.t("error"),
                fg=T.TEXT_ERROR,
            )

    def _do_download_update(self, url: str, sha256: str = ""):
        self.update_btn.configure(state="disabled", text=self.i.t("downloading_update"))
        threading.Thread(
            target=self._download_and_apply, args=(url, sha256), daemon=True,
        ).start()

    def _download_and_apply(self, url: str, sha256: str = ""):
        from ..services.updater import download_update, apply_update
        import sys

        try:
            def progress(pct):
                self.after(0, lambda: self.update_label.configure(
                    text=f"{int(pct * 100)}%", fg=T.TEXT_DIM,
                ))

            new_exe = download_update(url, expected_sha256=sha256, progress_cb=progress)

            if getattr(sys, "frozen", False):
                self.after(0, lambda: self._confirm_apply(new_exe))
            else:
                self.after(0, lambda: self.update_label.configure(
                    text=self.i.t("update_downloaded_dev"), fg=T.TEXT_SUCCESS,
                ))
                self.after(0, lambda: self.update_btn.configure(
                    state="normal", text=self.i.t("check_updates"),
                ))
        except Exception as e:
            msg = self.i.t("download_failed", e)
            self.after(0, lambda: self.update_label.configure(
                text=msg, fg=T.TEXT_ERROR,
            ))
            self.after(0, lambda: self.update_btn.configure(
                state="normal", text=self.i.t("check_updates"),
            ))

    def _confirm_apply(self, new_exe: str):
        from ..services.updater import apply_update
        if messagebox.askyesno(
            self.i.t("app_title"),
            self.i.t("update_restart_confirm"),
        ):
            apply_update(new_exe)
        else:
            self.update_label.configure(
                text=self.i.t("update_ready_restart"), fg=T.TEXT_SUCCESS,
            )
            self.update_btn.configure(state="normal", text=self.i.t("check_updates"))
