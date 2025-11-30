from __future__ import annotations

from queue import Queue, Empty
from typing import Optional

from .models import Job


class JobQueue:
    """
    Simple in-memory FIFO job queue.
    Backed by Python's thread-safe queue.Queue.
    """

    def __init__(self) -> None:
        self._queue: Queue[Job] = Queue()

    def enqueue(self, job: Job) -> None:
        self._queue.put(job)

    def dequeue(self, timeout: float | None = 1.0) -> Optional[Job]:
        try:
            return self._queue.get(timeout=timeout)
        except Empty:
            return None

    def task_done(self) -> None:
        self._queue.task_done()

    def join(self) -> None:
        """
        Block until all tasks in the queue have been processed.
        """
        self._queue.join()
