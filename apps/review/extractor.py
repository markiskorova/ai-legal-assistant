import re
import uuid
from typing import List, Dict, Optional


def normalize_text(text: str) -> str:
    """
    Basic normalization:
    - normalize line endings
    - strip trailing spaces
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Strip trailing spaces on each line
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines).strip()


HEADING_SECTION_RE = re.compile(
    r"^(section\s+)?\d+(\.\d+)*\s*[\).\:-]?\s+.+$", re.IGNORECASE
)


def is_heading_line(line: str) -> bool:
    """
    Heuristic to decide if a line is a heading.
    Tries to catch:
    - 'SECTION 1. TERMINATION'
    - 'Section 5.2 Termination'
    - ALL CAPS short lines
    - Lines ending with ':' (e.g. 'Termination:')
    """
    stripped = line.strip()
    if not stripped:
        return False

    # If matches "Section 1.2 X" pattern
    if HEADING_SECTION_RE.match(stripped):
        return True

    # ALL CAPS short-ish line
    if len(stripped) <= 120 and stripped.upper() == stripped and " " in stripped:
        return True

    # Ends with ':' and short enough
    if stripped.endswith(":") and len(stripped) <= 120:
        return True

    return False


def _split_into_blocks(text: str) -> List[str]:
    """
    Split text into blocks separated by blank lines.
    """
    blocks = re.split(r"\n\s*\n+", text)
    return [b.strip() for b in blocks if b.strip()]


def extract_clauses(text: str) -> List[Dict]:
    """
    Main clause extraction function.

    Input:
        raw document text (string)

    Output:
        List[Dict] with:
        {
          "id": "uuid",
          "heading": "Termination",
          "body": "Full clause text..."
        }
    """
    normalized = normalize_text(text)
    blocks = _split_into_blocks(normalized)

    clauses: List[Dict] = []

    for idx, block in enumerate(blocks, start=1):
        lines = block.split("\n")
        first_line = lines[0].strip()

        if is_heading_line(first_line):
            heading: Optional[str] = first_line
            body = "\n".join(lines[1:]).strip()
        else:
            heading = None
            body = block

        # Fallback heading label if none detected
        if not heading:
            heading = f"Clause {idx}"

        # Ignore empty bodies (just in case)
        if not body:
            body = heading

        clauses.append(
            {
                "id": str(uuid.uuid4()),
                "heading": heading,
                "body": body,
            }
        )

    # If everything somehow collapsed into nothing, create a single clause
    if not clauses and normalized:
        clauses.append(
            {
                "id": str(uuid.uuid4()),
                "heading": "Document",
                "body": normalized,
            }
        )

    return clauses
