from pathlib import Path

script_path = Path("ai_module/face_recognition/recognize_face.py")
text = script_path.read_text(encoding="utf-8")

if "PROJECT_ROOT = Path(__file__).resolve().parents[2]" not in text:
    text = text.replace(
        "from pathlib import Path\n",
        """from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

""",
    )

script_path.write_text(text, encoding="utf-8")

print("DONE: recognize_face.py can now import app modules.")
