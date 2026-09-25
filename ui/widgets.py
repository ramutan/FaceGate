"""FaceGate — shared UI helpers: frame painting + guided face capture."""
import time
import tkinter as tk

import cv2
from PIL import Image, ImageTk

import config


def frame_to_photo(frame_bgr, width):
    """Resize + convert a BGR frame into a Tkinter PhotoImage."""
    h, w = frame_bgr.shape[:2]
    resized = cv2.resize(frame_bgr, (width, int(h * width / float(w))))
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    return ImageTk.PhotoImage(Image.fromarray(rgb))


class FaceCapture:
    """Collects N clean single-face samples from the shared camera while
    painting a live preview with guidance overlays. Used by the Enrollment
    tab and the Face-Unlock enrollment in Settings."""

    def __init__(self, ctx, preview, n_samples, on_done,
                 on_status=lambda msg: None,
                 on_progress=lambda done, total: None):
        self.ctx = ctx
        self.preview = preview
        self.n = n_samples
        self.on_done = on_done
        self.on_status = on_status
        self.on_progress = on_progress
        self.features = []
        self.active = False
        self._job = None
        self._next_at = 0.0

    def start(self):
        self.features = []
        self.active = True
        self._next_at = 0.0
        self.ctx.camera.start()
        self.on_status("Look straight at the camera…")
        self._tick()

    def cancel(self):
        self.active = False
        if self._job:
            self.preview.after_cancel(self._job)
            self._job = None
        self.on_status("Capture cancelled.")

    # ---------------------------------------------------------- internals
    def _tick(self):
        if not self.active or not self.preview.winfo_exists():
            self.active = False
            return
        frame = self.ctx.camera.read()
        if frame is None:
            self.on_status("Waiting for camera…")
        else:
            display = frame.copy()
            faces = self.ctx.engine.detect(frame)
            if len(faces) == 1:
                x, y, w, h = map(int, faces[0][0:4])
                cv2.rectangle(display, (x, y), (x + w, y + h), (0, 200, 0), 2)
                if time.time() >= self._next_at and len(self.features) < self.n:
                    self.features.append(self.ctx.engine.feature(frame, faces[0]))
                    self._next_at = time.time() + config.SAMPLE_INTERVAL_MS / 1000.0
                    self.on_progress(len(self.features), self.n)
                cv2.putText(display,
                            f"Sample {min(len(self.features) + 1, self.n)}/{self.n}",
                            (x, max(y - 10, 22)), cv2.FONT_HERSHEY_SIMPLEX,
                            0.7, (0, 200, 0), 2)
                self.on_status("Hold still…"
                               if len(self.features) < self.n else "Finishing…")
            else:
                msg = ("Make sure ONLY ONE face is visible"
                       if len(faces) > 1 else "No face detected")
                cv2.putText(display, msg, (20, 44), cv2.FONT_HERSHEY_SIMPLEX,
                            0.8, (0, 0, 255), 2)
                self.on_status(msg)
            self._paint(display)

        if len(self.features) >= self.n:
            self.active = False
            self.on_done(self.features)
            return
        self._job = self.preview.after(config.CAMERA_FPS_MS, self._tick)

    def _paint(self, frame):
        photo = frame_to_photo(frame, config.PREVIEW_WIDTH)
        self.preview.configure(image=photo)
        self.preview.image = photo