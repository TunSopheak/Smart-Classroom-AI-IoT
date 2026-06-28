import hashlib
import os


# Lightweight demo hashing for Phase 0 + Phase 1.
# For production, replace this with passlib/bcrypt or another strong password-hashing library.
def hash_password(password: str) -> str:
    salt = os.environ.get("SMART_CLASSROOM_DEMO_SALT", "smart-classroom-demo-salt")
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash
