import os
import appdirs
import logging
from logging.handlers import RotatingFileHandler
import multiprocessing


def get_process_logger(process_name=None):
    
    if process_name is None:
        process_name = f"{multiprocessing.current_process().name}_{os.getpid()}"
        
    # Log format
    log_format = (
        '%(asctime)s.%(msecs)03d|'  # Timestamp with milliseconds
        '%(levelname)s|'            # Log level
        '%(thread)d|'               # Thread ID
        '%(threadName)s|'           # Thread name
        '%(name)s|'                 # Logger name (usually module name)
        '%(filename)s:%(lineno)d|'  # File name and line number
        '%(funcName)s|'             # Function name where logging call was issued
        '%(message)s'               # Log message
    )
    
    # Create unique logger for process
    logger_name = f'ailice.{process_name}'
    logger = logging.getLogger(logger_name)
    
    # If logger already configured, return it
    if logger.handlers:
        return logger
    
    # Set log level
    logger.setLevel(logging.INFO)
    
    # Log file directory
    LOG_DIR = os.path.join(appdirs.user_log_dir("ailice", "Steven Lu"), "logs")
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Use different log files for different processes
    LOG_FILE = os.path.join(LOG_DIR, f"ailice_{process_name}.log")
    
    # Set up file handler with rotation
    file_handler = RotatingFileHandler(
        LOG_FILE, 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    
    # Set up console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter and add to handlers
    formatter = logging.Formatter(log_format)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Ensure logs are not propagated to root logger
    logger.propagate = False
    
    return logger


logger = get_process_logger()