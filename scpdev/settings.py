"""
Django settings for scpdev project.

Generated by 'django-admin startproject' using Django 4.0.3.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.0/ref/settings/
"""

from pathlib import Path
import os
import mimetypes

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-)wy0h9z6x4o3t4@=s_keq0x$illy9yqyo!4g8wk%mo8l+8imun')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'true') == 'true'

ALLOWED_HOSTS = ['*']

# SILENCED_SYSTEM_CHECKS = ['templates.E003']


# Application definition

INSTALLED_APPS = [
    "jazzmin",

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',

    'guardian',

    'web',

    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'web.middleware.FixRawPathMiddleware',
    'django.middleware.security.SecurityMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
    'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'web.middleware.ForwardedPortMiddleware',
    'web.middleware.DropWikidotAuthMiddleware',
    'web.middleware.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'web.middleware.BotAuthTokenMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'web.middleware.MediaHostMiddleware',
    'web.middleware.UserContextMiddleware',
    'web.middleware.SpyRequestMiddleware',
]

ROOT_URLCONF = 'scpdev.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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


WSGI_APPLICATION = 'scpdev.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_PG_DATABASE', 'scpwiki'),
        'USER': os.environ.get('DB_PG_USERNAME', 'postgres'),
        'PASSWORD': os.environ.get('DB_PG_PASSWORD', 'zaq123'),
        'HOST': os.environ.get('DB_PG_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PG_PORT', '5432'),
        'ATOMIC_REQUESTS': True
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

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


AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
]


# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = 'ru'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Static and media files
STATIC_URL = "/-/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "static_dist"

STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

MEDIA_HOST = os.environ.get('MEDIA_HOST', None)
MEDIA_ROOT = BASE_DIR / "files"


def parse_size(size):
    import re
    match = re.fullmatch(r'(\d+)(.*)', size)
    if not match:
        raise ValueError('Invalid size specification: %s' % size)
    units = {"B": 1, "KB": 2 ** 10, "MB": 2 ** 20, "GB": 2 ** 30, "TB": 2 ** 40}
    number = match[1]
    unit = match[2].strip().upper()
    if not unit:
        unit = 'B'
    if unit not in units:
        raise ValueError('Invalid size specification: %s, allowed units: %s' % (size, ', '.join(units.keys())))
    return int(float(number)*units[unit])


ARTICLE_SOURCE_LIMIT = int(os.environ.get('ARTICLE_SOURCE_LIMIT', '200000'))

ABSOLUTE_MEDIA_UPLOAD_LIMIT = parse_size(os.environ.get('ABSOLUTE_MEDIA_UPLOAD_LIMIT', '0'))
MEDIA_UPLOAD_LIMIT = parse_size(os.environ.get('MEDIA_UPLOAD_LIMIT', '0'))


LOGIN_REDIRECT_URL = "/"
LOGIN_URL = "/-/login"

# Fixes slash at the end of URLs
APPEND_SLASH = False
REMOVE_SLASH = True


# Fixes
SECURE_CONTENT_TYPE_NOSNIFF = False
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# Default avatars
ANON_AVATAR = "/-/static/images/anon_avatar.png"
DEFAULT_AVATAR = "/-/static/images/default_avatar.png"
WIKIDOT_AVATAR = "/-/static/images/wikidot_avatar.png"


# Fixes static images
mimetypes.add_type("text/css", ".css", True)
mimetypes.add_type("text/javascript", ".js", True)


ARTICLE_IMPORT_REPLACE_CONFIG = {}
ARTICLE_REPLACE_CONFIG = {}

for v in os.environ.get('ARTICLE_REPLACE_CONFIG', '').split(','):
    if not v.strip():
        continue
    [k, v] = v.split('::')
    ARTICLE_REPLACE_CONFIG[k] = v

for v in os.environ.get('ARTICLE_IMPORT_REPLACE_CONFIG', '').split(','):
    if not v.strip():
        continue
    [k, v] = v.split('::')
    ARTICLE_IMPORT_REPLACE_CONFIG[k] = v


mail_backend = os.environ.get('EMAIL_ENGINE', 'console')
if mail_backend == 'console':
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
elif mail_backend == 'smtp':
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '1025'))
    EMAIL_HOST_USER = os.environ.get('EMAIL_USERNAME', '')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'false') == 'true'
    if 'EMAIL_DEFAULT_FROM' not in os.environ:
        raise KeyError('EMAIL_DEFAULT_FROM environment variable is required for SMTP')
    DEFAULT_FROM_EMAIL = os.environ['EMAIL_DEFAULT_FROM']
else:
    raise ValueError('Unknown email engine "%s"' % mail_backend)


GOOGLE_TAG_ID = os.environ.get('GOOGLE_TAG_ID', None)


AUTH_USER_MODEL = "web.User"

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'class': 'scpdev.logger.SimpleFormatter'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
    },
    'root': {
        'handlers': ['console'],
        'level': os.environ.get('LOGLEVEL', 'INFO'),
    },
}


JAZZMIN_SETTINGS = {
    "user_avatar": "avatar",

    "site_title": "RuFoundation",
    "site_brand": "Админка",
}


# Dict of supported ranged content-types in format: MIME, CHUNK_SIZE_IN_BYTES
RANGED_CONTENT_SERVING = {
    "audio/*": 2097152,                   # 2 MB
    "video/*": 4194304,                   # 4 MB
    # "image/*": 524288,                    # 512 KB  ### Some shit will happen if you try to uncomment this option
    "application/octet-stream": 4194304,  # 4 MB
    "application/zip": 8388608,           # 8 MB
    "application/gzip": 8388608,          # 8 MB
    "application/x-tar": 8388608,         # 8 MB
    "application/pdf": 1048576,           # 1 MB
}