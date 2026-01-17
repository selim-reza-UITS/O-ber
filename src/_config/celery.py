import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src._config.settings.local')

app = Celery('ober_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()