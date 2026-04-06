import os
import sys

from django.core.wsgi import get_wsgi_application

# print( 'the initial env, ```{}```'.format( pprint.pformat(dict(os.environ)) ) )

PROJECT_DIR_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

## update path
sys.path.append(PROJECT_DIR_PATH)

## reference django settings
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'  # so django can access its settings

# print( 'the final env, ```{}```'.format( pprint.pformat(dict(os.environ)) ) )

## gogogo
application = get_wsgi_application()
