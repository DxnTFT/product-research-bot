"""
Async Worker Pool for Bounded Concurrency

Manages concurrent async tasks with rate limiting to prevent blocking.
Used for parallel Reddit sentiment analysis while respecting rate limits.
"""

import asyncio
import time
from typing import List, Any, Callable, Optional, Coroutine


class AsyncWorkerPool:
    """
    Manages concurrent async tasks with rate limiting.

    Features:
    - Bounded concurrency via asyncio.Semaphore
    - Rate limiting with configurable delays
    - Progress callback support for UI updates
    - Graceful error handling per task

    Usage:
        pool = AsyncWorkerPool(max_workers=3, delay_between_tasks=10.0)

        async def fetch_data(item):
            return await some_async_operation(item)

        tasks = [fetch_data(item) for item in items]
        results = await pool.execute_batch(tasks)
    """

    def __init__(
        self,
        max_workers: int = 3,
        delay_between_tasks: float = 10.0,
        min_delay: float = 5.0
    ):
        """
        Initialize the worker pool.

        Args:
            max_workers: Maximum concurrent tasks (default 3)
            delay_between_tasks: Seconds between task starts (default 10)
            min_delay: Minimum delay floor (default 5)
        """
        self.max_workers = max_workers
        self.delay = delay_between_tasks
        self.min_delay = min_delay

        self.semaphore = asyncio.Semaphore(max_workers)
        self.lock = asyncio.Lock()
        self.last_request_time = 0

        # Stats
        self.completed_count = 0
        self.error_count = 0

    async def execute_batch(
        self,
        coroutines: List[Coroutine],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[Any]:
        """
        Execute coroutines with bounded concurrency and rate limiting.

        Args:
            coroutines: List of coroutines to execute
            progress_callback: Optional callback(completed, total, message)

        Returns:
            List of results in same order as input coroutines
        """
        total = len(coroutines)
        self.completed_count = 0
        self.error_count = 0

        async def wrapped_task(coro: Coroutine, index: int) -> Any:
            """Wrap coroutine with semaphore, delay, and error handling."""
            async with self.semaphore:
                # Apply rate limiting
                await self._apply_delay()

                try:
                    result = await coro
                    self.completed_count += 1

                    if progress_callback:
                        progress_callback(
                            self.completed_count,
                            total,
                            f"Completed {self.completed_count}/{total}"
                        )

                    return result

                except Exception as e:
                    self.error_count += 1
                    print(f"    Task {index + 1} failed: {str(e)[:100]}")

                    # Return error dict instead of raising
                    return {"error": str(e), "task_index": index}

        # Create wrapped tasks
        tasks = [
            wrapped_task(coro, i)
            for i, coro in enumerate(coroutines)
        ]

        # Execute all tasks concurrently (bounded by semaphore)
        results = await asyncio.gather(*tasks, return_exceptions=False)

        return results

    async def _apply_delay(self):
        """Apply rate limiting delay between requests."""
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_request_time

            if self.last_request_time > 0 and elapsed < self.delay:
                wait_time = max(self.min_delay, self.delay - elapsed)
                await asyncio.sleep(wait_time)

            self.last_request_time = time.time()

    def get_stats(self) -> dict:
        """Get execution statistics."""
        return {
            "completed": self.completed_count,
            "errors": self.error_count,
            "success_rate": (
                self.completed_count / max(self.completed_count + self.error_count, 1)
            ),
        }


class AsyncRateLimiter:
    """
    Async-compatible rate limiter for individual operations.

    Usage:
        limiter = AsyncRateLimiter(delay=10.0)

        async def make_request():
            await limiter.wait()
            return await do_request()
    """

    def __init__(self, delay: float = 10.0, min_delay: float = 5.0):
        """
        Initialize rate limiter.

        Args:
            delay: Seconds between requests
            min_delay: Minimum delay floor
        """
        self.delay = delay
        self.min_delay = min_delay
        self.lock = asyncio.Lock()
        self.last_request_time = 0

    async def wait(self):
        """Wait for rate limit, then mark request start."""
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_request_time

            if self.last_request_time > 0 and elapsed < self.delay:
                wait_time = max(self.min_delay, self.delay - elapsed)
                await asyncio.sleep(wait_time)

            self.last_request_time = time.time()

    def reset(self):
        """Reset the rate limiter."""
        self.last_request_time = 0
