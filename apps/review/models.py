import uuid
from django.db import models
from apps.documents.models import Document


class Finding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    
    clause_heading = models.CharField(max_length=255)
    clause_body = models.TextField()

    summary = models.TextField()
    severity = models.CharField(max_length=10)
    evidence = models.TextField()
    source = models.CharField(max_length=10)  # rule | llm
    
    model = models.CharField(max_length=50, null=True)
    confidence = models.FloatField(null=True)
    prompt_rev = models.CharField(max_length=200, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def to_dict(self):
        return {
            "id": str(self.id),
            "clause_heading": self.clause_heading,
            "clause_body": self.clause_body,
            "summary": self.summary,
            "severity": self.severity,
            "evidence": self.evidence,
            "source": self.source,
            "model": self.model,
            "confidence": self.confidence,
            "prompt_rev": self.prompt_rev,
        }
