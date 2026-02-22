from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from apps.review.views import ReviewRunStatusView

def health(request):
    return JsonResponse({"status": "ok", "app": "ai-legal-assistant-mvp"})

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", health),
    path("v1/accounts/", include("apps.accounts.urls")),
    path("v1/documents/", include("apps.documents.urls")),
    path("v1/review/", include("apps.review.urls")),
    path("v1/review-runs/<uuid:run_id>", ReviewRunStatusView.as_view(), name="review-run-status"),
]
