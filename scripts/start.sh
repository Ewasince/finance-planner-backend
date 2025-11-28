#!/bin/bash

# Применяем миграции
python manage.py migrate

# Собираем статику
python manage.py collectstatic --noinput

# Запускаем Gunicorn с принудительным JSON
exec gunicorn core.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --capture-output \
    --preload \
    --config gunicorn.conf.py
