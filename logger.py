"""logger.py file for timestamped output logging for info and errors."""
import logging
from datetime import datetime

filename = datetime.now().strftime('logs_%H_%M_%d_%m_%Y.log')
log_filepath = f"./output_logs/{filename}"

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s][%(asctime)s]: %(message)s",
    handlers=[
        logging.FileHandler(log_filepath),
        logging.StreamHandler()
    ]
)


def log_info(msg):
    """Helper method to log [INFO] messages"""
    logging.info(msg)


def log_error(msg):
    """Helper method to log [ERROR] messages"""
    logging.error(msg)
