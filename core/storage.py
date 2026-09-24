"""
FaceGate — accounts & runtime settings.

AccountStore  : salted PBKDF2-SHA256 PIN hashes (plain PINs never stored)
SettingsStore : user-tunable values persisted across runs
"""
import hashlib
import os
import pickle
import secrets

import config

_ITERATIONS = 120_000


def _hash_pin(pin: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, _ITERATIONS).hex()


class AccountStore:
    """Single-admin console; supports extra accounts if you extend the UI."""

    def __init__(self):
        self.accounts = {}
        self._load()

    def _load(self):
        if os.path.exists(config.ACCOUNTS_FILE):
            with open(config.ACCOUNTS_FILE, "rb") as fh:
                self.accounts = pickle.load(fh)
        else:
            self.create("admin", config.DEFAULT_ADMIN_PIN)
            self._save()

    def _save(self):
        with open(config.ACCOUNTS_FILE, "wb") as fh:
            pickle.dump(self.accounts, fh)

    def create(self, username: str, pin: str) -> None:
        salt = secrets.token_bytes(16)
        self.accounts[username] = {"salt": salt,
                                   "pin": _hash_pin(pin, salt),
                                   "face_unlock": False}
        self._save()

    def verify(self, username: str, pin: str) -> bool:
        acc = self.accounts.get(username)
        if not acc:
            return False
        return secrets.compare_digest(acc["pin"], _hash_pin(pin, acc["salt"]))

    def change_pin(self, username: str, new_pin: str) -> None:
        acc = self.accounts[username]
        acc["salt"] = secrets.token_bytes(16)
        acc["pin"] = _hash_pin(new_pin, acc["salt"])
        self._save()

    def face_unlock_enabled(self, username: str) -> bool:
        return bool(self.accounts.get(username, {}).get("face_unlock"))

    def set_face_unlock(self, username: str, enabled: bool) -> None:
        self.accounts[username]["face_unlock"] = bool(enabled)
        self._save()


_DEFAULTS = {
    "cosine_threshold": config.COSINE_THRESHOLD,
    "l2_threshold": config.L2_THRESHOLD,
    "match_metric": config.MATCH_METRIC,
    "camera_index": config.CAMERA_INDEX,
    "log_cooldown": config.LOG_COOLDOWN_SECONDS,
}


class SettingsStore:
    def __init__(self):
        self.values = dict(_DEFAULTS)
        self.load()

    def load(self):
        if os.path.exists(config.SETTINGS_FILE):
            try:
                with open(config.SETTINGS_FILE, "rb") as fh:
                    self.values.update(pickle.load(fh))
            except Exception:
                pass  # corrupted file -> fall back to defaults

    def save(self):
        with open(config.SETTINGS_FILE, "wb") as fh:
            pickle.dump(self.values, fh)

    def get(self, key, default=None):
        return self.values.get(key, _DEFAULTS.get(key, default))

    def set(self, key, value):
        self.values[key] = value

    def reset(self):
        self.values = dict(_DEFAULTS)
        self.save()