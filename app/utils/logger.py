"""
Logger Utility Module

This module provides centralized logging configuration and utilities.
"""

from loguru import logger
import sys
from app.core.config import get_settings

settings = get_settings()


def setup_logger():
    """
    Configure loguru logger with console and file handlers.
    """
    # Remove default handler
    logger.remove()
    
    # Console handler with colors
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL,
        colorize=True
    )
    
    # File handler for persistent logs
    if settings.LOG_FILE:
        logger.add(
            settings.LOG_FILE,
            rotation="500 MB",
            retention="30 days",
            level=settings.LOG_LEVEL,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            compression="zip"
        )
    
    # Error file handler
    if settings.LOG_FILE:
        error_log = settings.LOG_FILE.replace(".log", "_error.log")
        logger.add(
            error_log,
            rotation="100 MB",
            retention="30 days",
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            compression="zip"
        )
    
    return logger


def get_logger(name: str):
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Module name
        
    Returns:
        Logger: Logger instance
    """
    return logger.bind(name=name)


# Initialize logger on import
setup_logger()
