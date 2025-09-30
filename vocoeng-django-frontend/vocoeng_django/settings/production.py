"""
Production settings for VocoEng Django Frontend

These settings are used for production deployment on Google Cloud Run.
"""

from .base import *
import json

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Get Cloud Run service URL from environment
CLOUD_RUN_SERVICE_URL = os.getenv('K_SERVICE_URL', '')
if CLOUD_RUN_SERVICE_URL:
    ALLOWED_HOSTS = [CLOUD_RUN_SERVICE_URL]
else:
    ALLOWED_HOSTS = ['vocoeng-django-frontend-*.run.app']

# Database configuration for Cloud SQL
# Uses Cloud SQL Proxy connection
if os.getenv('DATABASE_URL'):
    # Parse DATABASE_URL for Cloud SQL connection
    import urllib.parse
    url = urllib.parse.urlparse(os.getenv('DATABASE_URL'))
    
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': url.path[1:],  # Remove leading slash
            'USER': url.username,
            'PASSWORD': url.password,
            'HOST': url.hostname,
            'PORT': url.port or '5432',
            'OPTIONS': {
                'sslmode': 'require',
            },
        }
    }
else:
    # Fallback to environment variables
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'vocoeng_db'),
            'USER': os.getenv('DB_USER', 'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', '/cloudsql/vocoeng-dev:us-central1:vocoeng-db'),
            'PORT': os.getenv('DB_PORT', '5432'),
            'OPTIONS': {
                'sslmode': 'require',
            },
        }
    }

# Security settings for production
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Static files served by Cloud Storage or CDN
STATIC_URL = 'https://storage.googleapis.com/vocoeng-static/static/'
MEDIA_URL = 'https://storage.googleapis.com/vocoeng-media/media/'

# CORS settings for production
CORS_ALLOWED_ORIGINS = [
    "https://vocoeng-frontend.web.app",
    "https://vocoeng-frontend.firebaseapp.com",
]

# Cache configuration using Redis
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://localhost:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
        },
        'KEY_PREFIX': 'vocoeng',
        'TIMEOUT': 300,
    }
}

# Email configuration for production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

# Logging configuration for production
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': structlog.stdlib.ProcessorFormatter,
            'processor': structlog.processors.JSONRenderer(),
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django_structlog': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Celery configuration for background tasks
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Secret management using Google Secret Manager
def get_secret(secret_name: str, version: str = "latest") -> str:
    """Retrieve secret from Google Secret Manager"""
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{PROJECT_ID}/secrets/{secret_name}/versions/{version}"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"Failed to retrieve secret {secret_name}: {e}")
        return os.getenv(secret_name.upper().replace('-', '_'), '')

# Override SECRET_KEY with value from Secret Manager
SECRET_KEY = get_secret('django-secret-key') or SECRET_KEY

# Override database password with value from Secret Manager
if not os.getenv('DATABASE_URL'):
    db_password = get_secret('database-password')
    if db_password:
        DATABASES['default']['PASSWORD'] = db_password

# Override email password with value from Secret Manager
email_password = get_secret('email-password')
if email_password:
    EMAIL_HOST_PASSWORD = email_password

# Admin interface customization
ADMIN_INTERFACE = {
    'TITLE': 'VocoEng Admin',
    'SUBTITLE': 'Conversational AI Platform',
    'LOGO': 'admin/img/logo.png',
    'FAVICON': 'admin/img/favicon.png',
}

# Performance optimizations
CONN_MAX_AGE = 60  # Database connection pooling
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
