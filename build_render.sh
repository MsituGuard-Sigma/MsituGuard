#!/bin/bash
set -o errexit

pip install -r requirements.txt
python3 manage.py collectstatic --noinput

# Try migrations, but don't fail if database is unreachable
python3 manage.py migrate --noinput || echo "Migration failed, will retry at runtime"