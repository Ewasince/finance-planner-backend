import json
import socket
import sys
from datetime import datetime
from logging import Logger
import gunicorn.glogging

# Базовые поля для всех логов
SERVICE_NAME = "finsecret-django"
HOSTNAME = socket.gethostname()


def get_ip_address():
    try:
        return socket.gethostbyname(HOSTNAME)
    except:
        return "unknown"


class JSONLogger(gunicorn.glogging.Logger):
    """
    Кастомный JSON логгер для Gunicorn
    """

    def setup(self, cfg):
        super().setup(cfg)

    def access(self, resp, req, environ, request_time):
        # Форматируем access логи в JSON
        status = resp.status
        if isinstance(status, str):
            status = status.split(None, 1)[0]

        access_data = {
            "timestamp": datetime.now().isoformat(),
            "level": "INFO",
            "logger": "gunicorn.access",
            "message": f"{environ['REQUEST_METHOD']} {environ['PATH_INFO']} {status}",
            "service_name": SERVICE_NAME,
            "host": HOSTNAME,
            "ip": get_ip_address(),
            "remote_address": environ.get('REMOTE_ADDR', '-'),
            "method": environ['REQUEST_METHOD'],
            "path": environ['PATH_INFO'],
            "status_code": int(status) if status.isdigit() else status,
            "response_size": getattr(resp, 'sent', None),
            "user_agent": environ.get('HTTP_USER_AGENT', '-'),
            "query_string": environ.get('QUERY_STRING', '') or '-',
            "http_referer": environ.get('HTTP_REFERER', '-'),
        }

        # Убираем пустые поля
        access_data = {k: v for k, v in access_data.items() if v not in ('', '-', None)}

        self.access_log.info(json.dumps(access_data, ensure_ascii=False))

    def critical(self, msg, *args, **kwargs):
        self._log_json("CRITICAL", msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self._log_json("ERROR", msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self._log_json("WARNING", msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self._log_json("INFO", msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self._log_json("DEBUG", msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        self._log_json("ERROR", msg, *args, **kwargs, exc_info=True)

    def log(self, lvl, msg, *args, **kwargs):
        self._log_json(lvl, msg, *args, **kwargs)

    def _log_json(self, level, msg, *args, **kwargs):
        """
        Внутренний метод для логирования в JSON формате
        """
        # Форматируем сообщение если есть аргументы
        if args:
            try:
                msg = msg % args
            except:
                pass

        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "logger": "gunicorn." + kwargs.get('logger_name', 'general'),
            "message": msg,
            "service_name": SERVICE_NAME,
            "host": HOSTNAME,
            "ip": get_ip_address(),
        }

        # Добавляем информацию об исключении
        exc_info = kwargs.get('exc_info')
        if exc_info:
            import traceback
            if exc_info is True:
                exc_info = sys.exc_info()
            if exc_info:
                log_data["exception"] = ''.join(traceback.format_exception(*exc_info))

        # Добавляем дополнительные поля
        extra_data = kwargs.get('extra', {})
        if extra_data:
            log_data.update(extra_data)

        # Логируем в соответствующий логгер
        if level == 'CRITICAL':
            self.error_log.critical(json.dumps(log_data, ensure_ascii=False))
        elif level == 'ERROR':
            self.error_log.error(json.dumps(log_data, ensure_ascii=False))
        elif level == 'WARNING':
            self.error_log.warning(json.dumps(log_data, ensure_ascii=False))
        elif level == 'INFO':
            self.error_log.info(json.dumps(log_data, ensure_ascii=False))
        elif level == 'DEBUG':
            self.error_log.debug(json.dumps(log_data, ensure_ascii=False))


# Конфигурация Gunicorn
bind = "0.0.0.0:8000"
workers = 3
worker_class = "sync"
accesslog = "-"
errorlog = "-"
loglevel = "info"
capture_output = True
preload_app = True
logger_class = JSONLogger

# Дополнительные настройки
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 2
