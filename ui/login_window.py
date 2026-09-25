"""
FaceGate — eGov-style login.

Six-digit PIN entered on a grid keypad (like the eGov PH app), optional
Face Unlock, attempt limiting and timed lockout.
"""
import time
import tkinter as tk

import cv2

import config
from ui.widgets import frame_to_photo

BG, PANEL, ACCENT = "#0E2A47", "#123B63", "#2F80ED"
FG, MUTED, DANGER = "#FFFFFF", "#9FB3C8", "#E5484D"


class LoginWindow(tk.Frame):
    def __init__(self, master, ctx, on_success):
        super().__init__(master, bg=BG)
        self.ctx, self.on_success = ctx, on_success
        self.username = "admin"
        self.pin = ""
        self.attempts = 0
        self.locked_until = 0.0
        self._verify_job = None
        self._build()
        self.pack(fill="both", expand=True)
        self.focus_set()
        self.bind_all("<Key>", self._on_key)

    # ------------------------------------------------------------------ UI
    def _build(self):
        tk.Label(self, text="FaceGate", font=("Segoe UI", 26, "bold"),
                 bg=BG, fg=FG).pack(pady=(48, 2))
        tk.Label(self, text="Secure Access Console", font=("Segoe UI", 11),
                 bg=BG, fg=MUTED).pack(pady=(0, 26))

        self.dots = tk.Canvas(self, width=240, height=26, bg=BG,
                              highlightthickness=0)
        self.dots.pack()
        self._draw_dots()

        self.status = tk.Label(self, text="Enter your 6-digit PIN",
                               font=("Segoe UI", 10), bg=BG, fg=MUTED)
        self.status.pack(pady=(10, 18))

        pad = tk.Frame(self, bg=BG)
        pad.pack()
        for r, row in enumerate([["1", "2", "3"], ["4", "5", "6"],
                                 ["7", "8", "9"], ["C", "0", "⌫"]]):
            for c, key in enumerate(row):
                tk.Button(pad, text=key, width=6, height=2,
                          font=("Segoe UI", 13, "bold"), relief="flat",
                          bg=PANEL, fg=FG, cursor="hand2",
                          activebackground=ACCENT, activeforeground=FG,
                          command=lambda k=key: self._press(k)
                          ).grid(row=r, column=c, padx=6, pady=6)

        if self._face_unlock_available():
            tk.Button(self, text="Use Face Unlock", font=("Segoe UI", 10),
                      bg=BG, fg=ACCENT, relief="flat", bd=0, cursor="hand2",
                      activebackground=BG, activeforeground=FG,
                      command=self._face_unlock).pack(pady=(16, 0))

    def _draw_dots(self):
        self.dots.delete("all")
        for i in range(config.PIN_LENGTH):
            x = 16 + i * 36
            filled = i < len(self.pin)
            self.dots.create_oval(x, 5, x + 16, 21,
                                  fill=FG if filled else "",
                                  outline=MUTED, width=2)

    # ---------------------------------------------------------------- input
    def _on_key(self, event):
        if event.char.isdigit():
            self._press(event.char)
        elif event.keysym == "BackSpace":
            self._press("⌫")
        elif event.keysym == "Escape":
            self._press("C")

    def _press(self, key):
        if time.time() < self.locked_until:
            return
        if self._verify_job:
            self.after_cancel(self._verify_job)
            self._verify_job = None
        if key == "C":
            self.pin = ""
        elif key == "⌫":
            self.pin = self.pin[:-1]
        elif len(self.pin) < config.PIN_LENGTH:
            self.pin += key
        self._draw_dots()
        if len(self.pin) == config.PIN_LENGTH:
            self._verify_job = self.after(120, self._verify)

    def _verify(self):
        self._verify_job = None
        if self.ctx.accounts.verify(self.username, self.pin):
            self.ctx.audit.log("LOGIN", self.username, details="pin")
            self.on_success(self.username)
            return
        self.attempts += 1
        left = config.MAX_LOGIN_ATTEMPTS - self.attempts
        self.pin = ""
        self._draw_dots()
        if left <= 0:
            self.locked_until = time.time() + config.LOCKOUT_SECONDS
            self.attempts = 0
            self._countdown()
        else:
            self._flash(f"Incorrect PIN — {left} attempt(s) left", DANGER)

    def _countdown(self):
        remaining = int(self.locked_until - time.time())
        if remaining <= 0:
            self._flash("Enter your 6-digit PIN", MUTED)
            return
        self._flash(f"Too many attempts — locked for {remaining}s", DANGER)
        self.after(1000, self._countdown)

    def _flash(self, msg, color):
        self.status.configure(text=msg, fg=color)

    # ---------------------------------------------------------- face unlock
    def _face_unlock_available(self):
        return (self.ctx.accounts.face_unlock_enabled(self.username)
                and self.username in self.ctx.engine.people)

    def _face_unlock(self):
        FaceUnlockDialog(self, self.ctx, self.username,
                         on_success=lambda: self.on_success(self.username))

    def destroy(self):
        try:
            self.unbind_all("<Key>")
        except Exception:
            pass
        super().destroy()


class FaceUnlockDialog(tk.Toplevel):
    """Modal camera dialog that logs you in with your face."""

    TIMEOUT = 15.0

    def __init__(self, master, ctx, username, on_success):
        super().__init__(master, title="Face Unlock")
        self.ctx, self.username, self.on_success = ctx, username, on_success
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())

        tk.Label(self, text="Look at the camera…",
                 font=("Segoe UI", 11)).pack(pady=(10, 4))
        self.preview = tk.Label(self, bg="black")
        self.preview.pack(padx=12, pady=8)
        self.hint = tk.Label(self, text="", fg="#555")
        self.hint.pack(pady=(0, 10))
        self._photo = None

        self.protocol("WM_DELETE_WINDOW", self._close)
        self.deadline = time.time() + self.TIMEOUT
        self.ctx.camera.start()
        self.after(50, self._tick)

    def _tick(self):
        if not self.winfo_exists():
            return
        frame = self.ctx.camera.read()
        if frame is not None:
            display = frame.copy()
            faces = self.ctx.engine.detect(frame)
            if len(faces) == 1:
                x, y, w, h = map(int, faces[0][0:4])
                feat = self.ctx.engine.feature(frame, faces[0])
                name, score, ok = self.ctx.engine.identify(feat)
                if ok and name in self.ctx.accounts.accounts:
                    cv2.rectangle(display, (x, y), (x + w, y + h),
                                  (46, 204, 113), 3)
                    self._photo = frame_to_photo(display, config.PREVIEW_WIDTH)
                    self.preview.configure(image=self._photo)
                    self.ctx.audit.log("LOGIN", name, score, details="face")
                    self._close()
                    self.on_success()
                    return
                cv2.rectangle(display, (x, y), (x + w, y + h), (46, 204, 113), 2)
                self.hint.configure(text="Face not recognised")
            elif len(faces) > 1:
                self.hint.configure(text="Only one face, please")
            else:
                self.hint.configure(text="No face detected")
            self._photo = frame_to_photo(display, config.PREVIEW_WIDTH)
            self.preview.configure(image=self._photo)

        if time.time() > self.deadline:
            self.hint.configure(text="Timed out — use your PIN")
            self.after(1200, self._close)
            return
        self.after(config.CAMERA_FPS_MS, self._tick)

    def _close(self):
        try:
            self.ctx.camera.stop()
        finally:
            self.destroy()