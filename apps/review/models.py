import uuid
from django.db import models
from apps.documents.models import Document


class ReviewRun(models.Model):
    """Represents a single analysis run for a given Document."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="review_runs")

    status = models.CharField(max_length=20, default="completed")  # completed | failed
    llm_model = models.CharField(max_length=50, null=True, blank=True)
    prompt_rev = models.CharField(max_length=200, null=True, blank=True)
    error = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def to_dict(self):
        return {
            "id": str(self.id),
            "status": self.status,
            "model": self.llm_model,
            "prompt_rev": self.prompt_rev,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


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
    severity = models.CharField(max_length=20)
    evidence = models.TextField()
    source = models.CharField(max_length=20)  # rule | llm

    rule_code = models.CharField(max_length=64, null=True, blank=True)
    
    model = models.CharField(max_length=50, null=True, blank=True)
    confidence = models.FloatField(null=True)
    prompt_rev = models.CharField(max_length=200, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def to_dict(self):
        return {
            "id": str(self.id),
            "run_id": str(self.run_id) if self.run_id else None,
            "clause_id": self.clause_id,
            "clause_heading": self.clause_heading,
            "clause_body": self.clause_body,
            "summary": self.summary,
            "severity": self.severity,
            "explanation": self.explanation,
            "evidence": self.evidence,
            "source": self.source,
            "rule_code": self.rule_code,
            "model": self.model,
            "confidence": self.confidence,
            "prompt_rev": self.prompt_rev,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
