"""
Stealth Configuration for Web Scraping
Provides user agent rotation, realistic headers, and anti-fingerprinting configurations.
"""

import random
from typing import Dict, List, Tuple


class UserAgentRotator:
    """Rotate through realistic user agents to avoid detection."""

    # Realistic user agents from recent browser versions
    USER_AGENTS = [
        # Chrome on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",

        # Chrome on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",

        # Chrome on Linux
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",

        # Firefox on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:118.0) Gecko/20100101 Firefox/118.0",

        # Firefox on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",

        # Safari on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",

        # Edge on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",

        # Edge on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    ]

    def __init__(self):
        self.last_used = None
        self.current_session_ua = None

    def get_next(self) -> str:
        """Get the next user agent (rotates per session, not per request)."""
        if self.current_session_ua is None:
            # First call - select a random UA
            available = [ua for ua in self.USER_AGENTS if ua != self.last_used]
            self.current_session_ua = random.choice(available)
            self.last_used = self.current_session_ua

        return self.current_session_ua

    def rotate_session(self):
        """Force rotation to a new user agent for a new session."""
        self.current_session_ua = None
        return self.get_next()

    def get_random(self) -> str:
        """Get a completely random user agent (use sparingly)."""
        return random.choice(self.USER_AGENTS)


class HeaderGenerator:
    """Generate realistic HTTP headers to mimic real browser behavior."""

    ACCEPT_LANGUAGES = [
        "en-US,en;q=0.9",
        "en-US,en;q=0.9,es;q=0.8",
        "en-US,en;q=0.9,fr;q=0.8",
        "en-GB,en;q=0.9,en-US;q=0.8",
        "en",
    ]

    ACCEPT_ENCODINGS = [
        "gzip, deflate, br",
        "gzip, deflate",
    ]

    def __init__(self):
        pass

    def get_realistic_headers(self, user_agent: str) -> Dict[str, str]:
        """Generate realistic headers based on user agent."""
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": random.choice(self.ACCEPT_LANGUAGES),
            "Accept-Encoding": random.choice(self.ACCEPT_ENCODINGS),
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

        # Add browser-specific headers
        if "Chrome" in user_agent or "Edg" in user_agent:
            headers["sec-ch-ua"] = '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"'
            headers["sec-ch-ua-mobile"] = "?0"
            headers["sec-ch-ua-platform"] = '"Windows"' if "Windows" in user_agent else '"macOS"'

        return headers


class StealthConfig:
    """Configuration for browser fingerprinting evasion."""

    # Common viewport sizes
    VIEWPORTS = [
        {"width": 1920, "height": 1080},
        {"width": 1366, "height": 768},
        {"width": 1536, "height": 864},
        {"width": 1440, "height": 900},
        {"width": 1280, "height": 720},
        {"width": 1600, "height": 900},
        {"width": 2560, "height": 1440},
    ]

    # US timezones
    TIMEZONES = [
        "America/New_York",      # EST/EDT
        "America/Chicago",       # CST/CDT
        "America/Denver",        # MST/MDT
        "America/Los_Angeles",   # PST/PDT
        "America/Phoenix",       # MST (no DST)
        "America/Detroit",       # EST/EDT
        "America/Indianapolis",  # EST/EDT
        "America/Anchorage",     # AKST/AKDT
    ]

    LOCALES = [
        "en-US",
        "en",
    ]

    def __init__(self):
        pass

    def get_random_viewport(self) -> Dict[str, int]:
        """Get a random viewport size."""
        return random.choice(self.VIEWPORTS)

    def get_random_timezone(self) -> str:
        """Get a random US timezone."""
        return random.choice(self.TIMEZONES)

    def get_random_locale(self) -> str:
        """Get a random locale."""
        return random.choice(self.LOCALES)

    def get_geolocation_coords(self) -> Dict[str, float]:
        """Get realistic US geolocation coordinates."""
        # Major US cities coordinates
        cities = [
            {"latitude": 40.7128, "longitude": -74.0060},   # New York
            {"latitude": 34.0522, "longitude": -118.2437},  # Los Angeles
            {"latitude": 41.8781, "longitude": -87.6298},   # Chicago
            {"latitude": 29.7604, "longitude": -95.3698},   # Houston
            {"latitude": 33.4484, "longitude": -112.0740},  # Phoenix
            {"latitude": 39.9526, "longitude": -75.1652},   # Philadelphia
            {"latitude": 37.7749, "longitude": -122.4194},  # San Francisco
            {"latitude": 47.6062, "longitude": -122.3321},  # Seattle
        ]
        return random.choice(cities)
