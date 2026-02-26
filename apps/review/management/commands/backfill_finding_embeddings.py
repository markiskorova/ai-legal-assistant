from typing import List

from django.core.management.base import BaseCommand

from apps.review.embeddings import (
    build_finding_embedding_input,
    generate_embeddings,
    sync_pgvector_embeddings,
)
from apps.review.models import Finding


class Command(BaseCommand):
    help = "Backfill embeddings for persisted findings and sync pgvector column when available."

    def add_arguments(self, parser):
        parser.add_argument("--run-id", dest="run_id", default=None)
        parser.add_argument("--document-id", dest="document_id", default=None)
        parser.add_argument("--batch-size", dest="batch_size", type=int, default=100)
        parser.add_argument("--overwrite", action="store_true")

    def handle(self, *args, **options):
        batch_size = max(1, int(options["batch_size"]))
        queryset = Finding.objects.all().order_by("created_at", "id")

        run_id = options.get("run_id")
        if run_id:
            queryset = queryset.filter(run_id=run_id)

        document_id = options.get("document_id")
        if document_id:
            queryset = queryset.filter(document_id=document_id)

        if not options.get("overwrite"):
            queryset = queryset.filter(embedding__isnull=True)

        total = queryset.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("No findings require embedding backfill."))
            return

        updated = 0
        pgvector_synced = 0
        ids = list(queryset.values_list("id", flat=True))
        for index in range(0, len(ids), batch_size):
            batch_ids = ids[index : index + batch_size]
            rows: List[Finding] = list(
                Finding.objects.filter(id__in=batch_ids).order_by("created_at", "id")
            )
            texts = [
                build_finding_embedding_input(
                    summary=f.summary,
                    explanation=f.explanation or "",
                    evidence=f.evidence or "",
                )
                for f in rows
            ]
            vectors = generate_embeddings(texts)
            for finding, vector in zip(rows, vectors):
                finding.embedding = vector
            Finding.objects.bulk_update(rows, ["embedding"])
            updated += len(rows)
            pgvector_synced += sync_pgvector_embeddings(rows)

        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill complete. embeddings_updated={updated}, pgvector_synced={pgvector_synced}"
            )
        )
