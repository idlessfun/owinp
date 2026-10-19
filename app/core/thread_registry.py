"""
Registry of background QThread workers.

Why it exists:
    A QThread that is still running when Python destroys it makes Qt abort
    the whole process ("QThread: Destroyed while thread is still running").
    Workers register themselves for the duration of run(), and the
    application calls shutdown_all() before exiting. This also covers a
    download dialog that was closed while its download was in progress.
"""

import threading

from PySide6.QtCore import QThread


_lock = threading.Lock()
_threads: set[QThread] = set()


def register(thread: QThread) -> None:
    """Adds a thread to the registry (called from run())."""
    with _lock:
        _threads.add(thread)


def unregister(thread: QThread) -> None:
    """Removes a thread from the registry (called from run()'s finally)."""
    with _lock:
        _threads.discard(thread)


def running_count() -> int:
    """Returns the number of registered threads that are still running."""
    with _lock:
        threads = list(_threads)

    count = 0
    for thread in threads:
        try:
            if thread.isRunning():
                count += 1
        except RuntimeError:
            # The C++ object is already gone
            continue
    return count


def shutdown_all(timeout_ms: int = 3000) -> None:
    """
    Stops every registered thread before the application exits.

    Threads with a cancel() method get a polite cancellation request first.
    If a thread does not finish in time it is terminated, because the
    alternative is a hard crash of the whole process.
    """
    with _lock:
        threads = list(_threads)

    for thread in threads:
        try:
            if not thread.isRunning():
                continue

            cancel = getattr(thread, "cancel", None)
            if callable(cancel):
                try:
                    cancel()
                except Exception as e:
                    print(f"[threads] cancel() failed: {e}")

            if thread.wait(timeout_ms):
                continue

            print(f"[threads] Thread did not stop in time — terminating: {thread}")
            thread.terminate()
            thread.wait(1000)

        except RuntimeError:
            # Already deleted by Qt
            continue
