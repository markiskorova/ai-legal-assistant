import hashlib
import math
from typing import Iterable, List, Sequence

from django.conf import settings
from django.db import connection
from openai import OpenAI


def build_finding_embedding_input(summary: str, explanation: str, evidence: str) -> str:
    return "\n".join(
        part.strip()
        for part in [summary or "", explanation or "", evidence or ""]
        if part and part.strip()
    )


def generate_embeddings(texts: Sequence[str]) -> List[List[float]]:
    if not texts:
        return []

    provider = getattr(settings, "REVIEW_EMBEDDING_PROVIDER", "mock").lower()
    dimensions = max(1, int(getattr(settings, "REVIEW_EMBEDDING_DIM", 1536)))

    if provider == "openai":
        api_key = getattr(settings, "OPENAI_API_KEY", None)
        if api_key:
            model = getattr(settings, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
            try:
                client = OpenAI(api_key=api_key)
                response = client.embeddings.create(model=model, input=list(texts))
                return [_normalize_dims(item.embedding, dimensions) for item in response.data]
            except Exception:
                # Keep the pipeline resilient if embedding calls fail.
                pass

    return [_mock_embedding(text, dimensions) for text in texts]


def sync_pgvector_embeddings(findings: Iterable) -> int:
    if connection.vendor != "postgresql" or not _pgvector_column_exists():
        return 0

    updated = 0
    with connection.cursor() as cursor:
        for finding in findings:
            embedding = getattr(finding, "embedding", None)
            if not embedding:
                continue
            cursor.execute(
                "UPDATE review_finding SET embedding_vector = %s::vector WHERE id = %s",
                [_vector_literal(embedding), str(finding.id)],
            )
            updated += 1
    return updated


def _normalize_dims(vector: Sequence[float], dimensions: int) -> List[float]:
    values = [float(v) for v in vector[:dimensions]]
    if len(values) < dimensions:
        values.extend([0.0] * (dimensions - len(values)))
    return values


def _mock_embedding(text: str, dimensions: int) -> List[float]:
    seed = hashlib.sha256((text or "").encode("utf-8")).digest()
    values: List[float] = []
    state = seed
    index = 0

    while len(values) < dimensions:
        if index >= len(state):
            state = hashlib.sha256(state).digest()
            index = 0
        byte_value = state[index]
        index += 1
        values.append((byte_value / 127.5) - 1.0)

    norm = math.sqrt(sum(v * v for v in values))
    if norm == 0:
        return [0.0] * dimensions
    return [v / norm for v in values]


def _vector_literal(embedding: Sequence[float]) -> str:
    return "[" + ",".join(f"{float(v):.8f}" for v in embedding) + "]"


def _pgvector_column_exists() -> bool:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'review_finding'
              AND column_name = 'embedding_vector'
            LIMIT 1
            """
        )
        return cursor.fetchone() is not None
