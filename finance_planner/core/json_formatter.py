from datetime import datetime
import json
import logging
import socket


class SimpleJSONFormatter(logging.Formatter):
    """Простой JSON форматтер без внешних зависимостей"""

    def __init__(self, service_name="django-app"):
        self.service_name = service_name
        self.hostname = socket.gethostname()
        self.ip = self._get_ip_address()

    def _get_ip_address(self):
        try:
            return socket.gethostbyname(self.hostname)
        except Exception:
            return "unknown"

    def format(self, record):
        # Базовые поля лога
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service_name": self.service_name,
            "host": self.hostname,
            "ip": self.ip,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Добавляем информацию об исключении если есть
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Добавляем дополнительные поля из extra
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        return json.dumps(log_data, ensure_ascii=False)
