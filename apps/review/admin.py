from django.contrib import admin

from .models import Finding, ReviewChunk, ReviewRun


@admin.register(ReviewRun)
class ReviewRunAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "document",
        "status",
        "current_stage",
        "idempotency_key",
        "cache_hits",
        "cache_misses",
        "llm_model",
        "prompt_rev",
        "started_at",
        "completed_at",
        "created_at",
    )
    list_filter = ("status", "llm_model", "prompt_rev", "request_fingerprint")
    search_fields = ("id", "document__title", "idempotency_key", "cache_key", "request_fingerprint")


@admin.register(Finding)
class FindingAdmin(admin.ModelAdmin):
    list_display = ("id", "document", "severity", "source", "rule_code", "created_at")
    list_filter = ("severity", "source")
    search_fields = ("id", "document__title", "clause_heading", "summary")


@admin.register(ReviewChunk)
class ReviewChunkAdmin(admin.ModelAdmin):
    list_display = ("id", "run", "document", "chunk_id", "schema_version", "ordinal", "created_at")
    list_filter = ("schema_version",)
    search_fields = ("id", "chunk_id", "document__title")
