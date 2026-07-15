
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
    """
    Detect explicit-format and generic document generation/export requests.

    Generic commands return an empty format so the active workspace can apply
    its saved/default format. Read/review questions remain excluded.
    """
    value = re.sub(r"\s+", " ", str(prompt_text or "")).strip().lower()
    if not value or any(pattern in value for pattern in _READ_ONLY_PATTERNS):
        return None

    requested_format = ""
    for format_name, patterns in _FORMAT_PATTERNS:
        if any(pattern in value for pattern in patterns):
            requested_format = format_name
            break

    creation_terms = (
        "create", "generate", "make", "produce", "prepare", "build", "compile",
        "export", "save", "download", "turn this into", "turn this conversation into",
        "turn this chat into", "convert this to", "convert this into",
        "convert this conversation to", "convert this conversation into",
        "convert this chat to", "convert this chat into",
    )
    artifact_terms = (
        "file", "document", "manual", "guide", "report", "proposal",
        "handbook", "sop", "documentation", "presentation", "slides",
        "spreadsheet", "workbook", "table", "export",
    )
    generic_context_phrases = (
        "convert this to a document",
        "convert this into a document",
        "convert this conversation to a document",
        "convert this conversation into a document",
        "convert this chat to a document",
        "convert this chat into a document",
        "turn this into a document",
        "turn this conversation into a document",
        "turn this chat into a document",
        "export this conversation",
        "export this chat",
        "save this conversation",
        "save this chat",
    )

    creation_requested = any(term in value for term in creation_terms)
    generic_requested = (
        any(phrase in value for phrase in generic_context_phrases)
        or (creation_requested and any(term in value for term in artifact_terms))
    )

    if not requested_format and not generic_requested:
        return None

    if requested_format and not creation_requested:
        if not any(term in value for term in artifact_terms):
            return None

    scope = (
        "conversation"
        if any(
            term in value
            for term in (
                "conversation", "chat",
                "convert this to a document",
                "convert this into a document",
                "turn this into a document",
            )
        )
        else "response"
    )

    if requested_format:
        config = FORMAT_CONFIG[requested_format]
        return {
            "format": requested_format,
            "extension": config["extension"],
            "mime_type": config["mime_type"],
            "label": config["label"],
            "scope": scope,
        }

    return {
        "format": "",
        "extension": "",
        "mime_type": "",
        "label": "Document",
        "scope": "conversation",
    }

def is_document_generation_request(prompt_text: Any) -> bool:
    return detect_document_generation_request(prompt_text) is not None


def _is_document_command_text(value: Any) -> bool:
    text = re.sub(r"\s+", " ", str(value or "")).strip().lower()
    if not text:
        return False
    command_patterns = (
        "convert this to a document",
        "convert this into a document",
        "convert this conversation",
        "convert this chat",
        "turn this into a document",
        "turn this conversation",
        "turn this chat",
        "export this conversation",
        "export this chat",
        "save this conversation",
        "save this chat",
        "create a document",
        "generate a document",
    )
    return any(pattern in text for pattern in command_patterns)


def _conversation_subject(answer_text: Any) -> str:
    """Derive a concise subject from conversation text, never from export commands."""
    text = str(answer_text or "").replace("\r\n", "\n").replace("\r", "\n")
    user_blocks = re.findall(
        r"(?:^|\n)User\s*\n(.*?)(?=\n\n(?:User|AutoTecPro AI)\s*\n|\Z)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    candidates = []
    for block in user_blocks:
        candidate = re.sub(r"\s+", " ", block).strip(" \t\r\n:.-")
        if candidate and not _is_document_command_text(candidate):
            candidates.append(candidate)

    subject_source = candidates[-1] if candidates else text
    subject_source = re.sub(r"(?im)^(?:User|AutoTecPro AI)\s*$", " ", subject_source)
    subject_source = re.sub(
        r"(?i)\b(?:convert|export|save|turn|create|generate|make)\b.*?\b(?:document|pdf|word|powerpoint|excel|csv)\b",
        " ",
        subject_source,
    )
    subject_source = re.sub(r"\s+", " ", subject_source).strip()

    # Prefer an explicit product/model number from the user's actual subject.
    model_patterns = (
        r"(?i)\b(?:model|series|sku|part(?:\s*number)?|what\s+is)\s*[:#-]?\s*([A-Z]{0,5}-?[A-Z0-9]{2,12})\b",
        r"(?i)^\s*(?:what\s+is\s+)?([A-Z]{0,5}-?\d{2,10})\b",
    )
    for pattern in model_patterns:
        match = re.search(pattern, subject_source)
        if match:
            model = match.group(1).upper()
            if re.search(r"\d", model):
                return f"AutoTecPro Model {model} Reference"

    heading_match = re.search(r"(?m)^\s*#{1,3}\s+(.{4,100})$", text)
    if heading_match:
        heading = re.sub(r"[*_`#]+", "", heading_match.group(1)).strip()
        if heading and not _is_document_command_text(heading):
            return heading[:110]

    cleaned = re.sub(
        r"(?i)^\s*(?:please\s+)?(?:can\s+you\s+)?(?:tell\s+me\s+|explain\s+|show\s+me\s+|what\s+is\s+|what\s+are\s+|how\s+do\s+i\s+|how\s+to\s+)",
        "",
        subject_source,
    ).strip(" ?.,:-")
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'&/().+-]*", cleaned)[:10]
    if words:
        title = " ".join(words)
        if not title.lower().startswith("autotecpro"):
            title = f"AutoTecPro {title}"
        if not re.search(r"(?i)\b(?:document|guide|report|reference|manual|proposal|brief)\b", title):
            title += " Reference"
        return title[:110].strip()
    return "AutoTecPro AI Document"


def derive_document_title(prompt_text: Any, answer_text: Any = "") -> str:
    """Return a useful title without ever using a conversion command."""
    prompt = re.sub(r"\s+", " ", str(prompt_text or "")).strip()
    if prompt and not _is_document_command_text(prompt):
        candidate = _conversation_subject(prompt)
        if candidate != "AutoTecPro AI Document":
            return candidate
    return _conversation_subject(answer_text)

def _safe_stem(prompt_text: Any, answer_text: Any = "") -> str:
    title = derive_document_title(prompt_text, answer_text)
    words = re.findall(r"[A-Za-z0-9]+", title)[:14]
    stem = "_".join(words).strip("_") or "AutoTecPro_AI_Document"
    stem = re.sub(r"_+", "_", stem)[:110].strip("_")
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
        "company_info": str(raw.get("company_info") or "Markham, Ontario, Canada | autotecpro.com | info@autotecpro.com").strip(),
    }


def _prepared_logo_stream(logo_path: Any):
    if not logo_path:
        return None
    path = Path(str(logo_path))
    if not path.is_file():
        return None
    try:
        from PIL import Image, ImageChops
        image = Image.open(path).convert("RGBA")
        rgb = Image.new("RGB", image.size, "white")
        rgb.paste(image.convert("RGB"), mask=image.getchannel("A"))
        diff = ImageChops.difference(rgb, Image.new("RGB", rgb.size, "white")).convert("L")
        box = diff.point(lambda value: 255 if value > 12 else 0).getbbox()
        if box:
            pad = max(6, int(min(image.size) * 0.012))
            image = image.crop((max(0, box[0]-pad), max(0, box[1]-pad), min(image.width, box[2]+pad), min(image.height, box[3]+pad)))
        flat = Image.new("RGB", image.size, "white")
        flat.paste(image.convert("RGB"), mask=image.getchannel("A"))
        stream = io.BytesIO(); flat.save(stream, format="PNG", optimize=True); stream.seek(0)
        return stream
    except Exception:
        return None


def _logo_dimensions(logo_stream, max_width, max_height):
    try:
        from PIL import Image
        position = logo_stream.tell(); image = Image.open(logo_stream)
        width, height = image.size; logo_stream.seek(position)
        scale = min(max_width / width, max_height / height)
        return width * scale, height * scale
    except Exception:
        return max_width, max_height


def _style_profile(style: str) -> dict[str, Any]:
    profiles = {
        "Professional": {"accent": "#B91C1C", "title_size": 24, "body_size": 10.5, "leading": 15, "cover": True, "compact": False},
        "Minimal": {"accent": "#111827", "title_size": 17, "body_size": 9.5, "leading": 13, "cover": False, "compact": True},
        "Presentation": {"accent": "#991B1B", "title_size": 30, "body_size": 13, "leading": 19, "cover": True, "compact": False},
    }
    return profiles.get(style, profiles["Professional"])


def _build_pdf_with_options(document_text, title, cleaner=None, options=None):
    opts = _document_options(options); profile = _style_profile(opts["style"])
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image as RLImage, KeepTogether
        import html as _html
    except Exception:
        return build_text_pdf(document_text, title, cleaner)

    text = _clean_document_text(document_text, cleaner); buffer = io.BytesIO()
    margins = .48*inch if profile["compact"] else .7*inch
    pdf_doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=margins, leftMargin=margins,
        topMargin=.48*inch if profile["compact"] else .65*inch, bottomMargin=.55*inch,
        title=title, author=opts["company_name"])
    styles = getSampleStyleSheet(); accent = colors.HexColor(profile["accent"])
    styles.add(ParagraphStyle(name="ATPTitleX", parent=styles["Title"], textColor=accent,
        fontName="Helvetica-Bold", fontSize=profile["title_size"], leading=profile["title_size"]+4,
        alignment=TA_CENTER if opts["style"] != "Minimal" else TA_LEFT, spaceAfter=12))
    styles.add(ParagraphStyle(name="ATPBodyX", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=profile["body_size"], leading=profile["leading"], textColor=colors.HexColor("#111827"),
        spaceAfter=3 if profile["compact"] else 7))
    styles.add(ParagraphStyle(name="ATPH1X", parent=styles["Heading1"], textColor=accent,
        fontName="Helvetica-Bold", fontSize=13 if profile["compact"] else (20 if opts["style"] == "Presentation" else 16),
        leading=17 if profile["compact"] else 23, spaceBefore=8, spaceAfter=5))
    company_style = ParagraphStyle(name="ATPCompanyX", parent=styles["BodyText"], alignment=TA_CENTER,
        textColor=colors.HexColor("#6B7280"), fontSize=9.5, leading=13, spaceAfter=12)

    story=[]; logo_added=False
    if opts["include_logo"]:
        stream=_prepared_logo_stream(opts["logo_path"])
        if stream is None: raise RuntimeError("AutoTecPro logo was selected, but App/logo.png could not be loaded.")
        max_w = 2.4*inch if opts["style"] == "Presentation" else 2.0*inch
        max_h = .9*inch if opts["style"] == "Presentation" else .72*inch
        w,h=_logo_dimensions(stream,max_w,max_h); image=RLImage(stream,width=w,height=h)
        image.hAlign = "CENTER" if opts["style"] != "Minimal" else "LEFT"
        story.extend([image, Spacer(1, 7 if profile["compact"] else 14)]); logo_added=True
    story.append(Paragraph(_html.escape(title), styles["ATPTitleX"]))
    if opts["include_company_info"]:
        story.append(Paragraph(_html.escape(opts["company_name"]), company_style))
        story.append(Paragraph(_html.escape(opts["company_info"]), company_style))
    if profile["cover"] and (logo_added or opts["include_company_info"]): story.append(PageBreak())
    elif not profile["compact"]: story.append(Spacer(1, 10))

    for kind,value in _iter_markdown_blocks(text):
        clean=re.sub(r"\*\*(.*?)\*\*",r"\1",value); clean=re.sub(r"`([^`]+)`",r"\1",clean); safe=_html.escape(clean)
        if kind=="blank": story.append(Spacer(1, 2 if profile["compact"] else 6))
        elif kind.startswith("heading"): story.append(KeepTogether([Paragraph(safe,styles["ATPH1X"])]))
        elif kind in {"bullet","number"}: story.append(Paragraph(("• " if kind=="bullet" else "")+safe,styles["ATPBodyX"]))
        else: story.append(Paragraph(safe,styles["ATPBodyX"]))

    def draw_page(canvas,doc_obj):
        canvas.saveState()
        if opts["watermark"]:
            canvas.setFillColor(colors.Color(.45,.45,.45,alpha=.12)); canvas.setFont("Helvetica-Bold",46)
            canvas.translate(letter[0]/2,letter[1]/2); canvas.rotate(35); canvas.drawCentredString(0,0,opts["watermark"])
        canvas.setFillColor(colors.HexColor("#6B7280")); canvas.setFont("Helvetica",8)
        if opts["include_company_info"]: canvas.drawString(margins,.30*inch,opts["company_name"])
        if opts["style"] != "Minimal": canvas.drawRightString(letter[0]-margins,.30*inch,f"Page {doc_obj.page}")
        canvas.restoreState()
    pdf_doc.build(story,onFirstPage=draw_page,onLaterPages=draw_page)
    data=buffer.getvalue(); return data,max(1,data.count(b"/Type /Page"))


def _build_docx_with_options(document_text, title, cleaner=None, options=None):
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.section import WD_SECTION
    opts=_document_options(options); profile=_style_profile(opts["style"]); text=_clean_document_text(document_text,cleaner)
    document=Document(); section=document.sections[0]
    margin=.55 if profile["compact"] else .8
    section.top_margin=Inches(margin); section.bottom_margin=Inches(margin); section.left_margin=Inches(margin); section.right_margin=Inches(margin)
    logo_added=False
    if opts["include_logo"]:
        stream=_prepared_logo_stream(opts["logo_path"])
        if stream is None: raise RuntimeError("AutoTecPro logo was selected, but App/logo.png could not be loaded.")
        p=document.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER if opts["style"]!="Minimal" else WD_ALIGN_PARAGRAPH.LEFT
        p.add_run().add_picture(stream,width=Inches(2.2 if opts["style"]=="Presentation" else 1.8)); logo_added=True
    heading=document.add_heading(title,0); heading.alignment=WD_ALIGN_PARAGRAPH.CENTER if opts["style"]!="Minimal" else WD_ALIGN_PARAGRAPH.LEFT
    for run in heading.runs: run.font.color.rgb=RGBColor(185,28,28) if opts["style"]!="Minimal" else RGBColor(17,24,39)
    if opts["include_company_info"]:
        for line in (opts["company_name"],opts["company_info"]):
            p=document.add_paragraph(line); p.alignment=WD_ALIGN_PARAGRAPH.CENTER if opts["style"]!="Minimal" else WD_ALIGN_PARAGRAPH.LEFT
    if profile["cover"] and (logo_added or opts["include_company_info"]): document.add_page_break()
    for kind,value in _iter_markdown_blocks(text):
        value=re.sub(r"\*\*(.*?)\*\*",r"\1",value); value=re.sub(r"`([^`]+)`",r"\1",value)
        if kind=="blank": document.add_paragraph("")
        elif kind.startswith("heading"): document.add_heading(value,level=min(int(kind[-1]),3))
        elif kind=="bullet": document.add_paragraph(value,style="List Bullet")
        elif kind=="number": document.add_paragraph(value,style="List Number")
        else: document.add_paragraph(value)
    document.styles["Normal"].font.name="Arial"; document.styles["Normal"].font.size=Pt(profile["body_size"])
    if opts["watermark"]:
        header=section.header.paragraphs[0]; header.text=f"{opts['watermark']}  •  {opts['watermark']}  •  {opts['watermark']}"
        header.alignment=WD_ALIGN_PARAGRAPH.CENTER
        for run in header.runs: run.font.size=Pt(18); run.font.bold=True; run.font.color.rgb=RGBColor(190,190,190)
    if opts["include_company_info"]:
        footer=section.footer.paragraphs[0]; footer.text=f"{opts['company_name']} | {opts['company_info']}"; footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
    buffer=io.BytesIO(); document.save(buffer); return buffer.getvalue(),max(1,len(document.paragraphs))


def _build_pptx_with_options(document_text, title, cleaner=None, options=None):
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    opts=_document_options(options); profile=_style_profile(opts["style"]); text=_clean_document_text(document_text,cleaner)
    prs=Presentation(); prs.slide_width=Inches(13.333); prs.slide_height=Inches(7.5)
    title_slide=prs.slides.add_slide(prs.slide_layouts[0]); title_slide.shapes.title.text=title
    title_slide.shapes.title.text_frame.paragraphs[0].font.size=Pt(34 if opts["style"]=="Presentation" else (26 if opts["style"]=="Professional" else 22))
    subtitle=""
    if opts["include_company_info"]: subtitle=f"{opts['company_name']}\n{opts['company_info']}"
    if len(title_slide.placeholders)>1: title_slide.placeholders[1].text=subtitle
    if opts["include_logo"]:
        stream=_prepared_logo_stream(opts["logo_path"])
        if stream is None: raise RuntimeError("AutoTecPro logo was selected, but App/logo.png could not be loaded.")
        title_slide.shapes.add_picture(stream,Inches(10.6),Inches(.25),width=Inches(2.15))
    sections=_split_slide_sections(text)
    max_lines=5 if opts["style"]=="Presentation" else (9 if opts["style"]=="Minimal" else 7)
    for section_title,lines in sections:
        chunks=[lines[i:i+max_lines] for i in range(0,len(lines),max_lines)] or [[]]
        for idx,chunk in enumerate(chunks):
            slide=prs.slides.add_slide(prs.slide_layouts[1]); slide.shapes.title.text=section_title if idx==0 else f"{section_title} (continued)"
            slide.shapes.title.text_frame.paragraphs[0].font.size=Pt(28 if opts["style"]=="Presentation" else 22)
            frame=slide.placeholders[1].text_frame; frame.clear()
            for j,line in enumerate(chunk):
                p=frame.paragraphs[0] if j==0 else frame.add_paragraph(); p.text=re.sub(r"\*\*(.*?)\*\*",r"\1",line)
                p.font.size=Pt(24 if opts["style"]=="Presentation" else (16 if opts["style"]=="Minimal" else 19)); p.space_after=Pt(9 if opts["style"]=="Presentation" else 3)
            if opts["include_logo"]:
                stream=_prepared_logo_stream(opts["logo_path"]); slide.shapes.add_picture(stream,Inches(11.0),Inches(.16),width=Inches(1.55))
            if opts["include_company_info"]:
                box=slide.shapes.add_textbox(Inches(.45),Inches(7.05),Inches(8),Inches(.25)); box.text_frame.text=opts["company_name"]
                box.text_frame.paragraphs[0].font.size=Pt(9)
            if opts["watermark"]:
                box=slide.shapes.add_textbox(Inches(2.0),Inches(2.8),Inches(9.3),Inches(1.0)); p=box.text_frame.paragraphs[0]; p.text=opts["watermark"]
                p.alignment=PP_ALIGN.CENTER; p.font.size=Pt(44); p.font.bold=True; p.font.color.rgb=RGBColor(205,205,205)
    buffer=io.BytesIO(); prs.save(buffer); return buffer.getvalue(),len(prs.slides)


def _build_xlsx_with_options(document_text, title, cleaner=None, options=None):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
    opts=_document_options(options); profile=_style_profile(opts["style"]); text=_clean_document_text(document_text,cleaner); rows=_extract_table_rows(text)
    wb=Workbook(); ws=wb.active; ws.title="Document"; width=max(1,len(rows[0]) if rows else 1)
    ws["A1"]=title; ws.merge_cells(start_row=1,start_column=1,end_row=1,end_column=width)
    ws["A1"].font=Font(bold=True,size=22 if opts["style"]=="Presentation" else (14 if opts["style"]=="Minimal" else 17),color="B91C1C" if opts["style"]!="Minimal" else "111827")
    start_row=3
    if opts["include_company_info"]:
        ws["A2"]=f"{opts['company_name']} | {opts['company_info']}"; ws.merge_cells(start_row=2,start_column=1,end_row=2,end_column=width); start_row=4
    if opts["watermark"]:
        ws.sheet_properties.pageSetUpPr.fitToPage=True; ws.oddHeader.center.text=f"&KCCCCCC&24{opts['watermark']}"
    if opts["include_logo"]:
        stream=_prepared_logo_stream(opts["logo_path"])
        if stream is None: raise RuntimeError("AutoTecPro logo was selected, but App/logo.png could not be loaded.")
        from openpyxl.drawing.image import Image as XLImage
        image=XLImage(stream); image.width=180; image.height=55; ws.add_image(image,f"{get_column_letter(max(2,width))}1")
    header_fill="B91C1C" if opts["style"]!="Minimal" else "E5E7EB"; header_font="FFFFFF" if opts["style"]!="Minimal" else "111827"
    thin=Side(style="thin",color="D1D5DB")
    for r_idx,row in enumerate(rows,start=start_row):
        for c_idx,value in enumerate(row,start=1):
            cell=ws.cell(r_idx,c_idx,value=value); cell.alignment=Alignment(vertical="top",wrap_text=True)
            if r_idx==start_row and len(rows)>1:
                cell.font=Font(bold=True,color=header_font); cell.fill=PatternFill("solid",fgColor=header_fill)
            if opts["style"]=="Professional": cell.border=Border(bottom=thin)
    for c_idx in range(1,max((len(r) for r in rows),default=1)+1):
        max_len=max((len(str(ws.cell(r,c_idx).value or "")) for r in range(1,ws.max_row+1)),default=10)
        ws.column_dimensions[get_column_letter(c_idx)].width=min(max(max_len+2,12),52 if opts["style"]=="Presentation" else 40)
    ws.freeze_panes=f"A{start_row}"; buffer=io.BytesIO(); wb.save(buffer); return buffer.getvalue(),len(wb.sheetnames)


def _build_csv_with_options(document_text, title, cleaner=None, options=None):
    opts=_document_options(options); text=_clean_document_text(document_text,cleaner); rows=_extract_table_rows(text)
    buffer=io.StringIO(newline=""); writer=csv.writer(buffer)
    if opts["include_company_info"]: writer.writerow([opts["company_name"],opts["company_info"]]); writer.writerow([])
    if opts["watermark"]: writer.writerow([opts["watermark"]]); writer.writerow([])
    writer.writerows(rows); return buffer.getvalue().encode("utf-8-sig"),max(1,len(rows))

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
    title = derive_document_title(prompt_text, answer_text)
    filename = safe_document_filename(title, answer_text, resolved_format)
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
        "style": opts["style"],
        "branded": bool(opts["include_logo"] or opts["include_company_info"]),
        "logo_requested": bool(opts["include_logo"]),
        "logo_available": bool(
            opts["logo_path"] and Path(str(opts["logo_path"])).is_file()
        ),
        "generator_version": "2.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
