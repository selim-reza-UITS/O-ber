import random
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings

class OTPService:
    @staticmethod
    def generate_otp(email):
        otp = str(random.randint(100000, 999999))
        cache.set(f"otp_{email}", otp, timeout=300)
        return otp

    @staticmethod
    def verify_otp(email, otp):
        cached_otp = cache.get(f"otp_{email}")
        return cached_otp == otp

    @staticmethod
    def send_otp_email(email, otp):
        send_mail(
            'Your O-ber Reset Code',
            f'Your OTP is {otp}. It expires in 5 minutes.',
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )

class SupportService:
    @staticmethod
    def send_support_email(user_email, message):
        """Sends an email notification to the Admin about a new support ticket"""
        subject = f"New Support Request from {user_email}"
        full_message = f"User Email: {user_email}\n\nMessage:\n{message}"
        
        send_mail(
            subject,
            full_message,
            user_email,
            [settings.ADMIN_SUPPORT_EMAIL],
            fail_silently=False,
        )