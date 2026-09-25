"""FaceGate — Users tab: manage enrolled identities."""
import tkinter as tk
from tkinter import messagebox, ttk


class UsersTab(tk.Frame):
    TAB_NAME = "  Users  "

    def __init__(self, master, ctx):
        super().__init__(master, bg="white")
        self.ctx = ctx
        self._build()
        self.refresh()

    def _build(self):
        bar = tk.Frame(self, bg="white")
        bar.pack(fill="x", padx=12, pady=(12, 4))
        tk.Button(bar, text="Delete selected", relief="flat", bg="#E5484D",
                  fg="white", padx=10, cursor="hand2",
                  command=self._delete).pack(side="left")
        tk.Button(bar, text="Refresh", relief="flat", bg="#EDF2F7",
                  padx=10, command=self.refresh).pack(side="left", padx=8)

        cols = (("name", "Name", 220), ("id", "ID", 130),
                ("role", "Role", 100), ("samples", "Samples", 80),
                ("enrolled", "Enrolled", 120))
        self.tree = ttk.Treeview(self, columns=[c[0] for c in cols],
                                 show="headings")
        for cid, text, width in cols:
            self.tree.heading(cid, text=text)
            self.tree.column(cid, width=width, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=12, pady=12)

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for name, rec in sorted(self.ctx.engine.people.items()):
            self.tree.insert("", "end", iid=name,
                             values=(name, rec.get("id", "-") or "-",
                                     rec.get("role", "-"),
                                     len(rec.get("features", [])),
                                     rec.get("enrolled", "-")))

    def _delete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Users", "Select a person first.", parent=self)
            return
        name = sel[0]
        if messagebox.askyesno("Users",
                               f"Delete '{name}' and all face samples?",
                               parent=self):
            self.ctx.engine.delete(name)
            self.ctx.audit.log("DELETE", name)
            self.refresh()