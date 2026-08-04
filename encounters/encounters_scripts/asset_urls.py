#!/usr/bin/env python3
"""
asset_urls.py — Shared helpers for resolving encounter image_url filenames to
their real URL on the Devocionales-assets GitHub repo (SOT).

Extracted from verify_image_urls.py so app_preview.py can reuse the same
encounter_id lookup and URL-building instead of re-deriving it.
"""

import json
from dataclasses import dataclass
from pathlib import Path

ASSETS_REPO_RAW_BASE = "https://raw.githubusercontent.com/develop4God/Devocionales-assets/main/images/encounters"


@dataclass(frozen=True)
class ImageReference:
    encounter_id: str
    filename: str

    def url(self, ext: str | None = None) -> str:
        name = self.filename
        if ext:
            name = f"{Path(name).stem}.{ext.lstrip('.')}"
        return f"{ASSETS_REPO_RAW_BASE}/{self.encounter_id}/{name}"


class EncounterIndexReader:
    """Reads index.json to map encounter file -> encounter_id (asset folder name)."""

    def __init__(self, encounters_dir: Path):
        self._encounters_dir = encounters_dir

    def build_file_to_encounter_id(self) -> dict:
        index_path = self._encounters_dir / "index.json"
        data = json.loads(index_path.read_text(encoding="utf-8"))

        file_to_id = {}
        for encounter in data["encounters"]:
            encounter_id = encounter["id"]
            if "intro_image" in encounter:
                file_to_id[("index.json", encounter["intro_image"])] = encounter_id
            for lang_file in encounter.get("files", {}).values():
                file_to_id[lang_file] = encounter_id
        return file_to_id

    def encounter_id_for(self, json_filename: str) -> str:
        return self.build_file_to_encounter_id().get(json_filename)
