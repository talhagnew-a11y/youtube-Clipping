"""Checks required portable clipping components; optional cloud/voice tools are excluded."""
import importlib.metadata as meta
import importlib.util
import os
from pathlib import Path
import shutil
import sys

root = Path(__file__).resolve().parent.parent
checks = [
    ("Bundled Python", Path(sys.executable).resolve().is_relative_to(root / "python")),
    ("FFmpeg", bool(shutil.which("ffmpeg"))),
    ("FFprobe", bool(shutil.which("ffprobe"))),
    ("Node", bool(shutil.which("node"))),
    ("Caption renderer", (root / "workspace/remotion-video/node_modules/@remotion/cli").is_dir()),
    ("Whisper", importlib.util.find_spec("stable_whisper") is not None),
    ("OpenCV", importlib.util.find_spec("cv2") is not None),
    ("Browser UI", importlib.util.find_spec("gradio") is not None),
    ("Portable Ollama", (root / "ollama/ollama.exe").is_file()),
    ("Qwen model", (root / "models/ollama/manifests/registry.ollama.ai/library/qwen2.5/1.5b").is_file()),
    ("Whisper base model", (root / "cache/whisper/base.pt").is_file()),
]
print("ShortsFlow portable check")
print("Launch folder:", os.environ["SHORTSFLOW_HOME"])
for label, ok in checks:
    print(("OK   " if ok else "FAIL ") + label)
for package in ("shortsflow", "torch", "stable-ts"):
    print(package + ": " + meta.version(package))
failed = sum(not ok for _, ok in checks)
print("Ready for local clipping." if not failed else f"{failed} required component(s) missing.")
raise SystemExit(1 if failed else 0)

