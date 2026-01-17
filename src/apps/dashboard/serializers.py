from rest_framework import serializers
from .models import TermsAndConditionsModel, PrivacyAndPolicyModel, AboutUs, HelpSupport

class TermsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsAndConditionsModel
        fields = ['content']

class PrivacySerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivacyAndPolicyModel
        fields = ['content']

class AboutUsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AboutUs
        fields = ['content']

class HelpSupportSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpSupport
        fields = ['id', 'message', 'created_at', 'is_resolved']
        read_only_fields = ['id', 'created_at', 'is_resolved']