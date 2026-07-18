import json
import re

def extract_json_objects(text):
    # A more robust way to find all { ... } structures that are valid JSON
    objects = []
    decoder = json.JSONDecoder()
    pos = 0
    while True:
        pos = text.find('{', pos)
        if pos == -1:
            break
        try:
            obj, end_pos = decoder.raw_decode(text[pos:])
            objects.append(obj)
            pos += end_pos
        except json.JSONDecodeError:
            pos += 1
    return objects

# 1. Read existing data from docs/KUROWATCH_YENI_VERI.md
with open("docs/KUROWATCH_YENI_VERI.md", "r", encoding="utf-8") as f:
    existing_content = f.read()

# Find the json block in existing_content
existing_json_match = re.search(r'```json\s*(.*?)\s*```', existing_content, re.DOTALL)
if existing_json_match:
    existing_items = json.loads(existing_json_match.group(1))
else:
    existing_items = []

print(f"Existing items: {len(existing_items)}")

# 2. Read the user snippet
with open("scripts/user_data_snippet.txt", "r", encoding="utf-8") as f:
    snippet_text = f.read()

snippet_items = extract_json_objects(snippet_text)
print(f"Snippet items found: {len(snippet_items)}")

# 3. Merge items by title
# We want to keep the one with the most information
all_items_map = {}

def merge_objects(base, new):
    # Merge keys from new into base if base doesn't have them or new has more info
    for k, v in new.items():
        if k not in base or not base[k]:
            base[k] = v
        elif isinstance(v, list) and isinstance(base[k], list):
            # Merge lists (tags, sites) and deduplicate
            base[k] = list(set(base[k] + v))
        elif isinstance(v, str) and isinstance(base[k], str):
            if len(v) > len(base[k]): # Prefer longer strings (e.g. detailed status or progress)
                base[k] = v
    return base

# First, populate with existing
for item in existing_items:
    title = item.get("title")
    if not title: continue
    all_items_map[title] = item

# Then, update with snippet
for item in snippet_items:
    title = item.get("title")
    if not title: continue
    if title in all_items_map:
        all_items_map[title] = merge_objects(all_items_map[title], item)
    else:
        all_items_map[title] = item

# 4. Convert back to list and sort
final_list = list(all_items_map.values())
# Sort by type then title
final_list.sort(key=lambda x: (x.get("type", ""), x.get("title", "")))

print(f"Final merged items count: {len(final_list)}")

# 5. Write back to docs/KUROWATCH_YENI_VERI.md
output_content = f"""# 📥 KUROWATCH YENI İÇERİK AKTARIMI

```json
{json.dumps(final_list, ensure_ascii=False, indent=2)}
```
"""

with open("docs/KUROWATCH_YENI_VERI.md", "w", encoding="utf-8") as f:
    f.write(output_content)

print("Successfully merged and updated docs/KUROWATCH_YENI_VERI.md")
