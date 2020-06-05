# cython: binding=True

from cpython cimport pythread

include "_lock.pxi"


cdef class FastRLock:
    """Fast, re-entrant locking.

    Under non-congested conditions, the lock is never acquired but only
    counted.  Only when a second thread comes in and notices that the
    lock is needed, it acquires the lock and notifies the first thread
    to release it when it's done.  This is all made possible by the
    wonderful GIL.
    """
    cdef _LockStatus _real_lock

    def __cinit__(self):
        self._real_lock = _LockStatus(
            lock=pythread.PyThread_allocate_lock(),
            owner=-1, is_locked=False, pending_requests=0, entry_count=0)
        if not self._real_lock.lock:
            raise MemoryError()

    def __dealloc__(self):
        if self._real_lock.lock:
            pythread.PyThread_free_lock(self._real_lock.lock)
            self._real_lock.lock = NULL

    # compatibility with RLock and expected Python level interface

    def acquire(self, bint blocking=True):
        return _lock_rlock(
            &self._real_lock, <long>pythread.PyThread_get_thread_ident(), blocking)

    def release(self):
        if self._real_lock.owner == -1:
            raise RuntimeError("cannot release un-acquired lock")
        _unlock_lock(&self._real_lock)

    def __enter__(self):
        # self.acquire()
        if not _lock_rlock(
                &self._real_lock, <long>pythread.PyThread_get_thread_ident(),
                blocking=True):
            raise LockNotAcquired()

    def __exit__(self, t, v, tb):
        # self.release()
        if self._real_lock.owner != <long>pythread.PyThread_get_thread_ident():
            raise RuntimeError("cannot release un-acquired lock")
        _unlock_lock(&self._real_lock)

    def _is_owned(self):
        return self._real_lock.owner == <long>pythread.PyThread_get_thread_ident()


cdef inline bint _lock_rlock(_LockStatus *lock, long current_thread,
                             bint blocking) nogil:
    # Note that this function *must* hold the GIL when being called.
    # We just use 'nogil' in the signature to make sure that no Python
    # code execution slips in that might free the GIL

    if lock.entry_count:
        # locked! - by myself?
        if lock.owner == current_thread:
            lock.entry_count += 1
            return 1
    elif not lock.pending_requests:
        # not locked, not requested - go!
        lock.owner = current_thread
        lock.entry_count = 1
        return 1
    # need to get the real lock
    return _acquire_lock(lock, current_thread, blocking)


###########################################################################
## public C-API

cdef create_fastrlock():
    """
    Public C level entry function for creating a FastRlock instance.
    """
    return FastRLock.__new__(FastRLock)


cdef bint lock_fastrlock(rlock, long current_thread, bint blocking) except -1:
    """
    Public C level entry function for locking a FastRlock instance.
    """
    if current_thread == -1:
        current_thread = <long>pythread.PyThread_get_thread_ident()
    return _lock_rlock(&(<FastRLock?>rlock)._real_lock, current_thread, blocking)


cdef int unlock_fastrlock(rlock) except -1:
    """
    Public C level entry function for unlocking a FastRlock instance.
    """
    _unlock_lock(&(<FastRLock?>rlock)._real_lock)
    return 0
