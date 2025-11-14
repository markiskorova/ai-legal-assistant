from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def health(request):
    return JsonResponse({"status": "ok", "app": "ai-legal-assistant-mvp"})

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", health),
    path("v1/accounts/", include("apps.accounts.urls")),
    path("v1/documents/", include("apps.documents.urls")),
    path("v1/review/", include("apps.review.urls")),
]
