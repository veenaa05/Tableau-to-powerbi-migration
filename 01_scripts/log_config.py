import logging
import json
import logging.handlers
import os
from datetime import datetime

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord):
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "pathname": record.pathname,
            "lineno": record.lineno,
            "funcName": record.funcName,
            "process": record.process,
            "thread": record.thread,
        }
        if hasattr(record, 'json_extra') and isinstance(record.json_extra, dict):
            log_record.update(record.json_extra)

        return json.dumps(log_record)
    
def configure_logging(log_file_path: str, level: int = logging.INFO, max_size_in_bytes: int = 1_000_000, backup_count: int = 5) -> logging.Logger:
    """
    Configures a logger for the application, outputting logs in JSONL format to a
    rotating file and a more concise format to the console.

    This function sets up a custom logger named 'tableau_to_bi_run' with two
    handlers:
    1. A RotatingFileHandler: Writes detailed, structured JSONL logs to a file.
       It handles log rotation based on file size to prevent unbounded growth.
    2. A StreamHandler: Outputs human-readable, concise logs to the console
       (stdout/stderr).

    The logger prevents propagation to the root logger to avoid duplicate output.
    If this function is called multiple times, it ensures handlers are not
    added redundantly to the same logger instance.

    Args:
        log_file_path (str): The full path to the log file where JSONL logs
                              will be stored. This path should include the
                              filename (e.g., 'logs/app_logs.jsonl').
        level (int, optional): The minimum logging level for the overall logger.
                               Messages below this level will be ignored by
                               both handlers. Defaults to logging.INFO.
                               Common levels: logging.DEBUG, logging.INFO,
                               logging.WARNING, logging.ERROR, logging.CRITICAL.
        max_size_in_bytes (int, optional): The maximum size (in bytes) a log
                                           file can reach before it's rotated.
                                           Defaults to 1,000,000 bytes (1 MB).
        backup_count (int, optional): The number of backup log files to keep
                                      after rotation. When the main log file
                                      is rotated, older backups are deleted.
                                      Defaults to 5.

    Returns:
        logging.Logger: The configured logger instance ready for use.

    Example:
        >>> import logging
        >>> import os
        >>> log_dir = "my_app_logs"
        >>> os.makedirs(log_dir, exist_ok=True)
        >>> log_file = os.path.join(log_dir, "application.jsonl")
        >>> app_logger = setup_jsonl_logging(log_file, level=logging.DEBUG, max_size_in_bytes=5*1024*1024)
        >>> app_logger.debug("This is a debug message.")
        >>> app_logger.info("An info message for console and file.")
        >>> app_logger.error("An error occurred!", extra={'json_extra': {'error_id': 'XYZ'}})
    """
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    logger : logging.Logger = logging.getLogger('tableau_to_bi_run')
    logger.setLevel(level)
    file_handler = logging.handlers.RotatingFileHandler(
        filename = log_file_path,
        maxBytes = max_size_in_bytes,
        backupCount = backup_count,
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(JsonFormatter())
    
    stream_handler = logging.StreamHandler() 
    stream_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.propagate = False 
    return logger

