from rest_framework import serializers

from .models import Finding, ReviewRun


class ReviewRunRequestSerializer(serializers.Serializer):
    """Request body for POST /v1/review/run."""

    document_id = serializers.UUIDField()


class ReviewRunSerializer(serializers.ModelSerializer):
    """Serializer for ReviewRun metadata."""

    class Meta:
        model = ReviewRun
        fields = [
            "id",
            "status",
            "llm_model",
            "prompt_rev",
            "error",
            "created_at",
        ]


class FindingSerializer(serializers.ModelSerializer):
    run_id = serializers.UUIDField(source="run.id", read_only=True, allow_null=True)

    class Meta:
        model = Finding
        fields = [
            "id",
            "run_id",
            "clause_id",
            "clause_heading",
            "clause_body",
            "summary",
            "explanation",
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
