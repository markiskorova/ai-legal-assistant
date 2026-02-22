import uuid
from django.db import models


class DocumentSourceType(models.TextChoices):
    TEXT = "text", "Text"
    PDF = "pdf", "PDF"
    SPREADSHEET = "spreadsheet", "Spreadsheet"


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    text = models.TextField()
    source_type = models.CharField(
        max_length=20,
        choices=DocumentSourceType.choices,
        default=DocumentSourceType.TEXT,
    )
    ingestion_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
