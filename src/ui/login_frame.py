import threading
import tkinter as tk

import customtkinter as ctk

from . import theme as T


class LoginFrame(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=T.BG)
        self.app = app
        self.i = app.i18n
        self._build()

    def _build(self):
        for w in self.winfo_children():
            w.destroy()

        i = self.i
        anchor = i.anchor_start

        center = tk.Frame(self, bg=T.BG)
        center.place(relx=0.5, rely=0.45, anchor="center")

        tk.Label(center, text=i.t("login_title"), font=T.FONT_XL, fg=T.TEXT, bg=T.BG).pack(pady=(0, 5))
        tk.Label(center, text=i.t("login_subtitle"), font=T.FONT_SM, fg=T.TEXT_DIM, bg=T.BG).pack(pady=(0, 25))

        tk.Label(center, text=i.t("email"), font=T.FONT_SM, fg=T.TEXT_DIM, bg=T.BG, anchor=anchor).pack(fill="x", padx=40)
        self.email_var = tk.StringVar()
        self.email_entry = ctk.CTkEntry(
            center, textvariable=self.email_var, width=320, height=38,
            fg_color=T.BG_INPUT, border_color=T.BORDER, text_color=T.TEXT,
            placeholder_text=i.t("email"), justify=i.justify,
        )
        self.email_entry.pack(padx=40, pady=(2, 12))

        tk.Label(center, text=i.t("password"), font=T.FONT_SM, fg=T.TEXT_DIM, bg=T.BG, anchor=anchor).pack(fill="x", padx=40)
        self.password_var = tk.StringVar()
        self.password_entry = ctk.CTkEntry(
            center, textvariable=self.password_var, width=320, height=38,
            fg_color=T.BG_INPUT, border_color=T.BORDER, text_color=T.TEXT,
            show="*", placeholder_text=i.t("password"), justify=i.justify,
        )
        self.password_entry.pack(padx=40, pady=(2, 12))

        self.remember_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            center, text=i.t("remember"), variable=self.remember_var,
            font=T.FONT_SM, text_color=T.TEXT_DIM,
            fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER, border_color=T.BORDER,
        ).pack(padx=40, anchor=anchor, pady=(0, 18))

        self.signin_btn = ctk.CTkButton(
            center, text=i.t("sign_in"), width=320, height=40,
            font=T.FONT_MD, fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
            command=self._on_signin,
        )
        self.signin_btn.pack(padx=40)

        self.status_label = tk.Label(center, text="", font=T.FONT_SM, fg=T.TEXT_DIM, bg=T.BG)
        self.status_label.pack(pady=(14, 0))

        self.password_entry.bind("<Return>", lambda _: self._on_signin())
        self.email_entry.bind("<Return>", lambda _: self.password_entry.focus())

    def rebuild(self):
        self.i = self.app.i18n
        email = self.email_var.get() if hasattr(self, "email_var") else ""
        pw = self.password_var.get() if hasattr(self, "password_var") else ""
        rem = self.remember_var.get() if hasattr(self, "remember_var") else True
        self._build()
        self.email_var.set(email)
        self.password_var.set(pw)
        self.remember_var.set(rem)

    def prefill(self, username: str, password: str, remember: bool):
        self.email_var.set(username)
        self.password_var.set(password)
        self.remember_var.set(remember)

    def _on_signin(self):
        email = self.email_var.get().strip()
        pw = self.password_var.get()
        if not email or not pw:
            self.status_label.configure(text=self.i.t("enter_credentials"), fg=T.TEXT_ERROR)
            return

        # MAJOR fix #6: capture Tk state BEFORE spawning thread
        remember = self.remember_var.get()

        self.signin_btn.configure(state="disabled", text=self.i.t("signing_in"))
        self.status_label.configure(text=self.i.t("connecting"), fg=T.TEXT_DIM)
        threading.Thread(
            target=self._do_auth, args=(email, pw, remember), daemon=True,
        ).start()

    def _do_auth(self, email: str, password: str, remember: bool):
        from ..core.auth import SeenAuth, AuthenticationError

        i = self.i

        def on_status(key):
            # Translate the i18n key on the main thread
            self.after(0, lambda: self.status_label.configure(
                text=i.t(key), fg=T.TEXT_DIM,
            ))

        try:
            auth = SeenAuth(email, password, on_status=on_status)
            token = auth.authenticate()
            # Pass pre-captured `remember` — no Tk access from this thread
            self.after(0, lambda: self.app.on_login_success(
                token, email, password, remember,
            ))
        except AuthenticationError as e:
            self.after(0, lambda: self._show_error(str(e)))
        except Exception as e:
            self.after(0, lambda: self._show_error(i.t("conn_error", e)))

    def _show_error(self, msg: str):
        self.signin_btn.configure(state="normal", text=self.i.t("sign_in"))
        self.status_label.configure(text=msg, fg=T.TEXT_ERROR)
