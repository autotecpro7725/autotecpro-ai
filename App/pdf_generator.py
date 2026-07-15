"""
AutoTecPro AI dedicated PDF Generator.

This module is intentionally independent of Streamlit, OpenAI, Supabase,
WooCommerce, and the workspace UI. It handles only:
- explicit PDF-request detection;
- safe filenames;
- text cleanup and wrapping;
- multi-page PDF construction;
- serializable document records for chat history;
- document marker serialization/restoration.
"""

from __future__ import annotations

import base64
import json
import re
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

DOCUMENT_MARKER_PREFIX = "\n<!--ATP_PDF_DOCUMENTS:"
DOCUMENT_MARKER_SUFFIX = ":ATP_PDF_DOCUMENTS-->\n"


def is_pdf_document_generation_request(prompt_text: Any) -> bool:
    """Return True only for an explicit request to create/export a PDF."""
    value = re.sub(r"\s+", " ", str(prompt_text or "")).strip().lower()
    if not value:
        return False

    read_only_phrases = (
        "summarize this pdf",
        "summarise this pdf",
        "read this pdf",
        "analyze this pdf",
        "analyse this pdf",
        "review this pdf",
        "what does this pdf",
        "extract from this pdf",
    )
    if any(phrase in value for phrase in read_only_phrases):
        return False

    explicit_phrases = (
        "create a pdf",
        "create pdf",
        "generate a pdf",
        "generate pdf",
        "make a pdf",
        "make pdf",
        "produce a pdf",
        "prepare a pdf",
        "export as pdf",
        "export to pdf",
        "downloadable pdf",
        "pdf file",
        "pdf document",
        "save as pdf",
        "turn this into a pdf",
        "convert this to pdf",
    )
    if any(phrase in value for phrase in explicit_phrases):
        return True

    creation_terms = (
        "create", "generate", "make", "produce", "prepare",
        "write", "build", "compile", "export",
    )
    document_terms = (
        "manual", "guide", "report", "document", "handbook",
        "proposal", "training material", "sop",
    )
    return (
        "pdf" in value
        and any(term in value for term in creation_terms)
        and any(term in value for term in document_terms)
    )


def safe_document_filename(prompt_text: Any, answer_text: Any = "") -> str:
    """Create a readable, filesystem-safe PDF filename."""
    source = str(prompt_text or "").strip() or str(answer_text or "").strip()
    words = re.findall(r"[A-Za-z0-9]+", source)[:8]
    stem = "_".join(words).strip("_") or "AutoTecPro_AI_Document"
    stem = re.sub(r"_+", "_", stem)[:88].strip("_")
    if not stem.lower().endswith(".pdf"):
        stem += ".pdf"
    return Path(stem).name


def _clean_pdf_text(
    value: Any,
    visible_text_cleaner: Callable[[Any], str] | None = None,
) -> str:
    """Convert chat Markdown into stable plain text for PDF output."""
    raw = (
        visible_text_cleaner(value)
        if callable(visible_text_cleaner)
        else str(value or "")
    )
    cleaned = str(raw or "")
    cleaned = re.sub(r"```[A-Za-z0-9_-]*", "", cleaned)
    cleaned = cleaned.replace("```", "")
    cleaned = re.sub(r"^\s{0,3}#{1,6}\s*", "", cleaned, flags=re.M)
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"__(.*?)__", r"\1", cleaned)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    cleaned = cleaned.replace("•", "-")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _pdf_escape_text(value: Any) -> str:
    """Escape a PDF literal string using a conservative Windows-1252 subset."""
    encoded = str(value or "").encode(
        "cp1252",
        errors="replace",
    ).decode("latin-1")
    return (
        encoded.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\r", "")
    )


def _wrap_pdf_lines(text: Any, max_chars: int = 92) -> list[str]:
    """Wrap text while preserving bullets and blank lines."""
    width = max(24, int(max_chars or 92))
    lines: list[str] = []

    for raw_line in str(text or "").splitlines():
        stripped = raw_line.rstrip()
        if not stripped:
            lines.append("")
            continue

        leading = ""
        content = stripped.strip()
        if content.startswith(("- ", "* ")):
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
    """
    Build a valid multi-page PDF using Python's standard library only.

    The implementation deliberately avoids a new deployment dependency.
    Documents can exceed ten pages; pagination is based on wrapped line count.
    """
    clean_title = re.sub(
        r"\s+",
        " ",
        str(title or "AutoTecPro AI Document"),
    ).strip()
    clean_text = _clean_pdf_text(
        document_text,
        visible_text_cleaner=visible_text_cleaner,
    )
    if not clean_text:
        clean_text = "No document content was generated."

    page_width = 612
    page_height = 792
    left_margin = 54
    top_y = 738
    bottom_y = 54
    body_font_size = 10
    line_height = 14
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

    catalog_id = reserve()
    pages_id = reserve()
    font_id = reserve()
    page_ids: list[int] = []
    content_ids: list[int] = []

    for _ in pages:
        page_ids.append(reserve())
        content_ids.append(reserve())

    objects[font_id] = (
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    )

    for page_number, (page_id, content_id, page_lines) in enumerate(
        zip(page_ids, content_ids, pages),
        start=1,
    ):
        commands = [
            "BT",
            f"/F1 {body_font_size} Tf",
            f"{left_margin} {top_y} Td",
            f"({_pdf_escape_text(clean_title)}) Tj",
            f"0 -{line_height * 2} Td",
        ]

        for line in page_lines:
            commands.append(f"({_pdf_escape_text(line)}) Tj")
            commands.append(f"0 -{line_height} Td")

        footer = f"Page {page_number} of {len(pages)}"
        commands.extend([
            "ET",
            "BT",
            "/F1 8 Tf",
            f"{page_width - 110} 30 Td",
            f"({_pdf_escape_text(footer)}) Tj",
            "ET",
        ])

        stream = "\n".join(commands).encode("latin-1", errors="replace")
        objects[content_id] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"\nendstream"
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
        pdf.extend(
            f"{offsets[object_id]:010d} 00000 n \n".encode("ascii")
        )

    pdf.extend(
        (
            f"trailer\n<< /Size {next_id} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF"
        ).encode("ascii")
    )
    return bytes(pdf), len(pages)


def create_pdf_document_record(
    prompt_text: Any,
    answer_text: Any,
    visible_text_cleaner: Callable[[Any], str] | None = None,
) -> dict[str, Any]:
    """Create one serializable PDF record for chat rendering and history."""
    filename = safe_document_filename(prompt_text, answer_text)
    title = (
        Path(filename).stem.replace("_", " ").strip()
        or "AutoTecPro AI Document"
    )
    pdf_bytes, page_count = build_text_pdf(
        answer_text,
        title=title,
        visible_text_cleaner=visible_text_cleaner,
    )
    encoded = base64.b64encode(pdf_bytes).decode("ascii")
    return {
        "name": filename,
        "mime_type": "application/pdf",
        "data_url": f"data:application/pdf;base64,{encoded}",
        "page_count": int(page_count),
        "size_bytes": len(pdf_bytes),
        "generated": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def serialize_documents_marker(documents: Iterable[dict[str, Any]] | None) -> str:
    """Serialize generated documents into an invisible history marker."""
    records = list(documents or [])
    if not records:
        return ""
    try:
        return (
            "\n\n"
            + DOCUMENT_MARKER_PREFIX
            + json.dumps(records, ensure_ascii=False)
            + DOCUMENT_MARKER_SUFFIX
        )
    except Exception:
        return ""


def extract_documents_from_message_content(
    content: Any,
) -> tuple[str, list[dict[str, Any]]]:
    """Restore PDF records while preserving messages created before this feature."""
    value = str(content or "")
    pattern = (
        re.escape(DOCUMENT_MARKER_PREFIX)
        + r"(.*?)"
        + re.escape(DOCUMENT_MARKER_SUFFIX)
    )
    match = re.search(pattern, value, flags=re.DOTALL)
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
        if not data_url.startswith("data:application/pdf;base64,"):
            continue

        try:
            page_count = int(document.get("page_count") or 0)
        except (TypeError, ValueError):
            page_count = 0
        try:
            size_bytes = int(document.get("size_bytes") or 0)
        except (TypeError, ValueError):
            size_bytes = 0

        clean_documents.append({
            "name": Path(
                str(document.get("name") or "AutoTecPro_AI_Document.pdf")
            ).name,
            "mime_type": "application/pdf",
            "data_url": data_url,
            "page_count": page_count,
            "size_bytes": size_bytes,
            "generated": bool(document.get("generated", True)),
            "created_at": document.get("created_at"),
        })

    return visible_text, clean_documents
