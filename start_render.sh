#!/usr/bin/env bash
set -o errexit

echo "=== Running database migrations ==="
python manage.py migrate --no-input

echo "=== Loading species data ==="
python manage.py load_species_data

echo "=== Loading county data ==="
python manage.py load_county_data

echo "=== Starting web server ==="
exec gunicorn crisis_communication.wsgi:application
