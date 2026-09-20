from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BLOCKED = [
    "Based Nut",
    "basednut",
    "private personal Hivemind",
]
SCAN = [ROOT / "README.md", ROOT / "docs", ROOT / "config"]
errors = []
for base in SCAN:
    paths = [base] if base.is_file() else list(base.rglob("*"))
    for path in paths:
        if not path.is_file() or path.suffix.lower() not in {".md", ".json", ".yaml", ".yml"}:
            continue
        text = path.read_text(encoding="utf-8")
        for phrase in BLOCKED:
            if phrase.lower() in text.lower():
                errors.append(f"{path.relative_to(ROOT)} contains blocked public-copy phrase: {phrase!r}")
if errors:
    print("\n".join(errors))
    sys.exit(1)
print("public copy audit: PASS")
