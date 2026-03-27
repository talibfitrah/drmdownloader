"""Download frame: URL input, episode list, progress, cancel."""

import threading
import tkinter as tk

import customtkinter as ctk

from . import theme as T
from .i18n import shape_if_arabic
from ..core.url_parser import parse_seenshow_url
from ..services.download_manager import DownloadManager, EpisodeTask, StatusUpdate


class EpisodeRow(tk.Frame):
    def __init__(self, master, episode, i18n, **kw):
        super().__init__(master, bg=T.BG_CARD, height=36, **kw)
        self.episode = episode
        self.eid = episode["id"]
        self.i = i18n
        self.pack_propagate(False)

        start = self.i.start
        end = self.i.end

        self.selected = tk.BooleanVar(value=True)
        self.cb = ctk.CTkCheckBox(
            self, text="", variable=self.selected, width=24,
            fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
            border_color=T.BORDER, checkbox_width=18, checkbox_height=18,
        )
        self.cb.pack(side=start, padx=(8, 4), pady=4)

        name = episode.get("name", f"Episode {self.eid}")
        dur = episode.get("duration", "")
        label_text = f"{name}   ({dur})" if dur else name
        label_text = shape_if_arabic(label_text)

        tk.Label(
            self, text=label_text, font=T.FONT_SM, fg=T.TEXT, bg=T.BG_CARD,
            anchor=self.i.anchor_start,
        ).pack(side=start, fill="x", expand=True, padx=4)

        self.status_label = tk.Label(
            self, text="", font=T.FONT_SM, fg=T.TEXT_DIM, bg=T.BG_CARD,
            width=30, anchor=self.i.anchor_end,
        )
        self.status_label.pack(side=end, padx=(4, 10))

    def set_status(self, text, color=T.TEXT_DIM):
        self.status_label.configure(text=text, fg=color)


class DownloadFrame(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=T.BG)
        self.app = app
        self.i = app.i18n
        self.episode_rows: dict[int, EpisodeRow] = {}
        self._dm: DownloadManager | None = None
        self._current_episodes: list[dict] = []
        self._media_id: int | None = None
        self._wheel_bindings: list[str] = []
        self._build()

    def _build(self):
        # Unbind any prior global wheel bindings before rebuild
        self._unbind_wheel()

        for w in self.winfo_children():
            w.destroy()
        self.episode_rows.clear()

        i = self.i
        start = i.start
        end = i.end

        # ── Top bar: URL ──
        top = tk.Frame(self, bg=T.BG)
        top.pack(fill="x", padx=16, pady=(12, 0))

        tk.Label(top, text=i.t("url_label"), font=T.FONT_MD, fg=T.TEXT, bg=T.BG).pack(side=start)

        self.url_var = tk.StringVar()
        self.url_entry = ctk.CTkEntry(
            top, textvariable=self.url_var, height=36,
            fg_color=T.BG_INPUT, border_color=T.BORDER, text_color=T.TEXT,
            placeholder_text=i.t("url_placeholder"),
        )
        self.url_entry.pack(side=start, fill="x", expand=True, padx=(8, 8))
        self.url_entry.bind("<Return>", lambda _: self._on_fetch())

        # Fix Ctrl+A and Ctrl+V for the entry
        inner = self.url_entry._entry

        def _select_all(e):
            e.widget.select_range(0, "end")
            e.widget.icursor("end")
            return "break"

        def _paste_over(e):
            try:
                if e.widget.selection_present():
                    e.widget.delete("sel.first", "sel.last")
                e.widget.insert("insert", e.widget.clipboard_get())
            except tk.TclError:
                pass
            return "break"

        inner.bind("<Control-a>", _select_all)
        inner.bind("<Control-A>", _select_all)
        inner.bind("<Control-v>", _paste_over)
        inner.bind("<Control-V>", _paste_over)

        self.fetch_btn = ctk.CTkButton(
            top, text=i.t("fetch"), width=80, height=36, font=T.FONT_MD,
            fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER, command=self._on_fetch,
        )
        self.fetch_btn.pack(side=start)

        # ── Title ──
        self.title_label = tk.Label(
            self, text="", font=T.FONT_LG, fg=T.TEXT, bg=T.BG, anchor=i.anchor_start,
        )
        self.title_label.pack(fill="x", padx=20, pady=(10, 2))

        # ── Episode list ──
        self._list_outer = tk.Frame(self, bg=T.BG_SECONDARY, bd=1, relief="flat")
        self._list_outer.pack(fill="both", expand=True, padx=16, pady=(4, 4))

        canvas = tk.Canvas(self._list_outer, bg=T.BG_SECONDARY, highlightthickness=0)
        self._scrollbar = tk.Scrollbar(self._list_outer, orient="vertical", command=canvas.yview)
        self.list_frame = tk.Frame(canvas, bg=T.BG_SECONDARY)

        self.list_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.list_frame, anchor="nw", tags="inner")
        canvas.configure(yscrollcommand=self._scrollbar.set)

        def _resize_inner(e):
            canvas.itemconfig("inner", width=e.width)
        canvas.bind("<Configure>", _resize_inner)

        self._scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        self._canvas = canvas

        # Placeholder
        self.placeholder = tk.Label(
            self.list_frame, text=i.t("placeholder_text"),
            font=T.FONT_MD, fg=T.TEXT_DIM, bg=T.BG_SECONDARY, justify="center",
        )
        self.placeholder.pack(pady=60)

        # ── Bottom bar ──
        bot = tk.Frame(self, bg=T.BG)
        bot.pack(fill="x", padx=16, pady=(0, 4))

        btn_row = tk.Frame(bot, bg=T.BG)
        btn_row.pack(fill="x", pady=(4, 6))

        ctk.CTkButton(
            btn_row, text=i.t("select_all"), width=100, height=30, font=T.FONT_SM,
            fg_color=T.BG_CARD, hover_color=T.BORDER, text_color=T.TEXT,
            command=self._select_all,
        ).pack(side=start, padx=(0, 4))

        ctk.CTkButton(
            btn_row, text=i.t("deselect_all"), width=110, height=30, font=T.FONT_SM,
            fg_color=T.BG_CARD, hover_color=T.BORDER, text_color=T.TEXT,
            command=self._deselect_all,
        ).pack(side=start, padx=(0, 4))

        self.cancel_btn = ctk.CTkButton(
            btn_row, text=i.t("cancel"), width=80, height=30, font=T.FONT_SM,
            fg_color="#7f1d1d", hover_color="#991b1b", text_color=T.TEXT,
            command=self._on_cancel, state="disabled",
        )
        self.cancel_btn.pack(side=end, padx=(4, 0))

        self.download_btn = ctk.CTkButton(
            btn_row, text=i.t("download_selected"), width=160, height=30,
            font=T.FONT_MD, fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
            command=self._on_download, state="disabled",
        )
        self.download_btn.pack(side=end, padx=(4, 4))

        # Progress
        prog = tk.Frame(bot, bg=T.BG)
        prog.pack(fill="x", pady=(0, 4))

        self.progress_label = tk.Label(
            prog, text="", font=T.FONT_SM, fg=T.TEXT_DIM, bg=T.BG, anchor=i.anchor_start,
        )
        self.progress_label.pack(fill="x")

        self.progress_bar = ctk.CTkProgressBar(
            prog, height=8, fg_color=T.BG_SECONDARY, progress_color=T.ACCENT, corner_radius=4,
        )
        self.progress_bar.pack(fill="x", pady=(2, 0))
        self.progress_bar.set(0)

    def _bind_wheel(self):
        """Bind mouse wheel scrolling (tracked for cleanup)."""
        self._unbind_wheel()
        canvas = self._canvas

        def _on_mousewheel(e):
            if e.num == 4:
                canvas.yview_scroll(-3, "units")
            elif e.num == 5:
                canvas.yview_scroll(3, "units")
            elif e.delta:
                canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        # Use bind on the canvas, not bind_all, to avoid global pollution
        self._wheel_bindings = [
            canvas.bind("<Button-4>", _on_mousewheel),
            canvas.bind("<Button-5>", _on_mousewheel),
            canvas.bind("<MouseWheel>", _on_mousewheel),
        ]
        # Also bind on the list frame so scrolling works when hovering over rows
        self.list_frame.bind("<Button-4>", _on_mousewheel)
        self.list_frame.bind("<Button-5>", _on_mousewheel)
        self.list_frame.bind("<MouseWheel>", _on_mousewheel)

    def _unbind_wheel(self):
        """Remove any prior wheel bindings."""
        if hasattr(self, "_canvas") and self._canvas.winfo_exists():
            try:
                self._canvas.unbind("<Button-4>")
                self._canvas.unbind("<Button-5>")
                self._canvas.unbind("<MouseWheel>")
            except tk.TclError:
                pass
        if hasattr(self, "list_frame") and self.list_frame.winfo_exists():
            try:
                self.list_frame.unbind("<Button-4>")
                self.list_frame.unbind("<Button-5>")
                self.list_frame.unbind("<MouseWheel>")
            except tk.TclError:
                pass
        self._wheel_bindings = []

    def rebuild(self):
        self.i = self.app.i18n
        saved_url = self.url_var.get() if hasattr(self, "url_var") else ""
        self._build()
        self.url_var.set(saved_url)
        # Don't restore stale episode data — require re-fetch

    def reset_state(self):
        """Clear all episode/download state (used on sign-out)."""
        self._current_episodes = []
        self._media_id = None
        if self._dm and self._dm.is_running:
            self._dm.cancel()
        self._dm = None

        for w in list(self.episode_rows.values()):
            w.destroy()
        self.episode_rows.clear()

        if hasattr(self, "title_label"):
            self.title_label.configure(text="", fg=T.TEXT)
        if hasattr(self, "progress_label"):
            self.progress_label.configure(text="", fg=T.TEXT_DIM)
        if hasattr(self, "progress_bar"):
            self.progress_bar.set(0)
        if hasattr(self, "download_btn"):
            self.download_btn.configure(state="disabled")
        if hasattr(self, "cancel_btn"):
            self.cancel_btn.configure(state="disabled")
        if hasattr(self, "fetch_btn"):
            self.fetch_btn.configure(state="normal")

        # Re-show placeholder
        if hasattr(self, "placeholder"):
            self.placeholder.pack(pady=60)

        self._unbind_wheel()

    # ── Fetch ──
    def _on_fetch(self):
        url = self.url_var.get().strip()
        if not url:
            return

        # MAJOR fix #3: clear stale state BEFORE fetching
        self._clear_episodes()
        self.fetch_btn.configure(state="disabled", text="...")
        self.title_label.configure(text=self.i.t("loading"), fg=T.TEXT)
        self.download_btn.configure(state="disabled")

        threading.Thread(target=self._do_fetch, args=(url,), daemon=True).start()

    def _clear_episodes(self):
        """Remove old episode rows and reset model state."""
        for w in list(self.episode_rows.values()):
            w.destroy()
        self.episode_rows.clear()
        self._current_episodes = []
        self._media_id = None
        self.progress_label.configure(text="", fg=T.TEXT_DIM)
        self.progress_bar.set(0)
        self._unbind_wheel()

    def _do_fetch(self, url):
        try:
            parsed = parse_seenshow_url(url)
            api = self.app.get_api()
            if parsed.url_type == "series":
                title, episodes = api.get_all_episodes(parsed.media_id)
                self.after(0, lambda: self._populate(parsed.media_id, title, episodes))
            else:
                media = api.get_media_detail(parsed.media_id)
                title = media.get("mediaTitle", "")
                ep = api.find_episode(media, parsed.episode_id)
                if ep:
                    ep["_media_title"] = title
                    self.after(0, lambda: self._populate(parsed.media_id, title, [ep]))
                else:
                    self.after(0, lambda: self._fetch_error(self.i.t("episode_not_found")))
        except Exception as e:
            self.after(0, lambda: self._fetch_error(str(e)))

    def _populate(self, media_id, title, episodes):
        self._media_id = media_id
        self._current_episodes = episodes
        self.fetch_btn.configure(state="normal", text=self.i.t("fetch"))
        self.title_label.configure(text=shape_if_arabic(title), fg=T.TEXT)
        self.placeholder.pack_forget()

        for ep in episodes:
            row = EpisodeRow(self.list_frame, ep, self.i)
            row.pack(fill="x", pady=2, padx=4, anchor="n")
            self.episode_rows[ep["id"]] = row

        # Enable download button
        self.download_btn.configure(state="normal")

        # Toggle scrolling based on episode count
        if len(episodes) <= 1:
            self._scrollbar.pack_forget()
            self._unbind_wheel()
        else:
            self._scrollbar.pack(side="right", fill="y")
            self._bind_wheel()

        self._canvas.yview_moveto(0)

    def _fetch_error(self, msg):
        # MAJOR fix #3: clear everything on error — no stale state
        self.fetch_btn.configure(state="normal", text=self.i.t("fetch"))
        self.title_label.configure(text=msg, fg=T.TEXT_ERROR)
        self.download_btn.configure(state="disabled")
        self._current_episodes = []
        self._media_id = None
        # Show placeholder again
        self.placeholder.pack(pady=60)

    def _select_all(self):
        for r in self.episode_rows.values():
            r.selected.set(True)

    def _deselect_all(self):
        for r in self.episode_rows.values():
            r.selected.set(False)

    # ── Download ──
    def _on_download(self):
        tasks = []
        for ep in self._current_episodes:
            row = self.episode_rows.get(ep["id"])
            if row and row.selected.get():
                tasks.append(EpisodeTask(
                    media_id=self._media_id, episode_id=ep["id"],
                    name=ep.get("name", ""), duration=ep.get("duration", ""),
                ))
        if not tasks:
            return

        self.download_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.fetch_btn.configure(state="disabled")

        self._dm = DownloadManager(
            api=self.app.get_api(),
            output_dir=self.app.config.get("output_dir"),
            i18n=self.i,
        )
        self._dm.start(tasks)
        self._poll_status()

    def _poll_status(self):
        if not self._dm:
            return
        import queue as _q
        try:
            while True:
                u: StatusUpdate = self._dm.status_queue.get_nowait()
                if u.phase in ("batch_done", "batch_cancelled", "batch_error"):
                    self._on_batch_finished(u.phase)
                    return
                self._handle_update(u)
        except _q.Empty:
            pass
        self.after(100, self._poll_status)

    def _handle_update(self, u):
        row = self.episode_rows.get(u.episode_id)
        if not row:
            return
        i = self.i
        if u.phase == "done":
            row.set_status(i.t("done"), T.TEXT_SUCCESS)
        elif u.phase == "error":
            row.set_status(i.t("error"), T.TEXT_ERROR)
        elif u.phase == "cancelled":
            row.set_status(i.t("cancelled"), T.TEXT_WARNING)
        else:
            pct = int(u.progress * 100)
            row.set_status(f"{u.message} {pct}%", T.TEXT_DIM)
        self.progress_bar.set(u.progress)
        self.progress_label.configure(text=u.message, fg=T.TEXT_DIM)

    def _on_batch_finished(self, terminal: str):
        """Handle all batch terminal states: done, cancelled, error."""
        self.download_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        self.fetch_btn.configure(state="normal")

        i = self.i
        if terminal == "batch_done":
            self.progress_label.configure(text=i.t("all_done"), fg=T.TEXT_SUCCESS)
            self.progress_bar.set(1.0)
        elif terminal == "batch_cancelled":
            self.progress_label.configure(text=i.t("cancelled"), fg=T.TEXT_WARNING)
        elif terminal == "batch_error":
            self.progress_label.configure(text=i.t("error"), fg=T.TEXT_ERROR)

    def _on_cancel(self):
        if self._dm:
            self._dm.cancel()
        self.cancel_btn.configure(state="disabled")
        self.progress_label.configure(text=self.i.t("cancelling"), fg=T.TEXT_WARNING)
