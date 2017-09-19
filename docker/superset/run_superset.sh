#!/bin/bash

echo Building documentation
sphinx-build -b html -d docs/_build/doctrees -E docs superset/static/help

# Use custom migrations setup
echo Running database migrations
superset db upgrade heads

echo Setting roles and permissions
superset init

echo Starting Gunicorn
exec gunicorn superset:app \
    --name ${APP}${ENV} \
    --bind 0.0.0.0:8000 \
    --limit-request-line 0 \
    --limit-request-field_size 0 \
    --access-logformat "${ACCESS_LOGFORMAT}" \
    $*
