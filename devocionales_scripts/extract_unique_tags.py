import json

with open("Devocional_year_2026_en_KJV.json", "r", encoding="utf-8") as f:
    data = json.load(f)

tags = set()
for lang_data in data.get("data", {}).values():
    for date_entries in lang_data.values():
        for entry in date_entries:
            tags.update(entry.get("tags") or [])

for tag in sorted(tags):
    print(tag)
