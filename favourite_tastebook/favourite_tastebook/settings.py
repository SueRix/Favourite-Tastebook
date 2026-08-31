import os
from pathlib import Path

from decouple import config
from django.urls import reverse_lazy

# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG')

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'authentication',
    'profile_manager',
    'recipe_manager',
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

ROOT_URLCONF = 'favourite_tastebook.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'authentication/templates/registration'),
            os.path.join(BASE_DIR, 'profile_manager/templates/profile'),
            os.path.join(BASE_DIR, 'recipe_manager/templates'),
            os.path.join(BASE_DIR, 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'favourite_tastebook.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases


DATABASES = {

    'default': {

        'ENGINE': config('DB_ENGINE', default='django.db.backends.postgresql'),
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT', default='5432'),

    }

}

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

APPEND_SLASH = False

LOGIN_REDIRECT_URL = reverse_lazy('home')
LOGOUT_REDIRECT_URL = reverse_lazy('login')
LOGIN_URL = reverse_lazy('login')

MAX_BIO_LEN = 1000
MAX_AVATAR_MB = 5

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Vector search (Pinecone via n8n webhook) ---
# Django never talks to Pinecone directly: it POSTs the keyword to a self-hosted
# n8n webhook, which embeds the query and runs the Pinecone similarity search.
N8N_PINECONE_WEBHOOK_URL = config('N8N_PINECONE_WEBHOOK_URL', default='')
N8N_WEBHOOK_AUTH_TOKEN = config('N8N_WEBHOOK_AUTH_TOKEN', default='')
N8N_WEBHOOK_TIMEOUT = config('N8N_WEBHOOK_TIMEOUT', default=5, cast=float)
VECTOR_SEARCH_TOP_K = config('VECTOR_SEARCH_TOP_K', default=20, cast=int)

# Calibration window for the match thermometer. Cosine similarity between
# related texts sits in a narrow band, so raw scores would pin every card to
# the middle of the scale. Mapping the useful band onto the full bar keeps the
# difference visible while staying comparable across searches (unlike
# normalising inside a single result set).
VECTOR_SCORE_FLOOR = config('VECTOR_SCORE_FLOOR', default=0.45, cast=float)
VECTOR_SCORE_CEILING = config('VECTOR_SCORE_CEILING', default=0.71, cast=float)

# Exponent applied to the calibrated ratio. A straight line through the window
# above would rate 0.48 at 12%; the curve pulls the weak tail down so the
# anchors are 0.45 -> 0%, 0.48 -> 5%, 0.71 -> 100%. Set to 1.0 for pure linear.
VECTOR_SCORE_CURVE = config('VECTOR_SCORE_CURVE', default=1.4, cast=float)

# --- n8n cooking agent: tool API ---
# Shared secret the n8n workflow presents on every tool call. Empty means the
# tool API refuses to serve at all (fail closed) rather than accepting anyone.
AGENT_SERVICE_TOKEN = config('AGENT_SERVICE_TOKEN', default='')

# Lifetime of the signed {user, session} context the chat view hands to n8n.
# It only needs to outlive one conversation, so keep it short: it is the window
# in which a leaked token could be replayed against the tool API.
AGENT_CONTEXT_MAX_AGE = config('AGENT_CONTEXT_MAX_AGE', default=3600, cast=int)

# How many recipes one tool call returns by default, and the ceiling the agent
# cannot argue past. Every row is prompt tokens on the next model turn.
AGENT_TOOL_MAX_RESULTS = config('AGENT_TOOL_MAX_RESULTS', default=5, cast=int)
AGENT_TOOL_RESULT_CEILING = config('AGENT_TOOL_RESULT_CEILING', default=10, cast=int)

CELERY_BROKER_URL = 'redis://redis:6379/0'
CELERY_RESULT_BACKEND = 'redis://redis:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'