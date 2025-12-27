#!/bin/bash
set -o errexit

pip install -r requirements.txt
export DJANGO_SETTINGS_MODULE=crisis_communication.settings
python3 manage.py collectstatic --noinput

# Try migrations, but don't fail if database is unreachable
python3 manage.py migrate --noinput || echo "Migration failed, will retry at runtime"