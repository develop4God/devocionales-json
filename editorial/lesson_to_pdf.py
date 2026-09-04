#!/usr/bin/env python3
"""
lesson_to_pdf.py

Convierte un archivo de lección exportado (alumno o maestro, generado por
validate_lesson.py --split) en un PDF con formato para imprimir/compartir.

Uso:
    python lesson_to_pdf.py exports/lesson_social_media_01_alumno.json
    python lesson_to_pdf.py exports/lesson_social_media_01_maestro.json --out pdf/
"""

import argparse
import json
from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem,
)


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="LessonTitle", parent=styles["Title"], spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeading", parent=styles["Heading2"],
        spaceBefore=16, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="Body", parent=styles["BodyText"], alignment=TA_LEFT,
        spaceAfter=6, leading=15,
    ))
    styles.add(ParagraphStyle(
        name="VerseText", parent=styles["BodyText"], leftIndent=18,
        rightIndent=18, spaceAfter=6, leading=15, italic=True,
    ))
    return styles


def render_alumno(doc_data: dict, story: list, styles):
    content = doc_data["content"]

    story.append(Paragraph("Contenido del alumno", styles["SectionHeading"]))
    story.append(Paragraph(content["teaching_summary"], styles["Body"]))

    story.append(Paragraph("Preguntas de comprensión", styles["SectionHeading"]))
    story.append(ListFlowable(
        [ListItem(Paragraph(q["text"], styles["Body"])) for q in content["comprehension_questions"]],
        bulletType="1",
    ))

    if content.get("fill_in_blanks"):
        story.append(Paragraph("Completa la frase", styles["SectionHeading"]))
        story.append(ListFlowable(
            [ListItem(Paragraph(t, styles["Body"])) for t in content["fill_in_blanks"]],
            bulletType="bullet",
        ))

    outline = content["personal_outline"]
    story.append(Paragraph(outline.get("title", "Para tu tiempo a solas"), styles["SectionHeading"]))
    story.append(ListFlowable(
        [ListItem(Paragraph(p, styles["Body"])) for p in outline["points"]],
        bulletType="bullet",
    ))

    story.append(Paragraph("Diálogo familiar", styles["SectionHeading"]))
    story.append(ListFlowable(
        [ListItem(Paragraph(q, styles["Body"])) for q in content["family_discussion"]["questions"]],
        bulletType="bullet",
    ))

    story.append(Paragraph("Desafío de evangelismo", styles["SectionHeading"]))
    story.append(Paragraph(content["evangelism_prompt"], styles["Body"]))


def render_maestro(doc_data: dict, story: list, styles):
    content = doc_data["content"]

    story.append(Paragraph("Enseñanza a fondo", styles["SectionHeading"]))
    story.append(Paragraph(content["teaching_deep_dive"], styles["Body"]))

    story.append(Paragraph("Notas de facilitación", styles["SectionHeading"]))
    story.append(Paragraph(content["facilitation_notes"], styles["Body"]))

    story.append(Paragraph("Dinámicas de grupo", styles["SectionHeading"]))
    story.append(ListFlowable(
        [ListItem(Paragraph(d, styles["Body"])) for d in content["group_dynamics"]],
        bulletType="bullet",
    ))

    leader = content["leader_training"]
    story.append(Paragraph(f"Capacitación del líder: {leader['topic']}", styles["SectionHeading"]))
    story.append(Paragraph(leader["content"], styles["Body"]))

    if content.get("materials_needed"):
        story.append(Paragraph("Materiales necesarios", styles["SectionHeading"]))
        story.append(ListFlowable(
            [ListItem(Paragraph(m, styles["Body"])) for m in content["materials_needed"]],
            bulletType="bullet",
        ))


def render_lesson_pdf(doc_data: dict, out_path: Path):
    styles = build_styles()
    story = []

    story.append(Paragraph(doc_data["title"], styles["LessonTitle"]))
    story.append(Paragraph(doc_data["objective"], styles["Body"]))
    story.append(Spacer(1, 12))

    bible_reading = doc_data["bible_reading"]
    story.append(Paragraph(
        f"Lectura bíblica: {bible_reading['reference']} ({bible_reading['version']})",
        styles["SectionHeading"],
    ))
    if bible_reading.get("context_note"):
        story.append(Paragraph(bible_reading["context_note"], styles["Body"]))

    key_verse = doc_data["key_verse"]
    story.append(Paragraph(f"Versículo clave: {key_verse['reference']}", styles["SectionHeading"]))
    story.append(Paragraph(key_verse["text"], styles["VerseText"]))

    hook = doc_data["hook"]
    story.append(Paragraph("Introducción", styles["SectionHeading"]))
    story.append(Paragraph(hook["content"], styles["Body"]))

    audience = doc_data["content"]["audience"]
    if audience == "alumno":
        render_alumno(doc_data, story, styles)
    elif audience == "maestro":
        render_maestro(doc_data, story, styles)
    else:
        raise ValueError(f"Audiencia desconocida: {audience!r}")

    pdf = SimpleDocTemplate(
        str(out_path), pagesize=LETTER,
        leftMargin=0.9 * inch, rightMargin=0.9 * inch,
        topMargin=0.8 * inch, bottomMargin=0.8 * inch,
    )
    pdf.build(story)


def main():
    parser = argparse.ArgumentParser(description="Convierte una lección exportada (alumno/maestro) a PDF.")
    parser.add_argument("lesson_file", type=Path, help="Ruta al JSON exportado (_alumno.json o _maestro.json)")
    parser.add_argument("--out", type=Path, default=None, help="Ruta o carpeta de salida para el PDF")
    args = parser.parse_args()

    doc_data = load_json(args.lesson_file)

    if args.out is None:
        out_path = args.lesson_file.with_suffix(".pdf")
    elif args.out.suffix == ".pdf":
        out_path = args.out
    else:
        args.out.mkdir(parents=True, exist_ok=True)
        out_path = args.out / args.lesson_file.with_suffix(".pdf").name

    render_lesson_pdf(doc_data, out_path)
    print(f"✓ generado: {out_path}")


if __name__ == "__main__":
    main()
