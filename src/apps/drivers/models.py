from django.utils import timezone
from django.db import models
from src.apps.accounts.models import DriverProfile

class DriverShift(models.Model):
    """Tracks when a driver goes online and offline to calculate active hours."""
    driver = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name='shifts')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)

    @property
    def duration(self):
        if self.end_time:
            return self.end_time - self.start_time
        return timezone.now() - self.start_time
