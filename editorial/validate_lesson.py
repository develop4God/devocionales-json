#!/usr/bin/env python3
"""
validate_lesson.py

Valida un documento maestro de lección (unit + lesson) contra
schema/lesson.schema.json, y opcionalmente genera los dos archivos
de salida separados: <id>_alumno.json y <id>_maestro.json.

Uso:
    python validate_lesson.py lessons/lesson_social_media_01.json
    python validate_lesson.py lessons/lesson_social_media_01.json --split
    python validate_lesson.py lessons/lesson_social_media_01.json --split --out exports/
"""

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft7Validator

SCHEMA_PATH = Path(__file__).parent / "lesson.schema.json"


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate(doc: dict, schema: dict) -> list[str]:
    """Devuelve una lista de mensajes de error (vacía si el documento es válido)."""
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
    messages = []
    for err in errors:
        location = " -> ".join(str(p) for p in err.path) or "(raíz)"
        messages.append(f"[{location}] {err.message}")
    return messages


def split_lesson(doc: dict) -> tuple[dict, dict]:
    """Genera las versiones alumno y maestro a partir del documento maestro."""
    lesson = doc["lesson"]
    base = {
        "lesson_id": lesson["id"],
        "unit_id": lesson["unit_id"],
        "title": lesson["title"],
        "objective": lesson["objective"],
        "bible_reading": lesson["shared"]["bible_reading"],
        "key_verse": lesson["shared"]["key_verse"],
        "hook": lesson["shared"]["hook"],
        "metadata": lesson["metadata"],
    }

    alumno = dict(base)
    alumno["content"] = lesson["student_content"]

    maestro = dict(base)
    maestro["content"] = lesson["teacher_content"]
    # El maestro recibe también el contenido del alumno, como referencia
    # para saber qué está trabajando el grupo esa semana.
    maestro["student_reference"] = lesson["student_content"]

    return alumno, maestro


def main():
    parser = argparse.ArgumentParser(description="Valida y opcionalmente separa una lección.")
    parser.add_argument("lesson_file", type=Path, help="Ruta al JSON maestro de la lección")
    parser.add_argument("--split", action="store_true", help="Generar también los archivos alumno/maestro")
    parser.add_argument("--out", type=Path, default=Path("exports"), help="Carpeta de salida para --split")
    args = parser.parse_args()

    schema = load_json(SCHEMA_PATH)
    doc = load_json(args.lesson_file)

    errors = validate(doc, schema)
    if errors:
        print(f"✗ INVÁLIDO — {args.lesson_file.name} tiene {len(errors)} error(es):\n")
        for msg in errors:
            print(f"  - {msg}")
        sys.exit(1)

    print(f"✓ VÁLIDO — {args.lesson_file.name} cumple el schema.")

    if args.split:
        args.out.mkdir(parents=True, exist_ok=True)
        alumno, maestro = split_lesson(doc)

        lesson_id = doc["lesson"]["id"]
        alumno_path = args.out / f"{lesson_id}_alumno.json"
        maestro_path = args.out / f"{lesson_id}_maestro.json"

        with open(alumno_path, "w", encoding="utf-8") as f:
            json.dump(alumno, f, ensure_ascii=False, indent=2)
        with open(maestro_path, "w", encoding="utf-8") as f:
            json.dump(maestro, f, ensure_ascii=False, indent=2)

        print(f"  → generado: {alumno_path}")
        print(f"  → generado: {maestro_path}")


if __name__ == "__main__":
    main()
