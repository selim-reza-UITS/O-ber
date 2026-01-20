from django.contrib import admin
from .models import TermsAndConditionsModel,PrivacyAndPolicyModel,AboutUs
# Register your models here.
admin.site.register(TermsAndConditionsModel)
admin.site.register(PrivacyAndPolicyModel)
admin.site.register(AboutUs)
