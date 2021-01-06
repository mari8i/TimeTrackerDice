"""
Django settings for timetrackerdice project.

Generated by 'django-admin startproject' using Django 3.0.6.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""

import os
import sys

import environ
from django.urls import reverse_lazy

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False),
    SESSION_COOKIE_SECURE=(bool, True),
    CSRF_COOKIE_SECURE=(bool, True),
    STATIC_ROOT=(str, os.path.join(BASE_DIR, "static")),
    MEDIA_ROOT=(str, os.path.join(BASE_DIR, "media")),
    ALLOWED_HOSTS=(list, []),
    USE_X_FORWARDED_HOST=(bool, False),
    LOGS_DIR=(str, BASE_DIR),
    ENABLE_FILE_LOG=(bool, False),
)

# reading .env file
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

DEBUG = env("DEBUG")

SECRET_KEY = env("SECRET_KEY")

USE_X_FORWARDED_HOST = env("USE_X_FORWARDED_HOST")

ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "django_extensions",
    "rest_framework",
    "rest_framework.authtoken",
    'bootstrap4',

    'mapper',
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "timetrackerdice.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "timetrackerdice.wsgi.application"

BASE_LOG_DIR = env("LOGS_DIR")

ENABLE_FILE_LOG = env("ENABLE_FILE_LOG")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"console": {"format": "%(name)-12s %(levelname)-8s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "console"}},
    "loggers": {
        "": {"level": "DEBUG", "handlers": ["console"]},
        "BotLogger": {"level": "DEBUG", "handlers": ["console"]},
        # 'django.db': {
        #    'handlers': ['console'],
        #    'level': 'DEBUG'
        # },
    },
}

if ENABLE_FILE_LOG:
    LOGGING["formatters"]["file"] = {"format": "%(asctime)s %(name)-12s %(levelname)-8s %(message)s"}
    LOGGING["handlers"]["file"] = {
        "level": "INFO",
        "class": "logging.FileHandler",
        "formatter": "file",
        "filename": os.path.join(BASE_LOG_DIR, "timetrackerdice.log"),
    }
    LOGGING["loggers"]["timetrackerdiceLogger"]["handlers"] = ["console", "file"]

DATABASES = {"default": env.db(), "extra": env.db("SQLITE_URL", default="sqlite:////tmp/my-tmp-sqlite.db")}

LANGUAGE_CODE = "it"

TIME_ZONE = "Europe/Rome"

USE_I18N = True

USE_L10N = True

USE_TZ = True

if not DEBUG:
    STATIC_ROOT = env("STATIC_ROOT")

STATIC_URL = env("STATIC_URL", default="/static/")

STATICFILES_DIRS = (
    "static/",
)

MEDIA_ROOT = env("MEDIA_ROOT")
MEDIA_URL = env("MEDIA_URL", default="/media/")

LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

CACHES = {
    "default": env.cache(),
}

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_RENDERER_CLASSES": [
        # "rest_framework.renderers.BrowsableAPIRenderer",
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.TokenAuthentication"],
}

SESSION_COOKIE_SECURE = env("SESSION_COOKIE_SECURE")
CSRF_COOKIE_SECURE = env("CSRF_COOKIE_SECURE")
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SILENCED_SYSTEM_CHECKS = [
    "security.W004",  # SECURE_HSTS_SECONDS
    "security.W008",  # SECURE_SSL_REDIRECT
    "security.W022",  # SECURE_REFERRER_POLICY
]

STATICFILES_STORAGE = env("STATICFILES_STORAGE", default="django.contrib.staticfiles.storage.StaticFilesStorage")

BASE_URL = env("BASE_URL", default="")

EMAIL_CONFIG = env.email_url("EMAIL_URL", default="smtp://user@:password@localhost:25")

vars().update(EMAIL_CONFIG)

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@timetrackerdice.it")

DOMAIN = env("DOMAIN", default="localhost:4200")
DOMAIN_PREFIX = env("DOMAIN_PREFIX", default="")
SITE_NAME = env("SITE_NAME", default="Time tracker dice")

# Include BOOTSTRAP4_FOLDER in path
BOOTSTRAP4_FOLDER = os.path.abspath(os.path.join(BASE_DIR, "..", "bootstrap4"))
if BOOTSTRAP4_FOLDER not in sys.path:
    sys.path.insert(0, BOOTSTRAP4_FOLDER)

# Settings for django-bootstrap4
BOOTSTRAP4 = {
    "error_css_class": "bootstrap4-error",
    "required_css_class": "bootstrap4-required",
    "javascript_in_head": True,
    "include_jquery": True,
}
