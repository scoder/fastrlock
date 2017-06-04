# this is a package


class LockNotAcquired(Exception):
    """
    Exception raised when the lock was not acquired in non-blocking mode.
    """
