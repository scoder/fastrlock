
from cpython cimport pythread

from fastrlock import LockNotAcquired


cdef struct _LockStatus:
    pythread.PyThread_type_lock lock
    long owner            # thread ID of the current lock owner
    int entry_count     # number of (re-)entries of the owner
    int pending_requests  # number of pending requests for real lock
    bint is_locked        # whether the real lock is acquired


cdef bint _acquire_lock(_LockStatus *lock, long current_thread,
                        bint blocking) nogil:
    # Note that this function *must* hold the GIL when being called.
    # We just use 'nogil' in the signature to make sure that no Python
    # code execution slips in that might free the GIL

    wait = pythread.WAIT_LOCK if blocking else pythread.NOWAIT_LOCK
    if not lock.is_locked and not lock.pending_requests:
        # someone owns it but didn't acquire the real lock - do that
        # now and tell the owner to release it when done
        if pythread.PyThread_acquire_lock(lock.lock, pythread.NOWAIT_LOCK):
            lock.is_locked = True
    #assert lock._is_locked

    lock.pending_requests += 1
    # wait for the lock owning thread to release it
    with nogil:
        while True:
            locked = pythread.PyThread_acquire_lock(lock.lock, wait)
            if locked:
                break
            if wait == pythread.NOWAIT_LOCK:
                return False
    lock.pending_requests -= 1
    #assert not lock.is_locked
    #assert lock.reentry_count == 0
    #assert locked
    lock.is_locked = True
    lock.owner = current_thread
    lock.entry_count = 1
    return True


cdef inline void _unlock_lock(_LockStatus *lock) nogil:
    # Note that this function *must* hold the GIL when being called.
    # We just use 'nogil' in the signature to make sure that no Python
    # code execution slips in that might free the GIL

    #assert lock.entry_count > 0
    lock.entry_count -= 1
    if lock.entry_count == 0:
        lock.owner = -1
        if lock.is_locked:
            pythread.PyThread_release_lock(lock.lock)
            lock.is_locked = False
