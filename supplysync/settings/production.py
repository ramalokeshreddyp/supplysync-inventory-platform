from .base import *
from urllib.parse import urlparse

DEBUG = False

SECRET_KEY = os.environ.get('SECRET_KEY')

db_url = os.environ.get('DATABASE_URL')
if db_url:
    parsed = urlparse(db_url)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': parsed.path.lstrip('/'),
            'USER': parsed.username,
            'PASSWORD': parsed.password,
            'HOST': parsed.hostname,
            'PORT': parsed.port or '5432',
            'OPTIONS': {
                'options': '-c search_path=supplysync,public'
            }
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'supplysync_db',
            'USER': 'supplysync_user',
            'PASSWORD': 'supplysync_pass',
            'HOST': 'localhost',
            'PORT': '5432',
            'OPTIONS': {
                'options': '-c search_path=supplysync,public'
            }
        }
    }

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')
