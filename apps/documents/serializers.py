from rest_framework import serializers
from .models import Document

class DocumentUploadSerializer(serializers.Serializer):
    title = serializers.CharField()
    file = serializers.FileField()

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["id", "title", "created_at"]
