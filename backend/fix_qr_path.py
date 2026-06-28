from pathlib import Path

print("Fixing QR image browser path...")

Path("app/services/qr_service.py").write_text(r'''from pathlib import Path
import re

import qrcode


def safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
    return cleaned or "qr_code"


def build_student_qr_code(stu_id: str) -> str:
    return f"SC-STUDENT-{stu_id.strip().upper()}"


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
''', encoding="utf-8")

print("DONE: qr_service.py fixed.")
