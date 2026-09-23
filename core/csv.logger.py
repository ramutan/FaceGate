"""
FaceGate — CSV audit trail.

Events are appended to monthly CSV files under data/logs/ so the Logs
tab (and any spreadsheet) can read them. Columns:

    timestamp, name, event, score, details
"""
import csv
import glob
import os
from datetime import datetime

import config

FIELDS = ["timestamp", "name", "event", "score", "details"]


class AuditLogger:
    def __init__(self):
        os.makedirs(config.LOG_DIR, exist_ok=True)

    # -------------------------------------------------------------- write
    def log(self, event, name="-", score="", details=""):
        path = self.month_path()
        new = not os.path.exists(path)
        with open(path, "a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=FIELDS)
            if new:
                writer.writeheader()
            writer.writerow({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "name": name,
                "event": event,
                "score": f"{score:.3f}" if isinstance(score, float) else score,
                "details": details,
            })

    # --------------------------------------------------------------- read
    def month_path(self, when=None) -> str:
        stamp = (when or datetime.now()).strftime("%Y-%m")
        return os.path.join(config.LOG_DIR, f"activity_{stamp}.csv")

    def months(self):
        """All monthly log files, newest first."""
        return sorted(glob.glob(os.path.join(config.LOG_DIR,
                                             "activity_*.csv")), reverse=True)

    def read(self, path):
        if not os.path.exists(path):
            return []
        with open(path, newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    def export(self, rows, dest):
        with open(dest, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)