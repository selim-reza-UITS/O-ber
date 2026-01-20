from django.contrib import admin
from .models import User,DriverProfile
# Register your models here.
admin.site.register(User)

# admin.py
@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'vehicle_type', 'ai_verified', 'admin_verified', 'is_active']
    list_filter = ['ai_verified', 'admin_verified', 'is_active']
    actions = ['approve_drivers']

    def approve_drivers(self, request, queryset):
        queryset.update(admin_verified=True, is_active=True)
        # Update the User model as well
        for profile in queryset:
            profile.user.is_driver = True
            profile.user.save()