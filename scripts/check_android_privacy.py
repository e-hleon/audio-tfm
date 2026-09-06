"""Static privacy checks for the Android module; exits non-zero on regressions."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "android"
files = [p for p in ROOT.rglob("*") if p.is_file() and p.suffix in {".xml", ".kt", ".kts"}]
text = "\n".join(p.read_text(encoding="utf-8") for p in files)
forbidden = ("READ_EXTERNAL_STORAGE", "WRITE_EXTERNAL_STORAGE", "MANAGE_EXTERNAL_STORAGE")
errors = [f"forbidden permission: {item}" for item in forbidden if item in text]
if "OPENAI_API_KEY" in text:
    errors.append("OPENAI_API_KEY appears under android/")
release_manifest = ROOT / "app/src/main/AndroidManifest.xml"
if "usesCleartextTraffic=\"true\"" in release_manifest.read_text(encoding="utf-8"):
    errors.append("cleartext traffic is enabled in the main manifest")
if errors:
    print("\n".join(errors), file=sys.stderr)
    raise SystemExit(1)
print("Android privacy checks passed")
