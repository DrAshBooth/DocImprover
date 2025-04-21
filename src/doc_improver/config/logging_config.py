"""Logging configuration for DocImprover."""
import logging
import os
from logging.handlers import RotatingFileHandler

class SensitiveDataFilter(logging.Filter):
    """Filter out sensitive information from logs."""
    def filter(self, record):
        # Check if the log message contains sensitive information
        sensitive_patterns = ['api_key', 'key:', 'apikey', 'password', 'secret']
        message = record.getMessage().lower()
        
        for pattern in sensitive_patterns:
            if pattern in message:
                # Replace the sensitive information with asterisks
                record.msg = '[REDACTED]'
                break
        
        return True

def setup_logging():
    """Set up logging configuration."""
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure logging
    log_file = os.path.join(log_dir, 'docimprover.log')
    
    # Create a rotating file handler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1024 * 1024,  # 1MB
        backupCount=5
    )
    
    # Create formatters and add it to handlers
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_format)
    
    # Add sensitive data filter
    sensitive_filter = SensitiveDataFilter()
    file_handler.addFilter(sensitive_filter)
    
    # Get the root logger and add handlers
    logger = logging.getLogger('docimprover')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    
    return logger
