# -*- coding: utf-8 -*-

import pathlib
from dotenv import find_dotenv, load_dotenv

import json, logging, os


## load envars ------------------------------------------------------
dotenv_path = pathlib.Path(__file__).resolve().parent.parent.parent / '.env'
assert dotenv_path.exists(), f'file does not exist, ``{dotenv_path}``'
load_dotenv(find_dotenv(str(dotenv_path), raise_error_if_not_found=True), override=True)

## Build paths inside the project like this: os.path.join(BASE_DIR, ...)
# BASE_DIR = os.path.dirname(os.path.dirname(__file__))
BASE_DIR = os.path.dirname( os.path.dirname(os.path.abspath(__file__)) )  # path to the project (no end-slash)

## SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ['USEPWEB__SECRET_KEY']

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = json.loads( os.environ['USEPWEB__DEBUG_JSON'] )  # "true" or "false" to True or False
# TEMPLATE_DEBUG = DEBUG

ADMINS = json.loads( os.environ['USEPWEB__ADMINS_JSON'] )
MANAGERS = ADMINS

ALLOWED_HOSTS = json.loads( os.environ['USEPWEB__ALLOWED_HOSTS'] )  # list


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'usep_app',
)

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

WSGI_APPLICATION = 'config.passenger_wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases

DATABASES = json.loads( os.environ['USEPWEB__DATABASES_JSON'] )


# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/New_York'

USE_I18N = True

USE_L10N = True

USE_TZ = False


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/

STATIC_URL = os.environ['USEPWEB__STATIC_URL']
STATIC_ROOT = os.environ['USEPWEB__STATIC_ROOT']  # needed for collectstatic command
STATICFILES_DIRS = json.loads( os.environ['USEPWEB__STATICFILES_DIRS_JSON'] )


# Templates

# TEMPLATE_DIRS = json.loads( os.environ['USEPWEB__TEMPLATE_DIRS'] )  # list  ## from Django-1.9.x
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [ '%s/usep_app' % BASE_DIR ],
        # 'DIRS': TEMPLATE_DIRS,
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

# Email
EMAIL_HOST = os.environ['USEPWEB__EMAIL_HOST']
SERVER_EMAIL = os.environ['USEPWEB__EMAIL_FROM_ADDRESS']
EMAIL_PORT = int( os.environ['USEPWEB__EMAIL_PORT'] )


# sessions

# <https://docs.djangoproject.com/en/1.9/ref/settings/#std:setting-SESSION_SAVE_EVERY_REQUEST>
# Thinking: not that many concurrent users, and no pages where session info isn't required, so overhead is reasonable.
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# logging

## disable module loggers
# existing_logger_names = logging.getLogger().manager.loggerDict.keys()
# print '- EXISTING_LOGGER_NAMES, `%s`' % existing_logger_names
logging.getLogger('requests').setLevel( logging.WARNING )

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'standard': {
            'format' : "[%(asctime)s] %(levelname)s [%(module)s-%(funcName)s()::%(lineno)d] %(message)s",
            'datefmt' : "%d/%b/%Y %H:%M:%S"
        },
    },
    'handlers': {
        'logfile': {
            'level':'DEBUG',
            'class':'logging.FileHandler',  # note: configure server to use system's log-rotate to avoid permissions issues
            'filename': os.environ.get('USEPWEB__LOG_PATH'),
            'formatter': 'standard',
        },
        'console':{
            'level':'DEBUG',
            'class':'logging.StreamHandler',
            'formatter': 'standard'
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        }
    },
    'loggers': {
        'usep_app': {
            'handlers': ['logfile'],
            'level': os.environ.get('USEPWEB__LOG_LEVEL'),
            'propagate': False,
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
    }
}

