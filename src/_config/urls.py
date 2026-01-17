from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path("accounts/",include("src.apps.accounts.urls")),
    path("dashboard/",include("src.apps.dashboard.urls")),
    # path("drivers/",include("src.apps.drivers.urls")),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)