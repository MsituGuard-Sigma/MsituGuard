#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "=== Starting build process ==="

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

echo "=== Checking Django installation ==="
python --version
pip show django

echo "=== Testing Django commands ==="
python manage.py --version
python manage.py help

echo "=== Checking INSTALLED_APPS ==="
python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crisis_communication.settings'); from django.conf import settings; print('staticfiles' in str(settings.INSTALLED_APPS))"

echo "=== Running collectstatic ==="
python manage.py collectstatic --no-input --verbosity 2

echo "=== Running migrations ==="
python manage.py migrate --no-input