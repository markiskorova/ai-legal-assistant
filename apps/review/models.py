from django.db import models
import uuid

class Finding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey('documents.Document', on_delete=models.CASCADE)
    clause_id = models.CharField(max_length=255)
    summary = models.TextField()
    risk = models.CharField(max_length=20)
    evidence = models.TextField()
    source = models.CharField(max_length=20)  # rule | llm
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.document.title} — {self.risk}'