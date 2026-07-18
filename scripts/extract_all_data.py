import re
import json
import os

file_path = "kuroshin-downloads/datalar2.md"
output_path = "docs/KUROWATCH_YENI_VERI.md"

if not os.path.exists("docs"):
    os.makedirs("docs")

with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

# Let's find all text blocks between [ and ] that could be JSON arrays
# We can find all matches of '[' to ']' but some might be nested.
# Let's use re.finditer or a custom scanner to find top-level arrays.

all_items = []

# A naive approach to find all json arrays: find all string indices of '[' and try to find matching ']'
# or look for standard JSON blocks.
# Let's search for lines starting with [ and find until a line with ]

# Alternatively, let's parse any string that matches standard json array structure.
# Let's find all occurrences of `[` and try to decode an array from that position.

decoder = json.JSONDecoder()
pos = 0
while True:
    pos = content.find('[', pos)
    if pos == -1:
        break
    try:
        obj, end_pos = decoder.raw_decode(content[pos:])
        if isinstance(obj, list):
            print(f"Found JSON array with {len(obj)} items at position {pos}")
            all_items.extend(obj)
            pos += end_pos
        else:
            pos += 1
    except json.JSONDecodeError:
        pos += 1

print(f"Total items extracted: {len(all_items)}")

# Let's de-duplicate by title if there are duplicates
seen_titles = set()
unique_items = []
for item in all_items:
    if isinstance(item, dict) and "title" in item:
        title = item["title"]
        if title == "İçerik Adı":
            continue
        if title not in seen_titles:
            seen_titles.add(title)
            unique_items.append(item)
    else:
        unique_items.append(item)

print(f"Unique items count: {len(unique_items)}")

# Now write out to docs/KUROWATCH_YENI_VERI.md
output_content = f"""# 📥 KUROWATCH YENI İÇERİK AKTARIMI

```json
{json.dumps(unique_items, ensure_ascii=False, indent=2)}
```
"""

with open(output_path, "w", encoding="utf-8") as f:
    f.write(output_content)

print("Successfully written to docs/KUROWATCH_YENI_VERI.md")
