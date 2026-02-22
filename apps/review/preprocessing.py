import hashlib
from typing import Dict, List, Optional

from apps.review.extractor import _split_into_blocks, is_heading_line, normalize_text

CHUNK_SCHEMA_VERSION = "v1"


def _stable_chunk_id(ordinal: int, heading: str, body: str) -> str:
    digest = hashlib.sha256(f"{ordinal}|{heading}|{body}".encode("utf-8")).hexdigest()
    return f"chk_{digest[:24]}"


def _spreadsheet_chunks_from_metadata(metadata: Dict, row_window_size: int = 5) -> List[Dict]:
    chunks: List[Dict] = []
    ordinal = 1

    for sheet in metadata.get("sheets", []):
        sheet_name = sheet.get("name") or "Sheet"
        rows = sheet.get("rows") or []
        if not rows:
            continue

        for idx in range(0, len(rows), row_window_size):
            window = rows[idx : idx + row_window_size]
            if not window:
                continue

            row_start = window[0].get("row_number")
            row_end = window[-1].get("row_number")
            heading = f"{sheet_name} rows {row_start}-{row_end}"

            body_lines: List[str] = []
            for row in window:
                row_num = row.get("row_number")
                row_text = row.get("text") or ""
                if row_text:
                    body_lines.append(f"Row {row_num}: {row_text}")
            body = "\n".join(body_lines).strip() or heading

            chunks.append(
                {
                    "chunk_id": _stable_chunk_id(ordinal, heading, body),
                    "schema_version": CHUNK_SCHEMA_VERSION,
                    "ordinal": ordinal,
                    "heading": heading,
                    "body": body,
                    "start_offset": None,
                    "end_offset": None,
                    "metadata": {
                        "source": "spreadsheet",
                        "evidence_pointer": {
                            "kind": "spreadsheet",
                            "sheet": sheet_name,
                            "row_start": row_start,
                            "row_end": row_end,
                        },
                    },
                }
            )
            ordinal += 1

    return chunks


def preprocess_document_to_chunks(
    text: str,
    source_type: str = "text",
    ingestion_metadata: Optional[Dict] = None,
) -> List[Dict]:
    """Split document text or spreadsheet rows into deterministic chunk artifacts."""

    if source_type == "spreadsheet" and isinstance(ingestion_metadata, dict):
        spreadsheet_chunks = _spreadsheet_chunks_from_metadata(ingestion_metadata)
        if spreadsheet_chunks:
            return spreadsheet_chunks

    normalized = normalize_text(text)
    if not normalized:
        return []

    blocks = _split_into_blocks(normalized)
    chunks: List[Dict] = []
    cursor = 0

    for idx, block in enumerate(blocks, start=1):
        lines = block.split("\n")
        first_line = lines[0].strip() if lines else ""

        heading: Optional[str] = first_line if is_heading_line(first_line) else None
        body = "\n".join(lines[1:]).strip() if heading else block

        if not heading:
            heading = f"Clause {idx}"
        if not body:
            body = heading

        start_offset = normalized.find(block, cursor)
        if start_offset == -1:
            start_offset = normalized.find(block)
        end_offset = start_offset + len(block) if start_offset >= 0 else None
        if end_offset is not None:
            cursor = end_offset

        chunks.append(
            {
                "chunk_id": _stable_chunk_id(idx, heading, body),
                "schema_version": CHUNK_SCHEMA_VERSION,
                "ordinal": idx,
                "heading": heading,
                "body": body,
                "start_offset": start_offset if start_offset >= 0 else None,
                "end_offset": end_offset,
                "metadata": {},
            }
        )

    if not chunks:
        chunks.append(
            {
                "chunk_id": _stable_chunk_id(1, "Document", normalized),
                "schema_version": CHUNK_SCHEMA_VERSION,
                "ordinal": 1,
                "heading": "Document",
                "body": normalized,
                "start_offset": 0,
                "end_offset": len(normalized),
                "metadata": {},
            }
        )

    return chunks
