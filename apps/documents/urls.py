from django.urls import path
from .views import DocumentUploadView, DocumentFindingsView

urlpatterns = [
    path("upload", DocumentUploadView.as_view(), name="document-upload"),
    path("<uuid:document_id>/findings", DocumentFindingsView.as_view(), name="document-findings"),
]
