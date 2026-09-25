"""FaceGate — Logs tab: browse, search and export the CSV audit trail."""
import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from core.csv_logger import FIELDS


class LogsTab(tk.Frame):
    TAB_NAME = "  Logs  "

    def __init__(self, master, ctx):
        super().__init__(master, bg="white")
        self.ctx = ctx
        self._build()
        self.refresh_months()

    def _build(self):
        bar = tk.Frame(self, bg="white")
        bar.pack(fill="x", padx=12, pady=(12, 4))
        tk.Label(bar, text="Month:", bg="white").pack(side="left")
        self.cmb_month = ttk.Combobox(bar, state="readonly", width=12)
        self.cmb_month.pack(side="left", padx=6)
        self.cmb_month.bind("<<ComboboxSelected>>",
                            lambda e: self.refresh_rows())

        tk.Label(bar, text="Search:", bg="white").pack(side="left", padx=(14, 0))
        self.var_search = tk.StringVar()
        self.var_search.trace_add("write", lambda *_: self.refresh_rows())
        tk.Entry(bar, textvariable=self.var_search,
                 width=22).pack(side="left", padx=6)

        tk.Button(bar, text="Refresh", relief="flat", bg="#EDF2F7",
                  padx=10, command=self.refresh_months).pack(side="right")
        tk.Button(bar, text="Export…", relief="flat", bg="#2F80ED",
                  fg="white", padx=10, cursor="hand2",
                  command=self._export).pack(side="right", padx=8)
        tk.Button(bar, text="Open folder", relief="flat", bg="#EDF2F7",
                  padx=10, command=self._open_folder).pack(side="right")

        widths = {"timestamp": 160, "name": 170, "event": 110,
                  "score": 70, "details": 220}
        self.tree = ttk.Treeview(self, columns=FIELDS, show="headings")
        for f in FIELDS:
            self.tree.heading(f, text=f.title())
            self.tree.column(f, width=widths[f], anchor="w")
        self.tree.pack(fill="both", expand=True, padx=12, pady=12)

    def refresh_months(self):
        months = [os.path.basename(p)[9:-4]      # activity_YYYY-MM.csv
                  for p in self.ctx.audit.months()]
        self.cmb_month["values"] = months
        if months:
            self.cmb_month.current(0)
        self.refresh_rows()

    def refresh_rows(self):
        self.tree.delete(*self.tree.get_children())
        idx = self.cmb_month.current()
        if idx < 0:
            return
        needle = self.var_search.get().lower()
        for row in self.ctx.audit.read(self.ctx.audit.months()[idx]):
            if needle and needle not in str(row).lower():
                continue
            self.tree.insert("", "end", values=[row.get(f, "") for f in FIELDS])

    def _export(self):
        idx = self.cmb_month.current()
        rows = [] if idx < 0 else self.ctx.audit.read(self.ctx.audit.months()[idx])
        if not rows:
            messagebox.showinfo("Logs", "Nothing to export.", parent=self)
            return
        dest = filedialog.asksaveasfilename(
            defaultextension=".csv", initialfile="facegate_export.csv",
            filetypes=[("CSV files", "*.csv")], parent=self)
        if dest:
            self.ctx.audit.export(rows, dest)
            messagebox.showinfo("Logs", f"Exported {len(rows)} rows.",
                                parent=self)

    def _open_folder(self):
        path = os.path.dirname(self.ctx.audit.month_path())
        try:
            os.startfile(path)                    # Windows
        except AttributeError:
            subprocess.Popen(["xdg-open", path])  # Linux