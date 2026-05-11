#!/bin/bash
set -o errexit

# Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Rebuild ML artifacts with the same scikit-learn version used in deploy.
# This prevents old pickle files from crashing or falling back at runtime.
pushd Tree_Prediction/training
python train_tree_model.py
popd

# Collect static files
python manage.py collectstatic --noinput
