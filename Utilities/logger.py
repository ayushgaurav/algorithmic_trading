import os
import logging
from logging import FileHandler, Formatter

LOG_FORMAT = '[%(asctime)s] [%(levelname)-8s] %(filename)s(%(lineno)d): %(message)s'
LOG_LEVEL = logging.INFO
FILE_DIR = os.path.dirname(os.path.realpath(__file__))

TRADES_LOG_FILE = FILE_DIR + "/trades.log"
trades_logger = logging.getLogger("Trades")
trades_logger.setLevel(LOG_LEVEL)
trades_logger_file_handler = FileHandler(TRADES_LOG_FILE, mode='a')
trades_logger_file_handler.setLevel(LOG_LEVEL)
trades_logger_file_handler.setFormatter(Formatter(LOG_FORMAT))
trades_logger.addHandler(trades_logger_file_handler)
