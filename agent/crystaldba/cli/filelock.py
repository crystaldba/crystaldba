"""
Platform-independent file locking utilities.

This module provides a cross-platform way to lock files, supporting both
Windows and Unix-like systems (Linux, macOS).
"""

import platform
from contextlib import contextmanager
from typing import IO
from typing import Iterator

# Import platform-specific locking modules
if platform.system() == "Windows":
    import msvcrt
else:
    import fcntl


@contextmanager
def file_lock(file_obj: IO) -> Iterator[None]:
    """
    A context manager for file locking that works across platforms.

    Args:
        file_obj: An open file object with appropriate permissions.

    Yields:
        None: The locked file context.

    Example:
        with open('file.txt', 'a+') as f:
            with file_lock(f):
                # Do something with the locked file
                f.write('data')
    """
    if platform.system() == "Windows":
        # Windows file locking
        try:
            # Lock from current position to end of file
            msvcrt.locking(file_obj.fileno(), msvcrt.LK_LOCK, 1)
            yield
        finally:
            # Unlock the file
            try:
                file_obj.seek(0)
                msvcrt.locking(file_obj.fileno(), msvcrt.LK_UNLCK, 1)
            except (OSError, PermissionError):
                # If unlocking fails, the file will be unlocked when it's closed anyway
                pass
    else:
        # Unix-like systems (Linux, macOS) use fcntl
        try:
            fcntl.flock(file_obj.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(file_obj.fileno(), fcntl.LOCK_UN)
