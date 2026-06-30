import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent

LOCAL_FALLBACK_SECRET_KEY = 'django-insecure-local-dev-only-change-me'
PROJECT_ENV_OVERRIDE_KEYS = {
    'OPENAI_API_KEY',
    'GOF_AI_ENABLED',
    'GOF_AI_MODEL',
}


def load_env_file(path):
    if not path.exists():
        return

    try:
        from dotenv import load_dotenv
    except ImportError:
        load_with_dotenv = False
    else:
        load_dotenv(path, override=False)
        load_with_dotenv = True

    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue

        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key in PROJECT_ENV_OVERRIDE_KEYS:
            os.environ[key] = value
            continue

        if not load_with_dotenv:
            os.environ.setdefault(key, value)


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def env_list(name, default=None):
    value = os.environ.get(name)
    if not value:
        return default or []
    return [item.strip() for item in value.split(',') if item.strip()]


load_env_file(BASE_DIR / '.env')

DEBUG = env_bool('DJANGO_DEBUG', False)
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = LOCAL_FALLBACK_SECRET_KEY
    else:
        raise ImproperlyConfigured('Set DJANGO_SECRET_KEY before running Django.')

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS')
if DEBUG:
    for local_host in ['127.0.0.1', 'localhost']:
        if local_host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(local_host)
elif not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['getonlinefast.eu', 'www.getonlinefast.eu']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'ai_starter',
    'blog',
    'content',
    'core',
    'print_design',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.template.context_processors.i18n',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.site_flags',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DB_ENGINE = os.environ.get('DB_ENGINE', 'django.db.backends.sqlite3')

if DB_ENGINE == 'django.db.backends.sqlite3':
    DATABASES = {
        'default': {
            'ENGINE': DB_ENGINE,
            'NAME': os.environ.get('DB_NAME', str(BASE_DIR / 'db.sqlite3')),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': DB_ENGINE,
            'NAME': os.environ.get('DB_NAME', ''),
            'USER': os.environ.get('DB_USER', ''),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', ''),
            'PORT': os.environ.get('DB_PORT', ''),
        }
    }

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

LANGUAGE_CODE = 'en'

TIME_ZONE = 'Europe/Amsterdam'

USE_I18N = True

USE_TZ = True

LANGUAGES = [
    ('en', 'English'),
    ('nl', 'Dutch'),
    ('fr', 'French'),
    ('pt', 'Portuguese'),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

STATIC_URL = os.environ.get('STATIC_URL', '/static/')
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / os.environ.get('STATIC_ROOT', 'staticfiles')

MEDIA_URL = os.environ.get('MEDIA_URL', '/media/')
MEDIA_ROOT = BASE_DIR / os.environ.get('MEDIA_ROOT', 'media')

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.zoho.eu')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'webmaster@localhost')
CONTACT_EMAIL_TO = os.environ.get('CONTACT_EMAIL_TO', DEFAULT_FROM_EMAIL)
GETONLINEFAST_WEBSITE_PACKAGE_PAYMENT_URL = os.environ.get('GETONLINEFAST_WEBSITE_PACKAGE_PAYMENT_URL', '').strip()
GETONLINEFAST_HMD_KLUSBEDRIJF_PAYMENT_URL = os.environ.get('GETONLINEFAST_HMD_KLUSBEDRIJF_PAYMENT_URL', '').strip()

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '').strip()
GOF_AI_MODEL = os.environ.get('GOF_AI_MODEL', 'gpt-4.1-mini').strip() or 'gpt-4.1-mini'
GOF_AI_ENABLED = env_bool('GOF_AI_ENABLED', bool(OPENAI_API_KEY))

CSRF_TRUSTED_ORIGINS = env_list(
    'DJANGO_CSRF_TRUSTED_ORIGINS',
    ['https://getonlinefast.eu', 'https://www.getonlinefast.eu'] if not DEBUG else [],
)

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = env_bool('DJANGO_SESSION_COOKIE_SECURE', True)
CSRF_COOKIE_SECURE = env_bool('DJANGO_CSRF_COOKIE_SECURE', True)
SECURE_SSL_REDIRECT = env_bool('DJANGO_SECURE_SSL_REDIRECT', False)
SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_SECURE_HSTS_SECONDS', '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', False)
SECURE_HSTS_PRELOAD = env_bool('DJANGO_SECURE_HSTS_PRELOAD', False)
SITE_NOINDEX = env_bool('DJANGO_SITE_NOINDEX', True)

# HSTS and Django-level SSL redirects are intentionally deferred until HTTPS is
# confirmed end-to-end through CyberPanel/OpenLiteSpeed.
SILENCED_SYSTEM_CHECKS = ['security.W004', 'security.W008']

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
