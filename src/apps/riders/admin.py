from django.contrib import admin
from .models import Ride, RideRequest, RideMessage, RideReview

admin.site.register(Ride)
admin.site.register(RideRequest)
admin.site.register(RideMessage)
admin.site.register(RideReview)
