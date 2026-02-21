from django.contrib import admin

from .models import Finding, ReviewRun


@admin.register(ReviewRun)
class ReviewRunAdmin(admin.ModelAdmin):
    list_display = ("id", "document", "status", "idempotency_key", "llm_model", "prompt_rev", "created_at")
    list_filter = ("status", "llm_model", "prompt_rev")
    search_fields = ("id", "document__title", "idempotency_key")


@admin.register(Finding)
class FindingAdmin(admin.ModelAdmin):
    list_display = ("id", "document", "severity", "source", "rule_code", "created_at")
    list_filter = ("severity", "source")
    search_fields = ("id", "document__title", "clause_heading", "summary")
