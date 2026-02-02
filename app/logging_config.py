from __future__ import annotations

import json
import logging
import sys
from typing import Any


def _json_default(obj: Any) -> str:
    try:
        return str(obj)
    except Exception:
        return "<unserializable>"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        for key in ("trace_id", "message_id", "telefone", "order_id", "status_code", "body", "model", "request_id"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, default=_json_default)


def init_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root.handlers = [handler]
