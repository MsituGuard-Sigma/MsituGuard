#!/usr/bin/env bash
# Exit on error
set -o errexit

# Upgrade pip
python3 -m pip install --upgrade pip

# Install dependencies
python3 -m pip install -r requirements.txt

# Set Django settings module
export DJANGO_SETTINGS_MODULE=crisis_communication.settings

# Collect static files (note: --no-input with hyphen)
python3 manage.py collectstatic --no-input

# Try migrations, but don't fail if database is unreachable
python3 manage.py migrate --no-input || echo "Migration failed, will retry at runtime"