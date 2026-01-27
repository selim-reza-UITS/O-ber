import os
import stripe
from pathlib import Path
from datetime import timedelta  # noqa: F401
from dotenv import load_dotenv
load_dotenv()
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

LOCAL_ALLOWED_HOSTS = ["*"]

ALLOWED_HOSTS = LOCAL_ALLOWED_HOSTS

# Application definition

INSTALLED_APPS = [
    'daphne', 
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'rest_framework',
    'channels',
    'src.apps.accounts',
    'src.apps.dashboard',
    'src.apps.drivers',
    'src.apps.payments',
    'src.apps.riders',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'src._config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates',],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
ASGI_APPLICATION = 'src._config.asgi.application'
WSGI_APPLICATION = 'src._config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

LOCAL_DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

LOCAL_POSTGRES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': os.getenv('POSTGRES_DB'),
        'USER': os.getenv('POSTGRES_USER'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD'),
        'HOST': os.getenv("POSTGRES_HOST"),  # The name of the service in docker-compose.yml
        'PORT': os.getenv("POSTGRES_PORT"),
    }
}

DATABASES = LOCAL_POSTGRES
# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Dhaka'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'


AUTH_USER_MODEL = 'accounts.User'

AUTHENTICATION_BACKENDS = [
    'src.apps.accounts.backends.EmailOrPhoneBackend',
    'django.contrib.auth.backends.ModelBackend',
]


REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(REDIS_HOST, REDIS_PORT)],
        },
    },
}

CELERY_BROKER_URL = os.getenv('REDIS_URL', f'redis://{REDIS_HOST}:{REDIS_PORT}/0')
CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', f'redis://{REDIS_HOST}:{REDIS_PORT}/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

GDAL_LIBRARY_PATH = "/usr/lib/x86_64-linux-gnu/libgdal.so"
GEOS_LIBRARY_PATH = "/usr/lib/x86_64-linux-gnu/libgeos_c.so"

STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET=os.getenv('STRIPE_WEBHOOK_SECRET')
stripe.api_key = STRIPE_SECRET_KEY



EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.hostinger.com"
EMAIL_USE_SSL = True
EMAIL_PORT = 465
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
ADMIN_SUPPORT_EMAIL = EMAIL_HOST_USER