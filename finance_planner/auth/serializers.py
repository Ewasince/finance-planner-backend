from rest_framework import serializers


class AuthResponse(serializers.Serializer):
    access = serializers.CharField(required=True)
    refresh = serializers.CharField(required=True)
