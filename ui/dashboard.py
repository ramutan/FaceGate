"""FaceGate — Dashboard tab: live recognition + session stats."""
import time
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

import cv2

import config
from ui.widgets import frame_to_photo

GREEN, RED = (46, 204, 113), (231, 76, 60)


class DashboardTab(tk.Frame):
    TAB_NAME = "  Dashboard  "

    def __init__(self, master, ctx):
        super().__init__(master, bg="white")
        self.ctx = ctx
        self.paused = False
        self.last_logged = {}       # key -> time of last CSV row (cooldown)
        self.recognised = 0
        self.unknown = 0
        self.present = {}           # name -> first-seen time
        self._photo = None
        self._build()
        self.after(config.CAMERA_FPS_MS, self._tick)

    # ------------------------------------------------------------------- UI
    def _build(self):
        left = tk.Frame(self, bg="white")
        left.pack(side="left", fill="both", expand=True, padx=12, pady=12)
        self.preview = tk.Label(left, bg="#101418", width=80, height=22)
        self.preview.pack(fill="both", expand=True)

        bar = tk.Frame(left, bg="white")
        bar.pack(fill="x", pady=(8, 0))
        self.pause_btn = tk.Button(bar, text="Pause", relief="flat",
                                   bg="#EDF2F7", padx=10,
                                   command=self._toggle_pause)
        self.pause_btn.pack(side="left")
        tk.Button(bar, text="Export today (CSV)", relief="flat",
                  bg="#EDF2F7", padx=10,
                  command=self._export_today).pack(side="left", padx=8)

        right = tk.Frame(self, bg="white", width=300)
        right.pack(side="right", fill="y", padx=(0, 12), pady=12)
        right.pack_propagate(False)

        stats = tk.LabelFrame(right, text=" Today ", bg="white",
                              font=("Segoe UI", 10, "bold"))
        stats.pack(fill="x")
        self.lbl_rec = self._stat(stats, "Logged recognitions")
        self.lbl_unk = self._stat(stats, "Logged unknowns")

        present = tk.LabelFrame(right, text=" Currently on site ", bg="white",
                                font=("Segoe UI", 10, "bold"))
        present.pack(fill="both", expand=True, pady=(10, 0))
        self.present_tree = ttk.Treeview(present, columns=("name", "since"),
                                         show="headings", height=12)
        self.present_tree.heading("name", text="Name")
        self.present_tree.heading("since", text="First seen")
        self.present_tree.column("name", width=140)
        self.present_tree.column("since", width=110)
        self.present_tree.pack(fill="both", expand=True, pady=(2, 4))
        tk.Button(present, text="Clear list", relief="flat", bg="#EDF2F7",
                  command=self._clear_present).pack(pady=(0, 6))

    @staticmethod
    def _stat(parent, text):
        row = tk.Frame(parent, bg="white")
        row.pack(fill="x", padx=8, pady=4)
        tk.Label(row, text=text, bg="white", fg="#555").pack(side="left")
        lbl = tk.Label(row, text="0", bg="white",
                       font=("Segoe UI", 11, "bold"))
        lbl.pack(side="right")
        return lbl

    # ------------------------------------------------------------ processing
    def _tick(self):
        if not self.winfo_exists():
            return
        if not self.paused:
            frame = self.ctx.camera.read()
            if frame is not None:
                self._process(frame)
        self.after(config.CAMERA_FPS_MS, self._tick)

    def _process(self, frame):
        display = frame.copy()
        faces = self.ctx.engine.detect(frame)
        cooldown = self.ctx.settings.get("log_cooldown")
        now = time.time()

        for face in faces:
            x, y, w, h = map(int, face[0:4])
            feat = self.ctx.engine.feature(frame, face)
            name, score, ok = self.ctx.engine.identify(feat)

            if ok:
                color, label, key = GREEN, f"{name}  {score:.2f}", name
                if now - self.last_logged.get(key, 0.0) >= cooldown:
                    self.ctx.audit.log("RECOGNIZED", name, score, "dashboard")
                    self.last_logged[key] = now
                    self.recognised += 1
                if name not in self.present:
                    self.present[name] = datetime.now().strftime("%H:%M:%S")
                    self.present_tree.insert("", "end", iid=name,
                                             values=(name, self.present[name]))
            else:
                color, label, key = RED, "UNREGISTERED", "__unknown__"
                if now - self.last_logged.get(key, 0.0) >= cooldown:
                    self.ctx.audit.log("UNKNOWN", "-", score, "dashboard")
                    self.last_logged[key] = now
                    self.unknown += 1

            ty = max(y, 26)
            cv2.rectangle(display, (x, y), (x + w, y + h), color, 2)
            cv2.rectangle(display, (x, ty - 26), (x + w, ty), color, -1)
            cv2.putText(display, label, (x + 4, ty - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        self.lbl_rec.configure(text=str(self.recognised))
        self.lbl_unk.configure(text=str(self.unknown))
        self._photo = frame_to_photo(display, config.PREVIEW_WIDTH)
        self.preview.configure(image=self._photo)

    # -------------------------------------------------------------- actions
    def _toggle_pause(self):
        self.paused = not self.paused
        self.pause_btn.configure(text="Resume" if self.paused else "Pause")

    def _clear_present(self):
        self.present.clear()
        self.present_tree.delete(*self.present_tree.get_children())

    def _export_today(self):
        rows = [r for r in self.ctx.audit.read(self.ctx.audit.month_path())
                if r["timestamp"].startswith(datetime.now().strftime("%Y-%m-%d"))]
        if not rows:
            messagebox.showinfo("Export", "No activity recorded today yet.",
                                parent=self)
            return
        dest = filedialog.asksaveasfilename(
            defaultextension=".csv", parent=self,
            initialfile=f"facegate_{datetime.now():%Y-%m-%d}.csv",
            filetypes=[("CSV files", "*.csv")])
        if dest:
            self.ctx.audit.export(rows, dest)
            messagebox.showinfo("Export", f"Exported {len(rows)} rows.",
                                parent=self)