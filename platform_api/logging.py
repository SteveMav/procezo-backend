import json
import logging
from datetime import datetime, timezone


class SafeJSONFormatter(logging.Formatter):
    def format(self, record):
        data = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        for key in ("request_id", "route", "status", "duration_ms", "exception_type"):
            value = getattr(record, key, None)
            if value is not None:
                data[key] = value
        return json.dumps(data, ensure_ascii=False)
