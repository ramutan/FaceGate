"""FaceGate — main application shell (header + tabbed workspace)."""
import datetime
import tkinter as tk
from tkinter import messagebox, ttk

from ui.dashboard_tab import DashboardTab
from ui.enroll_tab import EnrollTab
from ui.logs_tab import LogsTab
from ui.settings_tab import SettingsTab
from ui.users_tab import UsersTab

BG, HEADER_BG, ACCENT = "#F4F6F8", "#0E2A47", "#2F80ED"


class MainWindow(tk.Frame):
    def __init__(self, master, ctx, username, on_logout):
        super().__init__(master, bg=BG)
        self.ctx, self.username, self.on_logout = ctx, username, on_logout
        self._build()
        self.pack(fill="both", expand=True)

    def _build(self):
        header = tk.Frame(self, bg=HEADER_BG, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="FaceGate", font=("Segoe UI", 14, "bold"),
                 bg=HEADER_BG, fg="white").pack(side="left", padx=16)
        self.clock = tk.Label(header, font=("Segoe UI", 10),
                              bg=HEADER_BG, fg="#9FB3C8")
        self.clock.pack(side="right", padx=16)
        tk.Button(header, text="Logout", font=("Segoe UI", 9, "bold"),
                  bg=ACCENT, fg="white", relief="flat", cursor="hand2",
                  activebackground="#2568C4", activeforeground="white",
                  command=self._logout).pack(side="right", padx=8,
                                             ipadx=8, ipady=3)
        tk.Label(header, text=f"Signed in: {self.username}",
                 font=("Segoe UI", 10), bg=HEADER_BG,
                 fg="white").pack(side="right", padx=8)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.users_tab = UsersTab(self.notebook, self.ctx)
        self.dashboard = DashboardTab(self.notebook, self.ctx)
        self.enroll = EnrollTab(self.notebook, self.ctx,
                                on_enrolled=self.users_tab.refresh)
        self.logs_tab = LogsTab(self.notebook, self.ctx)
        self.settings_tab = SettingsTab(
            self.notebook, self.ctx,
            on_camera_change=self._apply_camera_index)

        for tab in (self.dashboard, self.enroll, self.users_tab,
                    self.logs_tab, self.settings_tab):
            self.notebook.add(tab, text=tab.TAB_NAME)

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self._on_tab_changed()
        self._tick_clock()

    # --------------------------------------------------------------- events
    def _tick_clock(self):
        if not self.winfo_exists():
            return
        self.clock.configure(text=datetime.datetime.now()
                             .strftime("%A, %d %b %Y   %H:%M:%S"))
        self.after(1000, self._tick_clock)

    def _on_tab_changed(self, _evt=None):
        tab = self.notebook.nametowidget(self.notebook.select())
        if isinstance(tab, (DashboardTab, EnrollTab)):
            try:
                self.ctx.camera.start()
            except Exception as exc:
                messagebox.showerror("Camera", str(exc), parent=self)
        else:
            self.ctx.camera.stop()

    def _apply_camera_index(self, index):
        try:
            self.ctx.camera.restart(int(index))
        except Exception as exc:
            messagebox.showerror("Camera",
                                 f"Could not open camera {index}:\n{exc}",
                                 parent=self)

    def _logout(self):
        self.ctx.camera.stop()
        self.on_logout()