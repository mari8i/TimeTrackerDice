"""
WSGI config for timetrackerdice project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

envvars = ['TIME_TRACKER_PROD', 'USE_MYSQL', 'MYSQL_HOST', 'MYSQL_USERNAME', 'MYSQL_PASSWORD', 'MYSQL_DATABASE']

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'timetrackerdice.settings')

def application(environ, start_response):
    for envvar in envvars:
        if envvar in environ:
            os.environ[envvar] = environ[envvar]

    _application = get_wsgi_application()
    return _application(environ, start_response)

#application = get_wsgi_application()

