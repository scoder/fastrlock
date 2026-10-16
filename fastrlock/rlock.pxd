# cython: language_level=3

# Create a new FastRLock instance.
cdef create_fastrlock()

# Acquire the lock of a FastRlock instance.
# 'current_thread' is deprecated and ignored. Pass -1 for backwards compatibility.
cdef bint lock_fastrlock(rlock, long current_thread, bint blocking) except -1

# Release the lock of a FastRlock instance.
cdef int unlock_fastrlock(rlock) except -1
