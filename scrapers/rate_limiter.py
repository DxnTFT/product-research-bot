"""
Rate Limiting and Circuit Breaker for Web Scraping
Prevents blocking through exponential backoff, circuit breaker pattern, and request throttling.
"""

import time
import random
from datetime import datetime, timedelta
from typing import Callable, Any, Optional
from enum import Enum


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"       # Normal operation
    OPEN = "OPEN"           # Blocking requests due to failures
    HALF_OPEN = "HALF_OPEN" # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent hammering blocked endpoints.

    States:
    - CLOSED: Normal operation, all requests allowed
    - OPEN: Too many failures, block all requests for recovery period
    - HALF_OPEN: After recovery timeout, try limited requests to test
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: int = 600,  # 10 minutes
        half_open_requests: int = 1
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_requests = half_open_requests

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.opened_time = None
        self.half_open_attempts = 0

    def can_request(self) -> bool:
        """Check if a request is allowed in the current state."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self.opened_time and datetime.now() >= self.opened_time + timedelta(seconds=self.recovery_timeout):
                # Transition to HALF_OPEN
                self.state = CircuitState.HALF_OPEN
                self.half_open_attempts = 0
                print(f"  Circuit breaker: OPEN -> HALF_OPEN (testing recovery)")
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            # Allow limited requests to test recovery
            if self.half_open_attempts < self.half_open_requests:
                self.half_open_attempts += 1
                return True
            return False

        return False

    def track_success(self):
        """Record a successful request."""
        if self.state == CircuitState.HALF_OPEN:
            # Success in HALF_OPEN means service recovered
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count += 1
            print(f"  Circuit breaker: HALF_OPEN -> CLOSED (service recovered)")
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0  # Reset failure count on success
            self.success_count += 1

    def track_failure(self, error_msg: str = ""):
        """Record a failed request."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        # Check for immediate blocking errors (403 Forbidden)
        if "403" in error_msg or "forbidden" in error_msg.lower():
            print(f"  Circuit breaker: Detected bot blocking (403) - opening immediately")
            self._open_circuit()
            return

        if self.state == CircuitState.HALF_OPEN:
            # Failure in HALF_OPEN means service not recovered
            print(f"  Circuit breaker: HALF_OPEN -> OPEN (service still blocked)")
            self._open_circuit()

        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                print(f"  Circuit breaker: CLOSED -> OPEN ({self.failure_count} failures)")
                self._open_circuit()

    def _open_circuit(self):
        """Open the circuit breaker."""
        self.state = CircuitState.OPEN
        self.opened_time = datetime.now()
        recovery_time = self.opened_time + timedelta(seconds=self.recovery_timeout)
        print(f"  Circuit breaker: Will retry at {recovery_time.strftime('%H:%M:%S')}")

    def get_state(self) -> str:
        """Get current state as string."""
        return self.state.value


class ExponentialBackoff:
    """
    Exponential backoff calculator for retry delays.

    Delays grow exponentially:
    - Attempt 0 (1st retry): 60s
    - Attempt 1 (2nd retry): 120s
    - Attempt 2 (3rd retry): 300s
    """

    def __init__(
        self,
        base_delay: float = 60.0,
        max_delay: float = 600.0,
        backoff_factor: float = 2.0,
        jitter: float = 0.1  # ±10% randomization
    ):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number (0-indexed)."""
        if attempt == 0:
            delay = self.base_delay
        elif attempt == 1:
            delay = self.base_delay * self.backoff_factor
        else:
            delay = min(self.base_delay * (self.backoff_factor ** attempt), self.max_delay)

        # Add jitter to avoid thundering herd
        jitter_amount = delay * self.jitter * random.uniform(-1, 1)
        final_delay = delay + jitter_amount

        return max(1.0, final_delay)  # Minimum 1 second


class RateLimiter:
    """
    Comprehensive rate limiter with exponential backoff and circuit breaker.

    Features:
    - Base delay between requests with jitter
    - Exponential backoff for retries
    - Circuit breaker for repeated failures
    - Retry-After header parsing
    - Per-domain configuration
    """

    def __init__(
        self,
        domain: str = "default",
        base_delay: float = 25.0,
        max_retries: int = 3,
        jitter: float = 2.0
    ):
        self.domain = domain
        self.base_delay = base_delay
        self.max_retries = max_retries
        self.jitter = jitter

        # Initialize components
        self.backoff = ExponentialBackoff(base_delay=60.0)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=600,
            half_open_requests=1
        )

        # Tracking
        self.request_count = 0
        self.last_request_time = None
        self.success_count = 0
        self.failure_count = 0

    def wait_with_backoff(self, attempt: int) -> float:
        """Calculate and return delay for retry attempt."""
        delay = self.backoff.calculate_delay(attempt)
        return delay

    def apply_delay(self):
        """Apply base delay with jitter before request."""
        jitter_amount = random.uniform(-self.jitter, self.jitter)
        delay = max(10.0, self.base_delay + jitter_amount)

        # Ensure minimum time between requests
        if self.last_request_time:
            elapsed = time.time() - self.last_request_time
            if elapsed < delay:
                remaining = delay - elapsed
                time.sleep(remaining)
        else:
            time.sleep(delay)

        self.last_request_time = time.time()
        self.request_count += 1

    def check_circuit_breaker(self) -> bool:
        """Check if circuit breaker allows requests."""
        can_proceed = self.circuit_breaker.can_request()
        if not can_proceed:
            state = self.circuit_breaker.get_state()
            print(f"  Circuit breaker is {state} - request blocked")
        return can_proceed

    def track_success(self):
        """Track successful request."""
        self.success_count += 1
        self.circuit_breaker.track_success()

    def track_failure(self, error_msg: str = ""):
        """Track failed request."""
        self.failure_count += 1
        self.circuit_breaker.track_failure(error_msg)

    def execute_with_retry(self, func: Callable, max_retries: Optional[int] = None) -> Any:
        """
        Execute a function with automatic retry logic.

        Args:
            func: Function to execute (should raise exception on failure)
            max_retries: Override default max_retries

        Returns:
            Result from successful function execution

        Raises:
            Exception from final failed attempt
        """
        if max_retries is None:
            max_retries = self.max_retries

        last_exception = None

        for attempt in range(max_retries + 1):
            # Check circuit breaker
            if not self.check_circuit_breaker():
                raise Exception(f"Circuit breaker is OPEN for {self.domain}")

            try:
                # Apply delay before request (except first attempt)
                if attempt > 0:
                    delay = self.wait_with_backoff(attempt - 1)
                    print(f"    Retry {attempt}/{max_retries} after {delay:.0f}s...")
                    time.sleep(delay)
                else:
                    # Normal rate limiting for first attempt
                    self.apply_delay()

                # Execute function
                result = func()

                # Success!
                self.track_success()
                return result

            except Exception as e:
                last_exception = e
                error_str = str(e)

                # Track failure
                self.track_failure(error_str)

                # Check if we should retry
                if attempt == max_retries:
                    # Final attempt failed
                    print(f"    Final attempt failed: {error_str[:100]}")
                    break

                # Check for retry-after header in error
                retry_after = self._parse_retry_after(error_str)
                if retry_after:
                    print(f"    Server requested retry after {retry_after}s")
                    time.sleep(retry_after)

        # All retries exhausted
        raise last_exception

    def _parse_retry_after(self, error_str: str) -> Optional[int]:
        """Parse Retry-After value from error message."""
        # Simple parsing - could be enhanced
        if "retry" in error_str.lower() and "after" in error_str.lower():
            # Try to extract number
            import re
            match = re.search(r'(\d+)\s*s', error_str)
            if match:
                return int(match.group(1))
        return None

    def get_stats(self) -> dict:
        """Get rate limiter statistics."""
        return {
            "domain": self.domain,
            "total_requests": self.request_count,
            "successes": self.success_count,
            "failures": self.failure_count,
            "success_rate": self.success_count / max(self.request_count, 1),
            "circuit_state": self.circuit_breaker.get_state(),
        }
