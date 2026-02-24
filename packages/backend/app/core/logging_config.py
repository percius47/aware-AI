"""
Logging configuration for Aware AI backend.
Provides colored, detailed console output for debugging chat flow.
"""
import logging
import sys
import time
from typing import Optional
from functools import wraps

# ANSI color codes for terminal output
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Colors
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels and components."""
    
    LEVEL_COLORS = {
        logging.DEBUG: Colors.GRAY,
        logging.INFO: Colors.GREEN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: Colors.RED + Colors.BOLD,
    }
    
    COMPONENT_COLORS = {
        'chat': Colors.CYAN,
        'memory': Colors.MAGENTA,
        'mem0': Colors.MAGENTA + Colors.BOLD,
        'rag': Colors.BLUE,
        'llm': Colors.YELLOW,
        'embedding': Colors.GREEN,
    }
    
    def format(self, record):
        # Get level color
        level_color = self.LEVEL_COLORS.get(record.levelno, Colors.WHITE)
        
        # Get component color based on logger name
        component_color = Colors.WHITE
        for comp, color in self.COMPONENT_COLORS.items():
            if comp in record.name.lower():
                component_color = color
                break
        
        # Format timestamp
        timestamp = self.formatTime(record, '%H:%M:%S')
        
        # Format the message
        formatted = (
            f"{Colors.GRAY}{timestamp}{Colors.RESET} | "
            f"{level_color}{record.levelname:8}{Colors.RESET} | "
            f"{component_color}{record.name:12}{Colors.RESET} | "
            f"{record.getMessage()}"
        )
        
        return formatted


def setup_logging(level: int = logging.INFO):
    """
    Configure logging for the application.
    
    Args:
        level: Logging level (default: INFO)
    """
    # Remove existing handlers
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    
    # Create console handler with colored formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredFormatter())
    console_handler.setLevel(level)
    
    # Configure root logger
    root.setLevel(level)
    root.addHandler(console_handler)
    
    # Set specific loggers
    loggers = ['chat', 'memory', 'mem0', 'rag', 'llm', 'embedding']
    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
    
    # Suppress noisy third-party loggers
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('supabase').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)


class Timer:
    """Context manager for timing operations."""
    
    def __init__(self, operation: str, logger: Optional[logging.Logger] = None):
        self.operation = operation
        self.logger = logger
        self.start_time = None
        self.elapsed_ms = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, *args):
        self.elapsed_ms = (time.perf_counter() - self.start_time) * 1000
        if self.logger:
            self.logger.info(f"  └─ {self.operation} completed ({self.elapsed_ms:.0f}ms)")


def log_separator(logger: logging.Logger, char: str = "═", length: int = 60):
    """Log a separator line."""
    logger.info(char * length)


def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text for logging, adding ellipsis if needed."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."
