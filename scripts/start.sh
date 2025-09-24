#!/bin/bash

# Применяем миграции
python manage.py migrate

# Собираем статику
python manage.py collectstatic --noinput

# Запускаем Gunicorn
exec gunicorn myproject.wsgi:application --bind 0.0.0.0:8000 --workers 3
