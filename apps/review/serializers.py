from rest_framework import serializers


class ReviewRunSerializer(serializers.Serializer):
    document_id = serializers.UUIDField()
