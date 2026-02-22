import uuid
from django.db.models import Q
from django.db import models
from apps.documents.models import Document


class ReviewRunStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    PARTIAL = "partial", "Partial"


class ReviewRunStage(models.TextChoices):
    PREPROCESS = "preprocess", "Preprocess"
    EXTRACT = "extract", "Extract"
    RULES = "rules", "Rules"
    LLM = "llm", "LLM"
    PERSIST = "persist", "Persist"


class FindingSeverity(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"


class FindingSource(models.TextChoices):
    RULE = "rule", "Rule"
    LLM = "llm", "LLM"
    UNKNOWN = "unknown", "Unknown"


class ReviewRun(models.Model):
    """Represents a single analysis run for a given Document."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="review_runs")
    idempotency_key = models.CharField(max_length=255, null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=ReviewRunStatus.choices,
        default=ReviewRunStatus.QUEUED,
    )
    llm_model = models.CharField(max_length=50, null=True, blank=True)
    prompt_rev = models.CharField(max_length=200, null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    request_fingerprint = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    cache_key = models.CharField(max_length=255, null=True, blank=True)
    cache_hits = models.PositiveIntegerField(default=0)
    cache_misses = models.PositiveIntegerField(default=0)
    token_usage = models.JSONField(default=dict, blank=True)
    stage_timings = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    current_stage = models.CharField(
        max_length=20, choices=ReviewRunStage.choices, null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["document", "idempotency_key"],
                condition=Q(idempotency_key__isnull=False),
                name="uniq_reviewrun_document_idempotency_key",
            )
        ]
        indexes = [
            models.Index(fields=["status", "created_at"], name="reviewrun_status_created_idx"),
        ]


class Finding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE)

    # Links the finding to a specific run (nullable for backward compatibility)
    run = models.ForeignKey(
        ReviewRun,
        on_delete=models.CASCADE,
        related_name="findings",
        null=True,
        blank=True,
    )

    # Clause identity from the extractor step (UUID string)
    clause_id = models.CharField(max_length=255, null=True, blank=True)
    chunk_id = models.CharField(max_length=255, null=True, blank=True)
    
    clause_heading = models.CharField(max_length=255, null=True, blank=True)
    clause_body = models.TextField(null=True, blank=True)

    summary = models.TextField()
    explanation = models.TextField(null=True, blank=True)

    # Keep max_length=20 for migration compatibility (was "risk")
    severity = models.CharField(max_length=20, choices=FindingSeverity.choices)
    evidence = models.TextField()
    evidence_span = models.JSONField(null=True, blank=True)
    source = models.CharField(max_length=20, choices=FindingSource.choices)

    rule_code = models.CharField(max_length=64, null=True, blank=True)
    
    model = models.CharField(max_length=50, null=True, blank=True)
    confidence = models.FloatField(null=True)
    prompt_rev = models.CharField(max_length=200, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)


class ReviewChunk(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(ReviewRun, on_delete=models.CASCADE, related_name="chunks")
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="review_chunks")
    chunk_id = models.CharField(max_length=255)
    schema_version = models.CharField(max_length=32, default="v1")
    ordinal = models.PositiveIntegerField()
    heading = models.CharField(max_length=255, null=True, blank=True)
    body = models.TextField()
    start_offset = models.IntegerField(null=True, blank=True)
    end_offset = models.IntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["run", "chunk_id"],
                name="uniq_reviewchunk_run_chunk_id",
            )
        ]
        indexes = [
            models.Index(fields=["run", "ordinal"], name="reviewchunk_run_ordinal_idx"),
            models.Index(fields=["document", "chunk_id"], name="reviewchunk_doc_chunk_idx"),
        ]
