
"""
AutoTecPro AI document generator framework.

This module is independent of Streamlit, OpenAI, Supabase, WooCommerce, and
workspace UI code. It generates real downloadable files for PDF, DOCX, PPTX,
XLSX, and CSV and serializes them into chat-history-safe records.
"""

from __future__ import annotations

import base64
import csv
import io
import json
import re
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

DOCUMENT_MARKER_PREFIX = "\n<!--ATP_GENERATED_DOCUMENTS:"
DOCUMENT_MARKER_SUFFIX = ":ATP_GENERATED_DOCUMENTS-->\n"

FORMAT_CONFIG = {
    "pdf": {
        "extension": ".pdf",
        "mime_type": "application/pdf",
        "label": "PDF",
        "icon": "📄",
    },
    "docx": {
        "extension": ".docx",
        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "label": "Word",
        "icon": "📝",
    },
    "pptx": {
        "extension": ".pptx",
        "mime_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "label": "PowerPoint",
        "icon": "📊",
    },
    "xlsx": {
        "extension": ".xlsx",
        "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "label": "Excel",
        "icon": "📈",
    },
    "csv": {
        "extension": ".csv",
        "mime_type": "text/csv",
        "label": "CSV",
        "icon": "📋",
    },
}

_READ_ONLY_PATTERNS = (
    "summarize this pdf", "summarise this pdf", "read this pdf",
    "analyze this pdf", "analyse this pdf", "review this pdf",
    "summarize this word", "read this word", "review this word",
    "analyze this spreadsheet", "review this spreadsheet",
    "summarize this powerpoint", "review this powerpoint",
    "extract from this pdf", "what does this pdf",
)

_FORMAT_PATTERNS = (
    ("pptx", (
        "powerpoint", "power point", "pptx", "slide deck",
        "presentation", "slides",
    )),
    ("xlsx", (
        "excel", "xlsx", "spreadsheet", "workbook",
    )),
    ("docx", (
        "word document", "word file", "docx", "microsoft word",
    )),
    ("csv", (
        "csv", "comma-separated", "comma separated",
    )),
    ("pdf", ("pdf",)),
)

_CREATION_TERMS = (
    "create", "generate", "make", "produce", "prepare", "build", "compile",
    "export", "save", "download", "turn this into", "convert this to",
)


def detect_document_generation_request(prompt_text: Any) -> dict[str, str] | None:
    """Return the requested document format only for explicit generation requests."""
    value = re.sub(r"\s+", " ", str(prompt_text or "")).strip().lower()
    if not value or any(pattern in value for pattern in _READ_ONLY_PATTERNS):
        return None

    requested_format = ""
    for format_name, patterns in _FORMAT_PATTERNS:
        if any(pattern in value for pattern in patterns):
            requested_format = format_name
            break

    if not requested_format:
        return None

    if not any(term in value for term in _CREATION_TERMS):
        # Accept direct artifact wording such as "PDF report" or "Excel file".
        artifact_terms = (
            "file", "document", "manual", "guide", "report", "proposal",
            "handbook", "sop", "presentation", "slides", "spreadsheet",
            "workbook", "table", "export",
        )
        if not any(term in value for term in artifact_terms):
            return None

    config = FORMAT_CONFIG[requested_format]
    return {
        "format": requested_format,
        "extension": config["extension"],
        "mime_type": config["mime_type"],
        "label": config["label"],
    }


def is_document_generation_request(prompt_text: Any) -> bool:
    return detect_document_generation_request(prompt_text) is not None


def _safe_stem(prompt_text: Any, answer_text: Any = "") -> str:
    source = str(prompt_text or "").strip() or str(answer_text or "").strip()
    # Remove common generator wording so filenames focus on the subject.
    source = re.sub(
        r"(?i)\b(?:create|generate|make|produce|prepare|build|export|save|"
        r"download|convert|turn this into|as a|an?)\b",
        " ",
        source,
    )
    source = re.sub(
        r"(?i)\b(?:pdf|docx|word|document|pptx|powerpoint|presentation|"
        r"xlsx|excel|spreadsheet|csv|file|downloadable)\b",
        " ",
        source,
    )
    words = re.findall(r"[A-Za-z0-9]+", source)[:10]
    stem = "_".join(words).strip("_") or "AutoTecPro_AI_Document"
    stem = re.sub(r"_+", "_", stem)[:96].strip("_")
    return Path(stem).name or "AutoTecPro_AI_Document"


def safe_document_filename(
    prompt_text: Any,
    answer_text: Any = "",
    format_name: str = "pdf",
) -> str:
    format_name = str(format_name or "pdf").lower()
    config = FORMAT_CONFIG.get(format_name, FORMAT_CONFIG["pdf"])
    return _safe_stem(prompt_text, answer_text) + config["extension"]


def _clean_document_text(
    value: Any,
    visible_text_cleaner: Callable[[Any], str] | None = None,
) -> str:
    raw = visible_text_cleaner(value) if callable(visible_text_cleaner) else str(value or "")
    cleaned = str(raw or "").replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"```[A-Za-z0-9_-]*", "", cleaned)
    cleaned = cleaned.replace("```", "")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip() or "No document content was generated."


def _plain_text(value: Any, cleaner=None) -> str:
    cleaned = _clean_document_text(value, cleaner)
    cleaned = re.sub(r"^\s{0,3}#{1,6}\s*", "", cleaned, flags=re.M)
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"__(.*?)__", r"\1", cleaned)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    cleaned = cleaned.replace("•", "-")
    return cleaned.strip()


def _pdf_escape_text(value: Any) -> str:
    encoded = str(value or "").encode("cp1252", errors="replace").decode("latin-1")
    return (
        encoded.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\r", "")
    )


def _wrap_pdf_lines(text: Any, max_chars: int = 92) -> list[str]:
    lines: list[str] = []
    width = max(24, int(max_chars or 92))
    for raw_line in str(text or "").splitlines():
        stripped = raw_line.rstrip()
        if not stripped:
            lines.append("")
            continue
        leading = ""
        content = stripped.strip()
        if content.startswith(("- ", "* ", "• ")):
            leading = "- "
            content = content[2:].strip()
        wrapped = textwrap.wrap(
            content,
            width=max(12, width - len(leading)),
            break_long_words=True,
            break_on_hyphens=True,
            replace_whitespace=False,
            drop_whitespace=True,
        ) or [""]
        for index, line in enumerate(wrapped):
            lines.append((leading if index == 0 else "  ") + line)
    return lines


def build_text_pdf(
    document_text: Any,
    title: str = "AutoTecPro AI Document",
    visible_text_cleaner: Callable[[Any], str] | None = None,
) -> tuple[bytes, int]:
    """Build a valid multi-page PDF without requiring ReportLab."""
    clean_title = re.sub(r"\s+", " ", str(title or "AutoTecPro AI Document")).strip()
    clean_text = _plain_text(document_text, visible_text_cleaner)

    page_width, page_height = 612, 792
    left_margin, top_y, bottom_y = 54, 738, 54
    body_font_size, line_height = 10, 14
    lines_per_page = max(1, int((top_y - bottom_y) / line_height) - 2)
    wrapped_lines = _wrap_pdf_lines(clean_text, max_chars=92)
    pages = [
        wrapped_lines[index:index + lines_per_page]
        for index in range(0, len(wrapped_lines), lines_per_page)
    ] or [["No document content was generated."]]

    objects: dict[int, bytes] = {}
    next_id = 1

    def reserve() -> int:
        nonlocal next_id
        object_id = next_id
        next_id += 1
        return object_id

    catalog_id, pages_id, font_id = reserve(), reserve(), reserve()
    page_ids, content_ids = [], []
    for _ in pages:
        page_ids.append(reserve())
        content_ids.append(reserve())

    objects[font_id] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

    for page_number, (page_id, content_id, page_lines) in enumerate(
        zip(page_ids, content_ids, pages), start=1
    ):
        commands = [
            "BT", f"/F1 {body_font_size} Tf", f"{left_margin} {top_y} Td",
            f"({_pdf_escape_text(clean_title)}) Tj", f"0 -{line_height * 2} Td",
        ]
        for line in page_lines:
            commands.extend([
                f"({_pdf_escape_text(line)}) Tj",
                f"0 -{line_height} Td",
            ])
        footer = f"Page {page_number} of {len(pages)}"
        commands.extend([
            "ET", "BT", "/F1 8 Tf", f"{page_width - 110} 30 Td",
            f"({_pdf_escape_text(footer)}) Tj", "ET",
        ])
        stream = "\n".join(commands).encode("latin-1", errors="replace")
        objects[content_id] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream + b"\nendstream"
        )
        objects[page_id] = (
            f"<< /Type /Page /Parent {pages_id} 0 R "
            f"/MediaBox [0 0 {page_width} {page_height}] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        ).encode("ascii")

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[pages_id] = (
        f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>"
    ).encode("ascii")
    objects[catalog_id] = (
        f"<< /Type /Catalog /Pages {pages_id} 0 R >>"
    ).encode("ascii")

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0] * next_id
    for object_id in range(1, next_id):
        offsets[object_id] = len(pdf)
        pdf.extend(f"{object_id} 0 obj\n".encode("ascii"))
        pdf.extend(objects[object_id])
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {next_id}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for object_id in range(1, next_id):
        pdf.extend(f"{offsets[object_id]:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer\n<< /Size {next_id} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF"
        ).encode("ascii")
    )
    return bytes(pdf), len(pages)


def _iter_markdown_blocks(text: str):
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            yield ("blank", "")
        elif re.match(r"^#{1,6}\s+", stripped):
            level = len(stripped) - len(stripped.lstrip("#"))
            yield (f"heading{min(level, 3)}", stripped[level:].strip())
        elif stripped.startswith(("- ", "* ", "• ")):
            yield ("bullet", stripped[2:].strip())
        elif re.match(r"^\d+[.)]\s+", stripped):
            yield ("number", re.sub(r"^\d+[.)]\s+", "", stripped))
        else:
            yield ("paragraph", stripped)


def build_docx(
    document_text: Any,
    title: str,
    visible_text_cleaner=None,
) -> tuple[bytes, int]:
    from docx import Document
    from docx.shared import Inches, Pt

    text = _clean_document_text(document_text, visible_text_cleaner)
    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)
    document.add_heading(title, 0)

    for kind, value in _iter_markdown_blocks(text):
        value = re.sub(r"\*\*(.*?)\*\*", r"\1", value)
        value = re.sub(r"`([^`]+)`", r"\1", value)
        if kind == "blank":
            document.add_paragraph("")
        elif kind.startswith("heading"):
            document.add_heading(value, level=int(kind[-1]))
        elif kind == "bullet":
            document.add_paragraph(value, style="List Bullet")
        elif kind == "number":
            document.add_paragraph(value, style="List Number")
        else:
            document.add_paragraph(value)

    styles = document.styles
    styles["Normal"].font.name = "Arial"
    styles["Normal"].font.size = Pt(10.5)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue(), max(1, len(document.paragraphs))


def _split_slide_sections(text: str) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    current_title = ""
    current_lines: list[str] = []
    for kind, value in _iter_markdown_blocks(text):
        if kind.startswith("heading"):
            if current_title or current_lines:
                sections.append((current_title or "Overview", current_lines))
            current_title, current_lines = value, []
        elif kind != "blank":
            current_lines.append(value)
    if current_title or current_lines:
        sections.append((current_title or "Overview", current_lines))
    return sections or [("Overview", [text])]


def build_pptx(
    document_text: Any,
    title: str,
    visible_text_cleaner=None,
) -> tuple[bytes, int]:
    from pptx import Presentation
    from pptx.util import Inches, Pt

    text = _clean_document_text(document_text, visible_text_cleaner)
    presentation = Presentation()
    presentation.slide_width = Inches(13.333)
    presentation.slide_height = Inches(7.5)

    title_slide = presentation.slides.add_slide(presentation.slide_layouts[0])
    title_slide.shapes.title.text = title
    if len(title_slide.placeholders) > 1:
        title_slide.placeholders[1].text = "Generated by AutoTecPro AI"

    for section_title, section_lines in _split_slide_sections(text):
        chunks = [
            section_lines[index:index + 7]
            for index in range(0, len(section_lines), 7)
        ] or [[]]
        for chunk_index, chunk in enumerate(chunks):
            slide = presentation.slides.add_slide(presentation.slide_layouts[1])
            slide.shapes.title.text = (
                section_title if chunk_index == 0
                else f"{section_title} (continued)"
            )
            frame = slide.placeholders[1].text_frame
            frame.clear()
            for item_index, line in enumerate(chunk):
                paragraph = frame.paragraphs[0] if item_index == 0 else frame.add_paragraph()
                paragraph.text = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
                paragraph.level = 0
                paragraph.font.size = Pt(22)

    buffer = io.BytesIO()
    presentation.save(buffer)
    return buffer.getvalue(), len(presentation.slides)


def _extract_table_rows(text: str) -> list[list[str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    markdown_rows: list[list[str]] = []
    for line in lines:
        if "|" in line:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if cells and not all(re.fullmatch(r":?-{3,}:?", c or "") for c in cells):
                markdown_rows.append(cells)
    if len(markdown_rows) >= 2:
        width = max(len(row) for row in markdown_rows)
        return [row + [""] * (width - len(row)) for row in markdown_rows]

    rows = []
    for line in lines:
        line = re.sub(r"^[-*•]\s+", "", line)
        if ":" in line and len(line.split(":", 1)[0]) <= 50:
            left, right = line.split(":", 1)
            rows.append([left.strip(), right.strip()])
        elif "," in line:
            rows.append([cell.strip() for cell in next(csv.reader([line]))])
        else:
            rows.append([line])
    width = max((len(row) for row in rows), default=1)
    return [row + [""] * (width - len(row)) for row in rows]


def build_xlsx(
    document_text: Any,
    title: str,
    visible_text_cleaner=None,
) -> tuple[bytes, int]:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    text = _clean_document_text(document_text, visible_text_cleaner)
    rows = _extract_table_rows(text)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Document"
    sheet["A1"] = title
    sheet["A1"].font = Font(bold=True, size=16)
    sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(1, len(rows[0]) if rows else 1))

    for r_index, row in enumerate(rows, start=3):
        for c_index, value in enumerate(row, start=1):
            cell = sheet.cell(row=r_index, column=c_index, value=value)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            if r_index == 3 and len(rows) > 1:
                cell.font = Font(bold=True)
                cell.fill = PatternFill("solid", fgColor="D9EAF7")

    for c_index in range(1, max((len(r) for r in rows), default=1) + 1):
        max_len = max(
            [len(str(sheet.cell(r, c_index).value or "")) for r in range(1, sheet.max_row + 1)]
            or [10]
        )
        sheet.column_dimensions[get_column_letter(c_index)].width = min(max(max_len + 2, 12), 40)
    sheet.freeze_panes = "A3"
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue(), max(1, len(workbook.sheetnames))


def build_csv(
    document_text: Any,
    title: str,
    visible_text_cleaner=None,
) -> tuple[bytes, int]:
    text = _clean_document_text(document_text, visible_text_cleaner)
    rows = _extract_table_rows(text)
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig"), max(1, len(rows))


def create_document_record(
    prompt_text: Any,
    answer_text: Any,
    format_name: str | None = None,
    visible_text_cleaner: Callable[[Any], str] | None = None,
) -> dict[str, Any]:
    request = detect_document_generation_request(prompt_text)
    resolved_format = str(format_name or (request or {}).get("format") or "pdf").lower()
    if resolved_format not in FORMAT_CONFIG:
        raise ValueError(f"Unsupported document format: {resolved_format}")

    filename = safe_document_filename(prompt_text, answer_text, resolved_format)
    title = Path(filename).stem.replace("_", " ").strip() or "AutoTecPro AI Document"

    if resolved_format == "pdf":
        file_bytes, unit_count = build_text_pdf(answer_text, title, visible_text_cleaner)
        unit_label = "Pages"
    elif resolved_format == "docx":
        file_bytes, unit_count = build_docx(answer_text, title, visible_text_cleaner)
        unit_label = "Paragraphs"
    elif resolved_format == "pptx":
        file_bytes, unit_count = build_pptx(answer_text, title, visible_text_cleaner)
        unit_label = "Slides"
    elif resolved_format == "xlsx":
        file_bytes, unit_count = build_xlsx(answer_text, title, visible_text_cleaner)
        unit_label = "Sheets"
    else:
        file_bytes, unit_count = build_csv(answer_text, title, visible_text_cleaner)
        unit_label = "Rows"

    config = FORMAT_CONFIG[resolved_format]
    encoded = base64.b64encode(file_bytes).decode("ascii")
    return {
        "name": filename,
        "format": resolved_format,
        "format_label": config["label"],
        "icon": config["icon"],
        "mime_type": config["mime_type"],
        "data_url": f"data:{config['mime_type']};base64,{encoded}",
        "unit_count": int(unit_count),
        "unit_label": unit_label,
        "page_count": int(unit_count) if resolved_format == "pdf" else 0,
        "size_bytes": len(file_bytes),
        "generated": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def serialize_documents_marker(documents: Iterable[dict[str, Any]] | None) -> str:
    records = list(documents or [])
    if not records:
        return ""
    try:
        return (
            "\n\n" + DOCUMENT_MARKER_PREFIX
            + json.dumps(records, ensure_ascii=False)
            + DOCUMENT_MARKER_SUFFIX
        )
    except Exception:
        return ""


def extract_documents_from_message_content(
    content: Any,
) -> tuple[str, list[dict[str, Any]]]:
    value = str(content or "")
    pattern = re.escape(DOCUMENT_MARKER_PREFIX) + r"(.*?)" + re.escape(DOCUMENT_MARKER_SUFFIX)
    match = re.search(pattern, value, flags=re.DOTALL)
    if not match:
        # Backward compatibility with PDF-only history markers.
        legacy_pattern = (
            re.escape("\n<!--ATP_PDF_DOCUMENTS:")
            + r"(.*?)"
            + re.escape(":ATP_PDF_DOCUMENTS-->\n")
        )
        match = re.search(legacy_pattern, value, flags=re.DOTALL)
        if not match:
            return value, []

    visible_text = (value[:match.start()] + value[match.end():]).strip()
    try:
        documents = json.loads(match.group(1))
    except Exception:
        documents = []

    clean_documents: list[dict[str, Any]] = []
    for document in documents if isinstance(documents, list) else []:
        if not isinstance(document, dict):
            continue
        data_url = str(document.get("data_url") or "")
        if not data_url.startswith("data:") or ";base64," not in data_url:
            continue
        format_name = str(document.get("format") or "").lower()
        if not format_name:
            mime = str(document.get("mime_type") or data_url[5:].split(";", 1)[0])
            format_name = next(
                (key for key, config in FORMAT_CONFIG.items() if config["mime_type"] == mime),
                "pdf",
            )
        if format_name not in FORMAT_CONFIG:
            continue
        config = FORMAT_CONFIG[format_name]
        try:
            size_bytes = int(document.get("size_bytes") or 0)
        except (TypeError, ValueError):
            size_bytes = 0
        try:
            unit_count = int(document.get("unit_count") or document.get("page_count") or 0)
        except (TypeError, ValueError):
            unit_count = 0
        clean_documents.append({
            "name": Path(str(document.get("name") or ("AutoTecPro_AI_Document" + config["extension"]))).name,
            "format": format_name,
            "format_label": document.get("format_label") or config["label"],
            "icon": document.get("icon") or config["icon"],
            "mime_type": config["mime_type"],
            "data_url": data_url,
            "unit_count": unit_count,
            "unit_label": document.get("unit_label") or ("Pages" if format_name == "pdf" else ""),
            "page_count": unit_count if format_name == "pdf" else 0,
            "size_bytes": size_bytes,
            "generated": bool(document.get("generated", True)),
            "created_at": document.get("created_at"),
        })
    return visible_text, clean_documents

# ============================================================
# Contextual document export and optional branding overrides
# ============================================================

def detect_document_generation_request(prompt_text: Any) -> dict[str, str] | None:
    value = re.sub(r"\s+", " ", str(prompt_text or "")).strip().lower()
    if not value or any(pattern in value for pattern in _READ_ONLY_PATTERNS):
        return None

    requested_format = ""
    for format_name, patterns in _FORMAT_PATTERNS:
        if any(pattern in value for pattern in patterns):
            requested_format = format_name
            break

    conversation_request = any(phrase in value for phrase in (
        "convert this conversation to a document",
        "convert the conversation to a document",
        "convert this chat to a document",
        "turn this conversation into a document",
        "turn this chat into a document",
        "export this conversation",
        "export this chat",
        "create a document from this conversation",
        "create a document from this chat",
    ))

    if not requested_format and not conversation_request:
        return None

    if requested_format and not any(term in value for term in _CREATION_TERMS):
        artifact_terms = (
            "file", "document", "manual", "guide", "report", "proposal",
            "handbook", "sop", "presentation", "slides", "spreadsheet",
            "workbook", "table", "export", "conversation", "chat",
        )
        if not any(term in value for term in artifact_terms):
            return None

    if requested_format:
        config = FORMAT_CONFIG[requested_format]
        return {
            "format": requested_format,
            "extension": config["extension"],
            "mime_type": config["mime_type"],
            "label": config["label"],
            "scope": "conversation" if ("conversation" in value or "chat" in value) else "response",
        }

    return {
        "format": "",
        "extension": "",
        "mime_type": "",
        "label": "Document",
        "scope": "conversation",
    }


def _document_options(options: Any = None) -> dict[str, Any]:
    raw = dict(options or {}) if isinstance(options, dict) else {}
    style = str(raw.get("style") or "Professional").strip().title()
    if style not in {"Professional", "Minimal", "Presentation"}:
        style = "Professional"
    logo_path = Path(str(raw.get("logo_path") or "")).expanduser()
    return {
        "include_logo": bool(raw.get("include_logo")),
        "include_company_info": bool(raw.get("include_company_info")),
        "watermark": str(raw.get("watermark") or "").strip()[:60],
        "style": style,
        "logo_path": logo_path if logo_path.is_file() else None,
        "company_name": str(raw.get("company_name") or "AutoTecPro Inc.").strip(),
        "company_info": str(raw.get("company_info") or "Generated by AutoTecPro AI").strip(),
    }


def _build_pdf_with_options(document_text, title, cleaner=None, options=None):
    opts = _document_options(options)
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image as RLImage
        import html as _html
    except Exception:
        return build_text_pdf(document_text, title, cleaner)

    text = _clean_document_text(document_text, cleaner)
    buffer = io.BytesIO()
    pdf_doc = SimpleDocTemplate(
        buffer, pagesize=letter, rightMargin=.7*inch, leftMargin=.7*inch,
        topMargin=.65*inch, bottomMargin=.65*inch, title=title,
        author=opts["company_name"],
    )
    styles = getSampleStyleSheet()
    accent = colors.HexColor("#B91C1C")
    styles.add(ParagraphStyle(name="ATPTitle", parent=styles["Title"], textColor=accent,
                              fontName="Helvetica-Bold", fontSize=22, leading=27,
                              alignment=TA_CENTER, spaceAfter=16))
    styles.add(ParagraphStyle(name="ATPBody", parent=styles["BodyText"],
                              fontName="Helvetica", fontSize=11 if opts["style"] != "Presentation" else 12,
                              leading=16, textColor=colors.HexColor("#111827"), spaceAfter=7))
    styles.add(ParagraphStyle(name="ATPH1", parent=styles["Heading1"], textColor=accent,
                              fontName="Helvetica-Bold", fontSize=16, leading=20,
                              spaceBefore=12, spaceAfter=7))
    story = []
    if opts["include_logo"] and opts["logo_path"]:
        try:
            logo = RLImage(str(opts["logo_path"]), width=1.65*inch, height=.58*inch)
            logo.hAlign = "CENTER"
            story.extend([logo, Spacer(1, 12)])
        except Exception:
            pass
    story.append(Paragraph(_html.escape(title), styles["ATPTitle"]))
    if opts["include_company_info"]:
        company_style = ParagraphStyle(name="ATPCompany", parent=styles["BodyText"],
                                       alignment=TA_CENTER, textColor=colors.HexColor("#6B7280"),
                                       fontSize=9.5, spaceAfter=16)
        story.append(Paragraph(_html.escape(f'{opts["company_name"]} — {opts["company_info"]}'), company_style))
    if opts["include_logo"] or opts["include_company_info"]:
        story.append(PageBreak())

    for kind, value in _iter_markdown_blocks(text):
        clean = re.sub(r"\*\*(.*?)\*\*", r"\1", value)
        clean = re.sub(r"`([^`]+)`", r"\1", clean)
        safe = _html.escape(clean)
        if kind == "blank":
            story.append(Spacer(1, 5))
        elif kind.startswith("heading"):
            story.append(Paragraph(safe, styles["ATPH1"]))
        elif kind in {"bullet", "number"}:
            story.append(Paragraph(("• " if kind == "bullet" else "") + safe, styles["ATPBody"]))
        else:
            story.append(Paragraph(safe, styles["ATPBody"]))

    def draw_page(canvas, doc_obj):
        canvas.saveState()
        if opts["watermark"]:
            canvas.setFillColor(colors.Color(.55, .55, .55, alpha=.16))
            canvas.setFont("Helvetica-Bold", 40)
            canvas.translate(letter[0]/2, letter[1]/2)
            canvas.rotate(35)
            canvas.drawCentredString(0, 0, opts["watermark"])
            canvas.rotate(-35)
            canvas.translate(-letter[0]/2, -letter[1]/2)
        canvas.setFillColor(colors.HexColor("#6B7280"))
        canvas.setFont("Helvetica", 8)
        if opts["include_company_info"]:
            canvas.drawString(.7*inch, .36*inch, opts["company_name"])
        canvas.drawRightString(letter[0]-.7*inch, .36*inch, f"Page {doc_obj.page}")
        canvas.restoreState()

    pdf_doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    data = buffer.getvalue()
    return data, max(1, data.count(b"/Type /Page"))


def _build_docx_with_options(document_text, title, cleaner=None, options=None):
    from docx import Document
    from docx.shared import Inches, Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    opts = _document_options(options)
    text = _clean_document_text(document_text, cleaner)
    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(.7)
    section.bottom_margin = Inches(.7)
    section.left_margin = Inches(.8)
    section.right_margin = Inches(.8)
    if opts["include_logo"] and opts["logo_path"]:
        try:
            p = document.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run().add_picture(str(opts["logo_path"]), width=Inches(1.7))
        except Exception:
            pass
    heading = document.add_heading(title, 0); heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if opts["include_company_info"]:
        p = document.add_paragraph(f'{opts["company_name"]} — {opts["company_info"]}')
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if opts["include_logo"] or opts["include_company_info"]:
        document.add_page_break()
    for kind, value in _iter_markdown_blocks(text):
        value = re.sub(r"\*\*(.*?)\*\*", r"\1", value)
        value = re.sub(r"`([^`]+)`", r"\1", value)
        if kind == "blank": document.add_paragraph("")
        elif kind.startswith("heading"): document.add_heading(value, level=int(kind[-1]))
        elif kind == "bullet": document.add_paragraph(value, style="List Bullet")
        elif kind == "number": document.add_paragraph(value, style="List Number")
        else: document.add_paragraph(value)
    document.styles["Normal"].font.name = "Arial"
    document.styles["Normal"].font.size = Pt(12 if opts["style"] == "Presentation" else 10.5)
    if opts["watermark"]:
        header = section.header.paragraphs[0]; header.text = opts["watermark"]
        header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    buffer = io.BytesIO(); document.save(buffer)
    return buffer.getvalue(), max(1, len(document.paragraphs))


def _build_pptx_with_options(document_text, title, cleaner=None, options=None):
    from pptx import Presentation
    from pptx.util import Inches, Pt
    opts = _document_options(options)
    text = _clean_document_text(document_text, cleaner)
    presentation = Presentation(); presentation.slide_width = Inches(13.333); presentation.slide_height = Inches(7.5)
    title_slide = presentation.slides.add_slide(presentation.slide_layouts[0])
    title_slide.shapes.title.text = title
    if len(title_slide.placeholders) > 1:
        title_slide.placeholders[1].text = f'{opts["company_name"]}\n{opts["company_info"]}' if opts["include_company_info"] else "Generated by AutoTecPro AI"
    if opts["include_logo"] and opts["logo_path"]:
        try: title_slide.shapes.add_picture(str(opts["logo_path"]), Inches(10.9), Inches(.35), width=Inches(1.7))
        except Exception: pass
    for section_title, section_lines in _split_slide_sections(text):
        chunks = [section_lines[i:i+7] for i in range(0, len(section_lines), 7)] or [[]]
        for chunk_index, chunk in enumerate(chunks):
            slide = presentation.slides.add_slide(presentation.slide_layouts[1])
            slide.shapes.title.text = section_title if chunk_index == 0 else f"{section_title} (continued)"
            frame = slide.placeholders[1].text_frame; frame.clear()
            for item_index, line in enumerate(chunk):
                p = frame.paragraphs[0] if item_index == 0 else frame.add_paragraph()
                p.text = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
                p.font.size = Pt(22 if opts["style"] == "Presentation" else 19)
            if opts["include_logo"] and opts["logo_path"]:
                try: slide.shapes.add_picture(str(opts["logo_path"]), Inches(11.1), Inches(.2), width=Inches(1.45))
                except Exception: pass
    buffer = io.BytesIO(); presentation.save(buffer)
    return buffer.getvalue(), len(presentation.slides)


def _build_xlsx_with_options(document_text, title, cleaner=None, options=None):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    opts = _document_options(options)
    text = _clean_document_text(document_text, cleaner); rows = _extract_table_rows(text)
    workbook = Workbook(); sheet = workbook.active; sheet.title = "Document"
    sheet["A1"] = title; sheet["A1"].font = Font(bold=True, size=16, color="B91C1C")
    width = max(1, len(rows[0]) if rows else 1)
    sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=width)
    start_row = 3
    if opts["include_company_info"]:
        sheet["A2"] = f'{opts["company_name"]} — {opts["company_info"]}'; start_row = 4
    if opts["include_logo"] and opts["logo_path"]:
        try:
            from openpyxl.drawing.image import Image as XLImage
            image = XLImage(str(opts["logo_path"])); image.width = 145; image.height = 48
            sheet.add_image(image, f"{get_column_letter(max(2, width))}1")
        except Exception: pass
    for r_index, row in enumerate(rows, start=start_row):
        for c_index, value in enumerate(row, start=1):
            cell = sheet.cell(r_index, c_index, value=value); cell.alignment = Alignment(vertical="top", wrap_text=True)
            if r_index == start_row and len(rows) > 1:
                cell.font = Font(bold=True, color="FFFFFF"); cell.fill = PatternFill("solid", fgColor="B91C1C")
    for c_index in range(1, max((len(r) for r in rows), default=1)+1):
        max_len = max((len(str(sheet.cell(r, c_index).value or "")) for r in range(1, sheet.max_row+1)), default=10)
        sheet.column_dimensions[get_column_letter(c_index)].width = min(max(max_len+2, 12), 40)
    sheet.freeze_panes = f"A{start_row}"
    buffer = io.BytesIO(); workbook.save(buffer)
    return buffer.getvalue(), len(workbook.sheetnames)


def _build_csv_with_options(document_text, title, cleaner=None, options=None):
    opts = _document_options(options)
    text = _clean_document_text(document_text, cleaner); rows = _extract_table_rows(text)
    buffer = io.StringIO(newline=""); writer = csv.writer(buffer)
    if opts["include_company_info"]:
        writer.writerow([opts["company_name"], opts["company_info"]]); writer.writerow([])
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig"), max(1, len(rows))


def create_document_record(
    prompt_text: Any,
    answer_text: Any,
    format_name: str | None = None,
    visible_text_cleaner: Callable[[Any], str] | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    request = detect_document_generation_request(prompt_text)
    resolved_format = str(format_name or (request or {}).get("format") or "pdf").lower()
    if resolved_format not in FORMAT_CONFIG:
        raise ValueError(f"Unsupported document format: {resolved_format}")
    filename = safe_document_filename(prompt_text, answer_text, resolved_format)
    title = Path(filename).stem.replace("_", " ").strip() or "AutoTecPro AI Document"
    opts = _document_options(options)
    if resolved_format == "pdf": file_bytes, unit_count, unit_label = *_build_pdf_with_options(answer_text, title, visible_text_cleaner, opts), "Pages"
    elif resolved_format == "docx": file_bytes, unit_count, unit_label = *_build_docx_with_options(answer_text, title, visible_text_cleaner, opts), "Paragraphs"
    elif resolved_format == "pptx": file_bytes, unit_count, unit_label = *_build_pptx_with_options(answer_text, title, visible_text_cleaner, opts), "Slides"
    elif resolved_format == "xlsx": file_bytes, unit_count, unit_label = *_build_xlsx_with_options(answer_text, title, visible_text_cleaner, opts), "Sheets"
    else: file_bytes, unit_count, unit_label = *_build_csv_with_options(answer_text, title, visible_text_cleaner, opts), "Rows"
    config = FORMAT_CONFIG[resolved_format]; encoded = base64.b64encode(file_bytes).decode("ascii")
    return {
        "name": filename, "format": resolved_format, "format_label": config["label"],
        "icon": config["icon"], "mime_type": config["mime_type"],
        "data_url": f"data:{config['mime_type']};base64,{encoded}",
        "unit_count": int(unit_count), "unit_label": unit_label,
        "page_count": int(unit_count) if resolved_format == "pdf" else 0,
        "size_bytes": len(file_bytes), "generated": True,
        "style": opts["style"], "branded": bool(opts["include_logo"] or opts["include_company_info"]),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
