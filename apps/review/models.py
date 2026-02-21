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
