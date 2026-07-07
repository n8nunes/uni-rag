import logging
import json
import sys
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_object = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "logger_name": record.name
        }
        # Capture extra contextual metrics if they exist (e.g., user_id, classification)
        if hasattr(record, "extra_context"):
            log_object["context"] = record.extra_context # type: ignore
            
        return json.dumps(log_object)

def setup_logging():
    logger = logging.getLogger("enterprise_logger")
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers if re-initialized
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        
    return logger

audit_logger = setup_logging()