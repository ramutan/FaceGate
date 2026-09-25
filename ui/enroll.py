"""FaceGate — Enrollment tab: guided capture of face samples."""
import tkinter as tk
from tkinter import messagebox, ttk

import config
from ui.widgets import FaceCapture

ROLES = ("Admin", "Staff", "Visitor")


class EnrollTab(tk.Frame):
    TAB_NAME = "  Enrollment  "

    def __init__(self, master, ctx, on_enrolled=lambda: None):
        super().__init__(master, bg="white")
        self.ctx = ctx
        self.on_enrolled = on_enrolled
        self.capture = None
        self.replace = False
        self._build()

    def _build(self):
        form = tk.Frame(self, bg="white")
        form.pack(side="left", fill="both", expand=True, padx=16, pady=16)

        tk.Label(form, text="Register a new face",
                 font=("Segoe UI", 15, "bold"),
                 bg="white").pack(anchor="w", pady=(0, 14))

        def field(label):
            row = tk.Frame(form, bg="white")
            row.pack(fill="x", pady=4)
            tk.Label(row, text=label, width=16, anchor="w",
                     bg="white").pack(side="left")
            ent = tk.Entry(row, font=("Segoe UI", 11))
            ent.pack(side="left", fill="x", expand=True)
            return ent

        self.ent_name = field("Full name")
        self.ent_id = field("ID / Employee no.")

        row = tk.Frame(form, bg="white")
        row.pack(fill="x", pady=4)
        tk.Label(row, text="Role", width=16, anchor="w",
                 bg="white").pack(side="left")
        self.cmb_role = ttk.Combobox(row, values=ROLES, state="readonly",
                                     width=18)
        self.cmb_role.current(1)
        self.cmb_role.pack(side="left")

        self.progress = ttk.Progressbar(form, maximum=config.SAMPLES_PER_ENROLLMENT,
                                        length=300)
        self.progress.pack(anchor="w", pady=(20, 2))
        self.status = tk.Label(form, text="Fill in the details, then start capture.",
                               bg="white", fg="#555")
        self.status.pack(anchor="w")

        btns = tk.Frame(form, bg="white")
        btns.pack(pady=16)
        self.start_btn = tk.Button(btns, text="Start capture", relief="flat",
                                   bg="#2F80ED", fg="white", padx=16, pady=6,
                                   cursor="hand2", command=self._start)
        self.start_btn.pack(side="left")
        self.cancel_btn = tk.Button(btns, text="Cancel", relief="flat",
                                    bg="#EDF2F7", padx=16, pady=6,
                                    state="disabled", command=self._cancel)
        self.cancel_btn.pack(side="left", padx=8)

        self.preview = tk.Label(self, bg="#101418", width=64, height=18)
        self.preview.pack(side="right", fill="both", expand=True,
                          padx=16, pady=16)

    # -------------------------------------------------------------- actions
    def _start(self):
        name = self.ent_name.get().strip()
        if not name:
            messagebox.showwarning("Enrollment", "Please enter a name.",
                                   parent=self)
            return
        self.replace = name in self.ctx.engine.people
        if self.replace and not messagebox.askyesno(
                "Enrollment",
                f"'{name}' already exists with "
                f"{self.ctx.engine.sample_count(name)} samples.\n"
                f"Replace them with new samples?", parent=self):
            return

        self.start_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.progress["value"] = 0
        self.capture = FaceCapture(
            self.ctx, self.preview, config.SAMPLES_PER_ENROLLMENT,
            on_done=self._finish,
            on_status=lambda m: self.status.configure(text=m, fg="#555"),
            on_progress=lambda i, n: self.progress.configure(value=i))
        self.capture.start()

    def _cancel(self):
        if self.capture:
            self.capture.cancel()
        self._reset()

    def _finish(self, features):
        name = self.ent_name.get().strip()
        try:
            total = self.ctx.engine.enroll(
                name, features, pid=self.ent_id.get().strip(),
                role=self.cmb_role.get(), replace=self.replace)
            self.ctx.audit.log("ENROLL", name, details=f"{len(features)} samples")
            messagebox.showinfo("Enrollment",
                                f"Enrolled '{name}' — {total} samples stored.",
                                parent=self)
            self.on_enrolled()
        except ValueError as exc:
            messagebox.showerror("Enrollment", str(exc), parent=self)
        self._reset()

    def _reset(self):
        self.start_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        self.progress["value"] = 0
        self.status.configure(text="Ready.", fg="#555")