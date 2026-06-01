import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'supplysync.settings.development')

app = Celery('supplysync')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.task_serializer = 'json'
app.conf.result_serializer = 'json'
app.conf.accept_content = ['json']
app.conf.timezone = 'Asia/Kolkata'

app.autodiscover_tasks()
