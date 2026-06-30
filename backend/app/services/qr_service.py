from pathlib import Path
import re
import hmac
import hashlib

import qrcode

from app.core.auth import AUTH_SECRET_KEY


SIGNED_QR_PREFIX = "SCQR"
SIGNED_QR_VERSION = "v1"
SIGNATURE_LENGTH = 16


def safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
    return cleaned or "qr_code"


def _sign_student_id(stu_id: str) -> str:
    return hmac.new(
        AUTH_SECRET_KEY.encode("utf-8"),
        stu_id.strip().upper().encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:SIGNATURE_LENGTH]


def build_student_qr_code(stu_id: str) -> str:
    clean_stu_id = stu_id.strip().upper()
    return f"{SIGNED_QR_PREFIX}:{SIGNED_QR_VERSION}:{clean_stu_id}:{_sign_student_id(clean_stu_id)}"


def parse_signed_student_qr(qr_value: str) -> str | None:
    parts = qr_value.strip().split(":")
    if len(parts) != 4:
        return None

    prefix, version, stu_id, signature = parts
    clean_stu_id = stu_id.strip().upper()

    if prefix != SIGNED_QR_PREFIX or version != SIGNED_QR_VERSION or not clean_stu_id:
        return None

    expected_signature = _sign_student_id(clean_stu_id)
    if not hmac.compare_digest(signature, expected_signature):
        return None

    return clean_stu_id


def generate_qr_image(qr_value: str, output_dir: Path, filename: str) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / filename

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_value)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(file_path)

    return str(file_path)


def generate_student_qr_image(stu_id: str, qr_code: str) -> str:
    output_dir = Path("app/static/generated_qr")
    filename = f"{safe_filename(stu_id)}.png"
    file_path = generate_qr_image(qr_code, output_dir, filename)

    # Convert Windows or Linux file path to browser URL.
    normalized = str(file_path).replace("\\", "/")

    if normalized.startswith("app/static/"):
        return "/" + normalized.replace("app/static/", "static/", 1)

    return normalized
