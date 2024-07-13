from django.urls import reverse_lazy
from rest_framework import serializers

from ..models import Pdf


class PdfSerializer(serializers.ModelSerializer):
    file = serializers.StringRelatedField()

    class Meta:
        model = Pdf
        fields = ("id", "url", "status", "name", "file")
        extra_kwargs = {"url": {"view_name": "pdf-detail"}}
