#!/bin/bash

# Применяем миграции
python manage.py migrate

# Применяем миграции
python manage.py bootstrap_dev_data

# Запускаем Gunicorn
exec gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 1
