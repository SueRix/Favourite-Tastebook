import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'favourite_tastebook.settings')

app = Celery('favourite_tastebook')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()