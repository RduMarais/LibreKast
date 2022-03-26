"""
Django settings for pollsite project.

Generated by 'django-admin startproject' using Django 3.0.8.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# for docker deployment :
isDocker = os.getenv('IS_DOCKER')


# SECURITY WARNING: keep the secret key used in production secret!
# TODO when deploying
SECRET_KEY = os.environ.get("SECRET_KEY", default='3zaz_n48y63wv5xl(s9=zfrkixc-p10p1g^thb=eqs*=c3t0gp')

# SECURITY WARNING: don't run with debug turned on in production!
# TODO when deploying
DEBUG = os.environ.get("DEBUG",default=False)

# TODO when deploying add your hostname
ALLOWED_HOSTS = ['localhost', '127.0.0.1']
# TODO ADD this variable to your env vars (ex : 'librekast.pour-info.tech')
if(os.environ.get("ALLOWED_HOSTS_LOCAL")):
    ALLOWED_HOSTS.append(os.environ.get("ALLOWED_HOSTS_LOCAL"))

# migration to django > 3.2
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# For channels deploymment
ASGI_APPLICATION = 'pollsite.asgi.application'



# Application definition

INSTALLED_APPS = [
    'channels',
    'home.apps.HomeConfig',
    'poll.apps.PollConfig',
    'django_toggle_switch_widget',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'markdownfield',
    'adminsortable',
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

ROOT_URLCONF = 'pollsite.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.static',
            ],
        },
    },
]

WSGI_APPLICATION = 'pollsite.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Europe/Paris'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR + "/static",
    # os.path.join(BASE_DIR, '/static'),
    # '/Users/romain/Stratus/info/server/tests_beekast/LibreKast/pollsite/static/',
]

# for testing only, can be omitted for deployment
if(DEBUG):
    STATIC_ROOT = '/Users/romain/Stratus/info/server/tests_beekast/LibreKast/pollsite/static/'

# TODO place here the absolute path of the static files you serve
if(isDocker):
    STATIC_ROOT = './static/'

# media settings
MEDIA_URL = '/media/'
MEDIA_ROOT = 'media/'

# For Markdown formatting
# TODO if need to change before deployment
SITE_URL = "http://localhost"

# Channels configuration
if(isDocker):
    channel_host = ('app-redis', 6379)
else:
    channel_host = ('127.0.0.1', 6379)


CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [channel_host],
        },
    },
}

