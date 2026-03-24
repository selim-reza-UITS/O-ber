from django.contrib.auth.base_user import BaseUserManager

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email must be set')
        email = self.normalize_email(email)
        
        # Set defaults for required fields if not provided
        if 'full_name' not in extra_fields or not extra_fields['full_name']:
            extra_fields['full_name'] = email.split('@')[0]
        if 'phone_number' not in extra_fields or not extra_fields['phone_number']:
            extra_fields['phone_number'] = f'admin_{email.split("@")[0]}'[:15]
        
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if not password:
            raise ValueError('Superuser must have a password')
        
        return self.create_user(email, password, **extra_fields)