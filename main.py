"""
FaceGate — entry point.

Run:  python main.py
"""
import tkinter as tk
from types import SimpleNamespace

import config
from core.csv_logger import AuditLogger
from core.face_engine import CameraStream, FaceEngine
from core.storage import AccountStore, SettingsStore
from ui.login_window import LoginWindow
from ui.main_window import MainWindow


class FaceGateApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(config.WINDOW_TITLE)
        self.configure(bg="#0E2A47")
        self.option_add("*Font", ("Segoe UI", 10))

        settings = SettingsStore()
        self.ctx = SimpleNamespace(
            settings=settings,
            accounts=AccountStore(),
            engine=FaceEngine(settings),
            audit=AuditLogger(),
            camera=CameraStream(settings.get("camera_index")),
        )
        self._show_login()
        self.protocol("WM_DELETE_WINDOW", self._quit)

    # ------------------------------------------------------- screen swapping
    def _clear(self):
        for child in self.winfo_children():
            child.destroy()

    def _show_login(self):
        self._clear()
        self.geometry(config.LOGIN_SIZE)
        self.resizable(False, False)
        LoginWindow(self, self.ctx, on_success=self._show_main)

    def _show_main(self, username):
        self._clear()
        self.geometry(config.APP_SIZE)
        self.resizable(True, True)
        self.minsize(1000, 640)
        MainWindow(self, self.ctx, username, on_logout=self._show_login)

    def _quit(self):
        try:
            self.ctx.camera.stop()
        finally:
            self.destroy()


if __name__ == "__main__":
    FaceGateApp().mainloop()