"""
FaceGate — computer-vision engine.

Wraps OpenCV Zoo models so the rest of the app never touches raw cv2
face objects:

    YuNet -> face detection (5 landmarks)
    SFace -> 128-D embeddings + cosine / L2 matching
"""
import os
import pickle
import threading
import urllib.request
from datetime import date

import cv2

import config


def ensure_models() -> None:
    """Download the ONNX models from OpenCV Zoo on first run (~40 MB)."""
    for path, url in ((config.YUNET_MODEL, config.YUNET_URL),
                      (config.SFACE_MODEL, config.SFACE_URL)):
        if not os.path.exists(path):
            print(f"[engine] downloading {os.path.basename(path)} ...")
            urllib.request.urlretrieve(url, path)


class CameraStream:
    """Background frame grabber shared by every screen that needs video.

    `read()` always returns the LATEST frame (or None) so the UI thread
    never blocks on the camera.
    """

    def __init__(self, index: int = config.CAMERA_INDEX):
        self._index = index
        self._cap = None
        self._lock = threading.Lock()
        self._frame = None
        self._running = False
        self._thread = None

    # ------------------------------------------------------------ lifecycle
    def start(self) -> None:
        if self._running:
            return
        if not self._open():
            raise RuntimeError(f"Camera index {self._index} could not be opened")
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        with self._lock:
            self._frame = None

    def restart(self, index: int) -> None:
        """Switch to a different camera index at runtime."""
        self.stop()
        self._index = index
        self._release()
        self.start()

    def _open(self) -> bool:
        if self._cap is None or not self._cap.isOpened():
            self._release()
            self._cap = cv2.VideoCapture(self._index)
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
        return self._cap.isOpened()

    def _release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    # ---------------------------------------------------------- frame access
    def _loop(self) -> None:
        while self._running and self._cap is not None:
            ok, frame = self._cap.read()
            if not ok:
                continue
            if config.MIRROR:
                frame = cv2.flip(frame, 1)
            with self._lock:
                self._frame = frame

    def read(self):
        with self._lock:
            return None if self._frame is None else self._frame.copy()

    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()


class FaceEngine:
    """Detection + embedding + identification against enrolled people."""

    def __init__(self, settings):
        ensure_models()
        self.settings = settings
        self._detector = cv2.FaceDetectorYN.create(
            config.YUNET_MODEL, "",
            (config.FRAME_WIDTH, config.FRAME_HEIGHT),
            config.SCORE_THRESHOLD, config.NMS_THRESHOLD, config.TOP_K,
        )
        self._recognizer = cv2.FaceRecognizerSF.create(config.SFACE_MODEL, "")
        # name -> {"id", "role", "enrolled", "features": [ndarray, ...]}
        self.people = {}
        self.load()

    # -------------------------------------------------------------- vision
    def detect(self, frame):
        self._detector.setInputSize((frame.shape[1], frame.shape[0]))
        _, faces = self._detector.detect(frame)
        return list(faces) if faces is not None else []

    def feature(self, frame, face):
        aligned = self._recognizer.alignCrop(frame, face)
        return self._recognizer.feature(aligned)          # (1, 128) float32

    def identify(self, feature):
        """Return (name, score, is_match) using the configured metric."""
        if not self.people:
            return "Unknown", 0.0, False
        metric = self.settings.get("match_metric", config.MATCH_METRIC)
        cosine = metric == "cosine"
        flag = cv2.FaceRecognizerSF_FR_COSINE if cosine \
            else cv2.FaceRecognizerSF_FR_NORM_L2
        best_name, best = "Unknown", (-1.0 if cosine else float("inf"))
        for name, rec in self.people.items():
            for ref in rec.get("features", []):
                s = float(self._recognizer.match(feature, ref, flag))
                if (cosine and s > best) or (not cosine and s < best):
                    best, best_name = s, name
        thr = self.settings.get(
            "cosine_threshold" if cosine else "l2_threshold",
            config.COSINE_THRESHOLD if cosine else config.L2_THRESHOLD)
        matched = best >= thr if cosine else best <= thr
        return (best_name if matched else "Unknown"), float(best), matched

    # -------------------------------------------------------- people store
    def load(self) -> None:
        if not os.path.exists(config.DB_FILE):
            return
        with open(config.DB_FILE, "rb") as fh:
            raw = pickle.load(fh)
        # Transparently migrate the legacy {"Name": [features]} format.
        for name, val in raw.items():
            if isinstance(val, list):
                val = {"id": "", "role": "Staff",
                       "enrolled": date.today().isoformat(), "features": val}
            self.people[name] = val

    def save(self) -> None:
        with open(config.DB_FILE, "wb") as fh:
            pickle.dump(self.people, fh)

    def enroll(self, name, features, pid="", role="Staff", replace=False):
        exists = name in self.people
        if exists and not replace:
            raise ValueError(f"'{name}' is already enrolled")
        rec = self.people.get(name) or {
            "id": "", "role": "Staff",
            "enrolled": date.today().isoformat(), "features": []}
        if exists and replace:
            rec["features"] = []
        rec["id"] = pid or rec.get("id", "")
        rec["role"] = role or rec.get("role", "Staff")
        rec["features"].extend(features)
        self.people[name] = rec
        self.save()
        return len(rec["features"])

    def delete(self, name) -> None:
        self.people.pop(name, None)
        self.save()

    def sample_count(self, name) -> int:
        return len(self.people.get(name, {}).get("features", []))