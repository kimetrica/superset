import logging
import os

from flask_appbuilder.security.manager import AUTH_DB, AUTH_OAUTH
from flask_appbuilder.security.sqla.manager import SecurityManager
from flask_migrate import migrate
from kombu import Queue
from werkzeug.contrib.cache import RedisCache


log = logging.getLogger(__name__)


# ---------------------------------------------------------
# Superset specific config
# ---------------------------------------------------------
ROW_LIMIT = 5000

# We launch Gunicorn from `run_superset.sh` so to change the
# Gunicorn config you should change the Docker Compose command.
# These settings apply to running the development server using:
# `superset runserver -d`
# SUPERSET_WORKERS = 4
# SUPERSET_WEBSERVER_PORT = 8088
# ---------------------------------------------------------

# ---------------------------------------------------------
# Flask App Builder configuration
# ---------------------------------------------------------
# Your App secret key
try:
    SECRET_KEY = os.environ['SECRET_KEY']
except KeyError:
    raise Exception('SECRET_KEY must be set in the environment.')

# The SQLAlchemy connection string to your database backend
# This connection defines the path to the database that stores your
# superset metadata (slices, connections, tables, dashboards, ...).
# Note that the connection information to connect to the datasources
# you want to explore are managed directly in the web UI
try:
    SQLALCHEMY_DATABASE_URI = os.environ['SQLALCHEMY_DATABASE_URI']
except KeyError:
    raise Exception('SQLALCHEMY_DATABASE_URI must be set in the environment.')

# Extract and use X-Forwarded-For/X-Forwarded-Proto headers?
ENABLE_PROXY_FIX = True

# ----------------------------------------------------
# AUTHENTICATION CONFIG
# ----------------------------------------------------


class KobocatSecurityManager(SecurityManager):
    """
    Flask Appbuilder Security Manager that can use Kobocat as an OAuth Provider

    Register the Flask application with kobocat at /o/applications/register/:

    - `name` - name of your application
    - `client_type` - Client Type: select confidential
    - `authorization_grant_type` - Authorization grant type: Authorization code
    - `redirect_uri` - Redirect urls: <scheme>://<server>/oath-authorized/kobocat
    """

    def get_oauth_user_info(self, provider, resp=None):
        log.debug("Get oauth user info for provider %s" % provider)
        if provider == 'kobocat':
            me = self.oauth_remotes[provider].get('api/v1/user')
            return {
                'username': me.data.get('username'),
                'email': me.data.get('email')
            }
        return super().get_oauth_user_info(provider, resp)


# You should register Superset as a client application with the provider first,
# and record the consumer_key and consumer_secret here. The client record on the
# provider should be configured with a Redirect URI of <scheme>://<server>/oath-authorized/<provider>
# E.g. https://dashboard.kimetrica.com/oauth-authorized/kobocat
# For OAuth2 providers, you need:
#     provider['token_key'] = 'access_token'
#     provider['remote_app']['request_token_url'] = None
OAUTH_PROVIDERS = []
if 'TWITTER_OAUTH_CONSUMER_KEY' in os.environ and os.environ['TWITTER_OAUTH_CONSUMER_KEY']:
    OAUTH_PROVIDERS.append({'name': 'twitter',
                            'icon': 'fa-twitter',
                            'remote_app': {
                                'consumer_key': os.environ['TWITTER_OAUTH_CONSUMER_KEY'],
                                'consumer_secret': os.environ['TWITTER_OAUTH_CONSUMER_SECRET'],
                                'base_url': '/kobocat/api/v1/',
                                'request_token_url': '/o/token',
                                'access_token_url': 'https://api.twitter.com/oauth/access_token',
                                'authorize_url': 'https://api.twitter.com/oauth/authenticate'}})
if 'GOOGLE_OAUTH_CONSUMER_KEY' in os.environ and os.environ['GOOGLE_OAUTH_CONSUMER_KEY']:
    OAUTH_PROVIDERS.append({'name': 'google',
                            'icon': 'fa-google',
                            'token_key': 'access_token',
                            'whitelist': ['@kimetrica.com'],
                            'remote_app': {
                                'consumer_key': os.environ['GOOGLE_OAUTH_CONSUMER_KEY'],
                                'consumer_secret': os.environ['GOOGLE_OAUTH_CONSUMER_SECRET'],
                                'base_url': 'https://www.googleapis.com/oauth2/v1/',
                                'request_token_url': None,
                                'request_token_params': {'scope': 'https://www.googleapis.com/auth/userinfo.email'},
                                'access_token_method': 'POST',
                                'access_token_url': 'https://accounts.google.com/o/oauth2/token',
                                'authorize_url': 'https://accounts.google.com/o/oauth2/auth'}})
if 'KOBOCAT_OAUTH_CONSUMER_KEY' in os.environ and os.environ['KOBOCAT_OAUTH_CONSUMER_KEY']:
    OAUTH_PROVIDERS.append({'name': 'kobocat',
                            'icon': 'fa-user',
                            'token_key': 'access_token',
                            'remote_app': {
                                'consumer_key': os.environ['KOBOCAT_OAUTH_CONSUMER_KEY'],
                                'consumer_secret': os.environ['KOBOCAT_OAUTH_CONSUMER_SECRET'],
                                'base_url': os.environ['KOBOCAT_BASE_URL'],
                                'request_token_url': None,  # Use OAUTH2
                                'access_token_method': 'POST',
                                'access_token_url': os.environ['KOBOCAT_BASE_URL'] + '/o/token/',
                                'authorize_url': os.environ['KOBOCAT_BASE_URL'] + '/o/authorize/'}})
    CUSTOM_SECURITY_MANAGER = KobocatSecurityManager

# The authentication type
# AUTH_OAUTH : Is for OAuth2
# AUTH_OID : Is for OpenID
# AUTH_DB : Is for database (username/password()
# AUTH_LDAP : Is for LDAP
# AUTH_REMOTE_USER : Is for using REMOTE_USER from web server
AUTH_TYPE = AUTH_OAUTH if OAUTH_PROVIDERS else AUTH_DB
AUTH_USER_REGISTRATION = True
AUTH_USER_REGISTRATION_ROLE = 'Public'

CACHE_CONFIG = {
    'CACHE_TYPE': 'redis',
    'CACHE_DEFAULT_TIMEOUT': 60 * 60 * 24,
    'CACHE_KEY_PREFIX': 'superset',
    'CACHE_REDIS_HOST': 'redis',
    'CACHE_REDIS_DB': 2}

TABLE_NAMES_CACHE_CONFIG = {
    'CACHE_TYPE': 'redis',
    'CACHE_DEFAULT_TIMEOUT': 60 * 60 * 24,
    'CACHE_KEY_PREFIX': 'superset_tables',
    'CACHE_REDIS_HOST': 'redis',
    'CACHE_REDIS_DB': 2}


# Celery Configuration to allow async SQL queries
# with caching of results
class CeleryConfig(object):
    # Make sure we make any queues specific to this application, so we can use a shared broker
    CELERY_DEFAULT_QUEUE = 'superset'
    CELERY_QUEUES = (Queue(CELERY_DEFAULT_QUEUE, routing_key=CELERY_DEFAULT_QUEUE),)
    # We must set the backend explicitly to override the setting from onadata.settings.common
    BROKER_BACKEND = 'redis'
    BROKER_URL = os.environ.get('REDIS_URL', 'redis://redis:6379') + '/' + os.environ.get('CELERY_BROKER_REDIS_DB', '1')
    CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://redis:6379') + '/' + os.environ.get('CELERY_RESULT_REDIS_DB', '1')
    CELERY_ACCEPT_CONTENT = ['application/json']
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_IMPORTS = ('superset.sql_lab', )
    CELERY_ANNOTATIONS = {'tasks.add': {'rate_limit': '10/s'}}
    # Need to account for: --app=superset --queues=superset --hostname=superset.${APP}${ENV}@%n -Ofair -l INFO


CELERY_CONFIG = CeleryConfig

# An instantiated derivative of werkzeug.contrib.cache.BaseCache
# if enabled, it can be used to store the results of long-running queries
# in SQL Lab by using the "Run Async" button/feature
RESULTS_BACKEND = RedisCache(host='redis', port=6379, key_prefix='superset_results')

# Set this API key to enable Mapbox visualizations
MAPBOX_API_KEY = ''

# Whether to bump the logging level to ERRROR on the flask_appbiulder package
# Set to False if/when debugging FAB related issues like
# permission management
SILENCE_FAB = False

# Include additional data sources
ADDITIONAL_MODULE_DS_MAP = {
    'contrib.connectors.pandas.models': ['PandasDatasource'],
}
ADDITIONAL_VERSION_LOCATIONS = ['%(here)s/../../contrib/migrations/versions']
