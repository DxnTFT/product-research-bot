"""
Logging Configuration for Scrapers
Provides structured logging for monitoring, debugging, and tracking blocking issues.
"""

import logging
import os
from datetime import datetime
from pathlib import Path


def setup_scraper_logging(log_level: str = "INFO"):
    """
    Configure logging for all scrapers.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Create a .gitignore in logs directory
    gitignore_path = log_dir / ".gitignore"
    if not gitignore_path.exists():
        with open(gitignore_path, 'w') as f:
            f.write("# Ignore all log files\n*.log\n")

    # Log file with date
    log_filename = f"scraper_{datetime.now():%Y%m%d}.log"
    log_path = log_dir / log_filename

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_path, encoding='utf-8'),
            logging.StreamHandler()  # Also log to console
        ]
    )

    # Configure specific logger levels
    logging.getLogger('scrapers.rate_limiter').setLevel(logging.DEBUG)
    logging.getLogger('scrapers.browser_scraper').setLevel(logging.INFO)
    logging.getLogger('scrapers.trends_scraper').setLevel(logging.INFO)
    logging.getLogger('scrapers.circuit_breaker').setLevel(logging.WARNING)

    # Suppress verbose third-party loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('playwright').setLevel(logging.WARNING)

    logging.info(f"Logging initialized - log file: {log_path}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


class BlockingEventLogger:
    """
    Special logger for tracking blocking events (403, 429 errors).
    Helps identify patterns and tune anti-blocking measures.
    """

    def __init__(self):
        self.logger = logging.getLogger('scrapers.blocking_events')
        self.events = []

    def log_403(self, domain: str, url: str, user_agent: str = ""):
        """Log a 403 Forbidden error."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": "403_FORBIDDEN",
            "domain": domain,
            "url": url,
            "user_agent": user_agent,
        }
        self.events.append(event)
        self.logger.error(f"403 Forbidden - {domain} - {url[:50]}")

    def log_429(self, domain: str, retry_after: int = 0):
        """Log a 429 Too Many Requests error."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": "429_RATE_LIMIT",
            "domain": domain,
            "retry_after": retry_after,
        }
        self.events.append(event)
        self.logger.warning(f"429 Rate Limited - {domain} - retry after {retry_after}s")

    def log_timeout(self, domain: str, timeout_seconds: int):
        """Log a timeout error."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": "TIMEOUT",
            "domain": domain,
            "timeout": timeout_seconds,
        }
        self.events.append(event)
        self.logger.warning(f"Timeout - {domain} - {timeout_seconds}s")

    def log_circuit_breaker_open(self, domain: str, failure_count: int):
        """Log when circuit breaker opens."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": "CIRCUIT_BREAKER_OPEN",
            "domain": domain,
            "failure_count": failure_count,
        }
        self.events.append(event)
        self.logger.error(f"Circuit Breaker OPEN - {domain} - {failure_count} failures")

    def get_summary(self) -> dict:
        """Get summary of blocking events."""
        summary = {
            "total_events": len(self.events),
            "403_count": sum(1 for e in self.events if e["type"] == "403_FORBIDDEN"),
            "429_count": sum(1 for e in self.events if e["type"] == "429_RATE_LIMIT"),
            "timeout_count": sum(1 for e in self.events if e["type"] == "TIMEOUT"),
            "circuit_breaker_count": sum(1 for e in self.events if e["type"] == "CIRCUIT_BREAKER_OPEN"),
        }
        return summary

    def export_events(self, filepath: str = None):
        """Export events to JSON file."""
        import json
        if filepath is None:
            filepath = f"logs/blocking_events_{datetime.now():%Y%m%d_%H%M%S}.json"

        with open(filepath, 'w') as f:
            json.dump(self.events, f, indent=2)

        self.logger.info(f"Exported {len(self.events)} events to {filepath}")
