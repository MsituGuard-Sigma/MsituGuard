from rest_framework import serializers
from .models import User, Tree


class TreeUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tree
        fields = ['photo']

    def validate(self, attrs):
        """Optional: additional validation can go here"""
        if not attrs.get('photo'):
            raise serializers.ValidationError("Photo is required.")
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'user_type', 'tree_count', 'badge']
