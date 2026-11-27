"""
Django settings for zit_core project.
"""

from pathlib import Path
import os
import sys

# Detect if running in PyInstaller compiled executable
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    BASE_DIR = Path(sys._MEIPASS)
    # Store SQLite DB in user home directory so settings & API keys persist across runs/repos
    DATA_DIR = Path.home() / ".blamestorm"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH = Path(os.environ.get("BLAMESTORM_DB_PATH", str(DATA_DIR / "blamestorm.sqlite3")))
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
    DB_PATH = Path(os.environ.get("BLAMESTORM_DB_PATH", str(BASE_DIR / "db.sqlite3")))

SECRET_KEY = "django-insecure-0b84&by@1r9)+fwz2wdpl29*0awu1awrmkqj)8fck8k(u@xtxk"

DEBUG = True

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "zit_app",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "zit_core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "zit_app" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "zit_app.context_processors.zit_context",
            ],
        },
    },
]

WSGI_APPLICATION = "zit_core.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DB_PATH,
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [
    BASE_DIR / "zit_app" / "static",
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 86400 * 30
