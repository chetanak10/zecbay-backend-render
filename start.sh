#!/bin/bash
python manage.py collectstatic --no-input
python manage.py migrate
gunicorn zecbay_admin.wsgi:application --bind 0.0.0.0:$PORT
