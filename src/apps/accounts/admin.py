from django.contrib import admin
from .models import User, DriverProfile, PendingDriverUpdate, VehicleImage
# Register your models here.
admin.site.register(User)

# admin.py
@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'vehicle_type', 'ai_verified', 'admin_verified', 'is_active']
    list_filter = ['ai_verified', 'admin_verified', 'is_active']
    actions = ['approve_drivers']

    @admin.action(description="Approve selected drivers")
    def approve_drivers(self, request, queryset):
        # IMPORTANT: iterate and call .save() on each profile so that
        # DriverProfile.save() runs and syncs the User role flags
        # (is_driver=True, is_rider=False). A bulk queryset.update() would
        # bypass save() and leave is_rider=True, which makes an approved
        # driver still behave like a normal user in the apps.
        approved = 0
        for profile in queryset:
            profile.admin_verified = True
            profile.is_active = True
            profile.is_rejected = False
            profile.save()
            approved += 1
        self.message_user(request, f"{approved} driver(s) approved and activated.")

admin.site.register(PendingDriverUpdate)
admin.site.register(VehicleImage)