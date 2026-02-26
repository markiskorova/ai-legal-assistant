from rest_framework import serializers

from .models import Finding, ReviewRun


class ReviewRunRequestSerializer(serializers.Serializer):
    """Request body for POST /v1/review/run."""

    document_id = serializers.UUIDField()
    idempotency_key = serializers.CharField(required=False, allow_blank=False, max_length=255)


class ReviewRunSerializer(serializers.ModelSerializer):
    """Serializer for ReviewRun metadata."""

    document_id = serializers.UUIDField(source="document.id", read_only=True)
    findings_count = serializers.SerializerMethodField()

    def get_findings_count(self, obj):
        return obj.findings.count()

    class Meta:
        model = ReviewRun
        fields = [
            "id",
            "document_id",
            "idempotency_key",
            "status",
            "current_stage",
            "cache_key",
            "cache_hits",
            "cache_misses",
            "llm_model",
            "prompt_rev",
            "error",
            "token_usage",
            "stage_timings",
            "started_at",
            "completed_at",
            "created_at",
            "findings_count",
        ]


class FindingSerializer(serializers.ModelSerializer):
    run_id = serializers.UUIDField(source="run.id", read_only=True, allow_null=True)

    class Meta:
        model = Finding
        fields = [
            "id",
            "run_id",
            "clause_id",
            "chunk_id",
            "clause_heading",
            "clause_body",
            "summary",
            "explanation",
            "recommendation",
            "severity",
            "evidence",
            "evidence_span",
            "source",
            "rule_code",
            "model",
            "confidence",
            "prompt_rev",
            "created_at",
        ]
