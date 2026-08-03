#!/usr/bin/env bash
# Validate Classical Text Spec v1 chapter files.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

errors=0

if [[ ! -f book.yaml ]]; then
  echo "ERROR: book.yaml missing"
  errors=$((errors + 1))
fi

count=$(find chapters -maxdepth 1 -name '[0-9][0-9][0-9].md' 2>/dev/null | wc -l | tr -d ' ')
expected=$(python3 - <<'PY'
import re
from pathlib import Path
t=Path('book.yaml').read_text(encoding='utf-8')
m=re.search(r'^chapter_count:\s*(\d+)\s*$', t, re.M)
print(m.group(1) if m else 81)
PY
)

if [[ "$count" -ne "$expected" ]]; then
  echo "ERROR: expected $expected chapters, found $count"
  errors=$((errors + 1))
fi

required_h1=(
  "Original Text"
  "Textual Variants"
  "Sino-Vietnamese"
  "Literal Translation"
  "Literary Translation"
  "Commentary"
  "Textual Notes"
  "References"
)

python3 - <<'PY'
import re
import sys
from pathlib import Path

required = [
    "Original Text",
    "Textual Variants",
    "Sino-Vietnamese",
    "Literal Translation",
    "Literary Translation",
    "Commentary",
    "Textual Notes",
    "References",
]
allowed_fm = {"chapter", "title", "status", "version"}
errors = 0

for path in sorted(Path("chapters").glob("[0-9][0-9][0-9].md")):
    raw = path.read_bytes()
    if b"\t" in raw:
        print(f"ERROR: {path} contains tab characters")
        errors += 1
    text = raw.decode("utf-8")
    if "\r" in text:
        print(f"ERROR: {path} has CR (expected LF)")
        errors += 1
    for i, line in enumerate(text.splitlines(), 1):
        if line.endswith(" ") or line.endswith("\t"):
            print(f"ERROR: {path}:{i} trailing whitespace")
            errors += 1
            break

    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        print(f"ERROR: {path} missing YAML front matter")
        errors += 1
        continue
    fm, body = m.group(1), m.group(2)
    fields = {}
    for line in fm.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        if ":" not in line:
            print(f"ERROR: {path} bad front matter line: {line!r}")
            errors += 1
            continue
        k, v = line.split(":", 1)
        fields[k.strip()] = v.strip()
    extra = set(fields) - allowed_fm
    missing = allowed_fm - set(fields)
    if extra:
        print(f"ERROR: {path} extra front matter fields: {sorted(extra)}")
        errors += 1
    if missing:
        print(f"ERROR: {path} missing front matter fields: {sorted(missing)}")
        errors += 1

    try:
        n = int(fields.get("chapter", ""))
    except ValueError:
        print(f"ERROR: {path} chapter not int")
        errors += 1
        continue
    if path.name != f"{n:03d}.md":
        print(f"ERROR: {path} filename does not match chapter {n}")
        errors += 1

    headings = re.findall(r"^# (.+)$", body, re.M)
    # Only top-level H1 (lines starting with "# " not "##")
    headings = [h for h in re.findall(r"^#(?!#) (.+)$", body, re.M)]
    if headings != required:
        print(f"ERROR: {path} H1 sections mismatch")
        print(f"  got: {headings}")
        print(f"  want: {required}")
        errors += 1

if errors:
    print(f"FAILED: {errors} error(s)")
    sys.exit(1)
print(f"OK: {len(list(Path('chapters').glob('[0-9][0-9][0-9].md')))} chapters + book.yaml (classical-text/v1)")
PY

if [[ "$errors" -ne 0 ]]; then
  exit 1
fi
