"""FaceGate — Settings tab: recognition tuning, camera, security."""
import tkinter as tk
from tkinter import messagebox, ttk

import config
from ui.widgets import FaceCapture


class SettingsTab(tk.Frame):
    TAB_NAME = "  Settings  "

    def __init__(self, master, ctx, on_camera_change=lambda i: None):
        super().__init__(master, bg="white")
        self.ctx = ctx
        self.on_camera_change = on_camera_change
        self._build()
        self._load()

    def _build(self):
        outer = tk.Frame(self, bg="white")
        outer.pack(fill="both", expand=True, padx=16, pady=16)

        # ---------------------------------------------------- recognition
        rec = tk.LabelFrame(outer, text=" Recognition ", bg="white",
                            font=("Segoe UI", 10, "bold"))
        rec.pack(fill="x")
        tk.Label(rec, text="Metric", bg="white").grid(
            row=0, column=0, sticky="w", padx=8, pady=4)
        self.cmb_metric = ttk.Combobox(rec, state="readonly", width=10,
                                       values=("cosine", "l2"))
        self.cmb_metric.grid(row=0, column=1, sticky="w")

        tk.Label(rec, text="Cosine threshold", bg="white").grid(
            row=1, column=0, sticky="w", padx=8)
        self.scale_cos = tk.Scale(rec, from_=0.20, to=0.60, resolution=0.001,
                                  orient="horizontal", length=280,
                                  bg="white", highlightthickness=0)
        self.scale_cos.grid(row=1, column=1, sticky="w")

        tk.Label(rec, text="L2 threshold", bg="white").grid(
            row=2, column=0, sticky="w", padx=8)
        self.scale_l2 = tk.Scale(rec, from_=0.80, to=1.60, resolution=0.001,
                                 orient="horizontal", length=280,
                                 bg="white", highlightthickness=0)
        self.scale_l2.grid(row=2, column=1, sticky="w")

        tk.Label(rec, text="Log cooldown (s)", bg="white").grid(
            row=3, column=0, sticky="w", padx=8)
        self.spin_cooldown = tk.Spinbox(rec, from_=5, to=600, width=6)
        self.spin_cooldown.grid(row=3, column=1, sticky="w", pady=4)

        tk.Button(rec, text="Save recognition settings", relief="flat",
                  bg="#2F80ED", fg="white", padx=12, cursor="hand2",
                  command=self._save_recognition).grid(
            row=4, column=1, sticky="w", padx=4, pady=8)

        # ---------------------------------------------------------- camera
        cam = tk.LabelFrame(outer, text=" Camera ", bg="white",
                            font=("Segoe UI", 10, "bold"))
        cam.pack(fill="x", pady=(12, 0))
        tk.Label(cam, text="Camera index", bg="white").pack(
            side="left", padx=8, pady=8)
        self.spin_cam = tk.Spinbox(cam, from_=0, to=8, width=4)
        self.spin_cam.pack(side="left")
        tk.Button(cam, text="Apply", relief="flat", bg="#EDF2F7", padx=10,
                  command=self._apply_camera).pack(side="left", padx=8)

        # -------------------------------------------------------- security
        sec = tk.LabelFrame(outer, text=" Security ", bg="white",
                            font=("Segoe UI", 10, "bold"))
        sec.pack(fill="x", pady=(12, 0))

        def pin_row(label, row):
            frame = tk.Frame(sec, bg="white")
            frame.grid(row=row, column=0, sticky="w", padx=8, pady=3)
            tk.Label(frame, text=label, width=14, anchor="w",
                     bg="white").pack(side="left")
            return tk.Entry(frame, show="•", width=16)

        self.ent_cur = pin_row("Current PIN", 0)
        self.ent_new = pin_row("New PIN", 1)
        self.ent_conf = pin_row("Confirm PIN", 2)
        tk.Button(sec, text="Change PIN", relief="flat", bg="#2F80ED",
                  fg="white", padx=12, cursor="hand2",
                  command=self._change_pin).grid(row=3, column=0,
                                                 sticky="w", padx=8, pady=6)

        row4 = tk.Frame(sec, bg="white")
        row4.grid(row=4, column=0, sticky="w", padx=8, pady=6)
        self.var_face_unlock = tk.BooleanVar()
        tk.Checkbutton(row4, text="Enable Face Unlock for 'admin'",
                       variable=self.var_face_unlock, bg="white",
                       command=self._toggle_face_unlock).pack(side="left")
        tk.Button(row4, text="Enroll admin face…", relief="flat",
                  bg="#EDF2F7", padx=10,
                  command=self._enroll_admin_face).pack(side="left", padx=10)

    # --------------------------------------------------------------- loading
    def _load(self):
        s = self.ctx.settings
        self.cmb_metric.set(s.get("match_metric"))
        self.scale_cos.set(s.get("cosine_threshold"))
        self.scale_l2.set(s.get("l2_threshold"))
        self.spin_cooldown.delete(0, "end")
        self.spin_cooldown.insert(0, s.get("log_cooldown"))
        self.spin_cam.delete(0, "end")
        self.spin_cam.insert(0, s.get("camera_index"))
        self.var_face_unlock.set(self.ctx.accounts.face_unlock_enabled("admin"))

    # --------------------------------------------------------------- actions
    def _save_recognition(self):
        s = self.ctx.settings
        s.set("match_metric", self.cmb_metric.get())
        s.set("cosine_threshold", float(self.scale_cos.get()))
        s.set("l2_threshold", float(self.scale_l2.get()))
        s.set("log_cooldown", int(self.spin_cooldown.get()))
        s.save()
        self.ctx.audit.log("SETTINGS", details="recognition updated")
        messagebox.showinfo("Settings", "Recognition settings saved.",
                            parent=self)

    def _apply_camera(self):
        idx = int(self.spin_cam.get())
        self.ctx.settings.set("camera_index", idx)
        self.ctx.settings.save()
        self.on_camera_change(idx)

    def _change_pin(self):
        cur, new, conf = (self.ent_cur.get(), self.ent_new.get(),
                          self.ent_conf.get())
        if not self.ctx.accounts.verify("admin", cur):
            messagebox.showerror("Security", "Current PIN is incorrect.",
                                 parent=self)
            return
        if len(new) != config.PIN_LENGTH or not new.isdigit():
            messagebox.showerror(
                "Security", f"New PIN must be exactly {config.PIN_LENGTH} digits.",
                parent=self)
            return
        if new != conf:
            messagebox.showerror("Security", "PINs do not match.", parent=self)
            return
        self.ctx.accounts.change_pin("admin", new)
        self.ctx.audit.log("PIN_CHANGED", "admin")
        for ent in (self.ent_cur, self.ent_new, self.ent_conf):
            ent.delete(0, "end")
        messagebox.showinfo("Security", "PIN changed successfully.", parent=self)

    def _toggle_face_unlock(self):
        if self.var_face_unlock.get() and "admin" not in self.ctx.engine.people:
            messagebox.showwarning("Security",
                                   "Enroll the admin face first.", parent=self)
            self.var_face_unlock.set(False)
            return
        self.ctx.accounts.set_face_unlock("admin", self.var_face_unlock.get())

    def _enroll_admin_face(self):
        win = tk.Toplevel(self)
        win.title("Enroll admin face")
        preview = tk.Label(win, bg="black", width=64, height=18)
        preview.pack(padx=12, pady=12)
        status = tk.Label(win, text="Capturing 3 samples…")
        status.pack(pady=(0, 12))

        def done(features):
            self.ctx.engine.enroll("admin", features, role="Admin",
                                   replace=True)
            self.var_face_unlock.set(True)
            self.ctx.accounts.set_face_unlock("admin", True)
            self.ctx.audit.log("ENROLL", "admin", details="face unlock")
            messagebox.showinfo(
                "Security", "Admin face enrolled — Face Unlock enabled.",
                parent=self)
            win.destroy()

        FaceCapture(self.ctx, preview, 3, on_done=done,
                    on_status=lambda m: status.configure(text=m)).start()