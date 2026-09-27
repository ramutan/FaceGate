"""
FaceGate — central configuration.

Every tunable knob lives here so behaviour can be changed without
touching application logic.
"""
import os

# ------------------------------------------------------------------ paths --
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODEL_DIR = os.path.join(DATA_DIR, "models")
LOG_DIR = os.path.join(DATA_DIR, "logs")

DB_FILE = os.path.join(DATA_DIR, "face_database.pkl")
ACCOUNTS_FILE = os.path.join(DATA_DIR, "accounts.pkl")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.pkl")

YUNET_MODEL = os.path.join(MODEL_DIR, "face_detection_yunet_2023mar.onnx")
SFACE_MODEL = os.path.join(MODEL_DIR, "face_recognition_sface_2021dec.onnx")

YUNET_URL = ("https://github.com/opencv/opencv_zoo/raw/main/models/"
             "face_detection_yunet/face_detection_yunet_2023mar.onnx")
SFACE_URL = ("https://github.com/opencv/opencv_zoo/raw/main/models/"
             "face_recognition_sface/face_recognition_sface_2021dec.onnx")

# ----------------------------------------------------------- recognition --
COSINE_THRESHOLD = 0.363      # cosine score >= this -> SAME person
L2_THRESHOLD = 1.128          # L2 distance <= this  -> SAME person
MATCH_METRIC = "cosine"       # "cosine" | "l2"

# ---------------------------------------------------------------- camera --
CAMERA_INDEX = 0
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
MIRROR = True

# ------------------------------------------------------------- detection --
SCORE_THRESHOLD = 0.8
NMS_THRESHOLD = 0.3
TOP_K = 5000

# ------------------------------------------------------------ enrollment --
SAMPLES_PER_ENROLLMENT = 5
SAMPLE_INTERVAL_MS = 250

# --------------------------------------------------------------- security --
PIN_LENGTH = 6
DEFAULT_ADMIN_PIN = "123456"   # !! change immediately on first login
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 30

# -------------------------------------------------------------------- ui --
WINDOW_TITLE = "FaceGate — Face Recognition Console"
LOGIN_SIZE = "400x640"
APP_SIZE = "1200x740"
CAMERA_FPS_MS = 33             # UI refresh period (~30 fps)
PREVIEW_WIDTH = 640            # px width of embedded camera previews

# A person's recognition is written to the CSV at most once per period.
LOG_COOLDOWN_SECONDS = 30

for _d in (DATA_DIR, MODEL_DIR, LOG_DIR):
    os.makedirs(_d, exist_ok=True)