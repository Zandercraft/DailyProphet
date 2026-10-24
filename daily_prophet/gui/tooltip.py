"""Lightweight tooltip pop-up helper for CustomTkinter widgets.

Styled to match the dark-parchment aesthetic of The Daily Prophet.
"""

from __future__ import annotations
import tkinter as tk
from typing import Optional
import customtkinter as ctk


class ToolTip:
    """Displays a sleek dark-parchment tooltip when hovering over a widget."""

    def __init__(
        self,
        widget: tk.Widget | ctk.CTkBaseClass,
        text: str,
        delay_ms: int = 350,
        bg_color: str = "#231c16",
        text_color: str = "#f5ede0",
        border_color: str = "#544333",
    ):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.bg_color = bg_color
        self.text_color = text_color
        self.border_color = border_color

        self._tip_window: Optional[tk.Toplevel] = None
        self._timer_id: Optional[str] = None

        # Bind events
        self.widget.bind("<Enter>", self._on_enter, add="+")
        self.widget.bind("<Leave>", self._on_leave, add="+")
        self.widget.bind("<ButtonPress>", self._on_leave, add="+")

    def _on_enter(self, event=None):
        self._schedule()

    def _on_leave(self, event=None):
        self._cancel()
        self._hide()

    def _schedule(self):
        self._cancel()
        self._timer_id = self.widget.after(self.delay_ms, self._show)

    def _cancel(self):
        if self._timer_id is not None:
            self.widget.after_cancel(self._timer_id)
            self._timer_id = None

    def _show(self):
        if self._tip_window or not self.text:
            return

        try:
            x = self.widget.winfo_rootx() + (self.widget.winfo_width() // 2)
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4

            self._tip_window = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.attributes("-topmost", True)

            # Frame with subtle engraved border
            frame = tk.Frame(tw, background=self.border_color, bd=1)
            frame.pack(fill="both", expand=True)

            label = tk.Label(
                frame,
                text=self.text,
                background=self.bg_color,
                foreground=self.text_color,
                font=("Segoe UI", 9),
                padx=6,
                pady=3,
            )
            label.pack()

            tw.wm_geometry(f"+{x}+{y}")
        except Exception:
            self._hide()

    def _hide(self):
        if self._tip_window:
            try:
                self._tip_window.destroy()
            except Exception:
                pass
            self._tip_window = None

    def update_text(self, new_text: str):
        self.text = new_text


def add_tooltip(widget: tk.Widget | ctk.CTkBaseClass, text: str, delay_ms: int = 350) -> ToolTip:
    """Convenience helper to attach a tooltip to any widget."""
    return ToolTip(widget, text, delay_ms=delay_ms)
