from django.urls import path
from .views import TermsView, PrivacyView, AboutUsView, HelpSupportView

urlpatterns = [
    path('terms/', TermsView.as_view(), name='terms'),
    path('privacy/', PrivacyView.as_view(), name='privacy'),
    path('about-us/', AboutUsView.as_view(), name='about-us'),
    path('support/', HelpSupportView.as_view(), name='support'),
]