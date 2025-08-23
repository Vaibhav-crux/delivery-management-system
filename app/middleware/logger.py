import logging
import os
import traceback
from logging.handlers import RotatingFileHandler
from colorama import init, Fore, Style

# Initialize colorama for colored console output
init()

class ColoredFormatter(logging.Formatter):
    COLORS = {
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED,
        'DEBUG': Fore.CYAN
    }

    def format(self, record):
        log_message = f"{record.asctime} - {record.levelname} - {record.message}"
        if record.levelname == 'ERROR':
            # Include stack trace for ERROR logs
            if record.exc_info:
                log_message += f"\n{''.join(traceback.format_exception(*record.exc_info))}"
        return f"{self.COLORS.get(record.levelname, '')}{log_message}{Style.RESET_ALL}"

def setup_logger(log_level: str, log_file: str):
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Configure logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Create formatters
    file_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s\n%(exc_info)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_formatter = ColoredFormatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler with colors
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)