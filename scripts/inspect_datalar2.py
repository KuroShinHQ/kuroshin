import re

file_path = "kuroshin-downloads/datalar2.md"

with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

# Print lines that look like headers or have list markers or anime/manga keywords
for idx, line in enumerate(lines):
    if line.strip().startswith("#") or "Omniscient" in line or "Trashero" in line or "KuroWatch" in line or "izleme_profili" in line:
        if idx < 100 or idx > len(lines) - 200 or len(line.strip()) > 10:
            print(f"Line {idx+1}: {line.strip()[:120]}")
