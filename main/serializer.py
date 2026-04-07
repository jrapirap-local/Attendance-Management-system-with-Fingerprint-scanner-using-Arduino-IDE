# app/serializers.py
from rest_framework import serializers
from .models import Fingerprint

class FingerprintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fingerprint
        fields = '__all__'
        extra_kwargs = {
            'user': {'required': False}
        }