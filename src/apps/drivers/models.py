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

class RideReview(models.Model):
    """Rider reviews for the driver."""
    ride = models.OneToOneField('riders.Ride', on_delete=models.CASCADE, related_name='review')
    driver = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(default=5) # 1 to 5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)