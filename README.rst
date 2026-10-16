FastRLock
---------

This is a C-level implementation of a fast, re-entrant, optimistic lock for CPython.
It is a drop-in replacement for
`threading.RLock <https://docs.python.org/3/library/threading.html#threading.RLock>`_.
FastRLock is implemented in `Cython <https://cython.org>`_ and also provides a C-API
for direct use from Cython code via ``from fastrlock cimport rlock`` or
``from cython.cimports.fastrlock import rlock``. See the
`pxd interface file <https://github.com/scoder/fastrlock/blob/master/fastrlock/rlock.pxd>`_.

Under normal conditions, it is about 10x faster than ``threading.RLock`` in Python 2.7
because it avoids all locking unless two or more threads try to acquire it at the
same time.  Under congestion, it is still about 10% faster than RLock due to being
implemented in Cython.

This is mostly equivalent to the revised RLock implementation in Python 3.2,
but still faster due to being implemented in Cython.  However, in Python 3.4 and
later, the ``threading.RLock`` implementation in the stdlib tends to be as fast
or even faster than the lock provided by this package, when called through the
Python API.  ``FastRLock`` is still faster also on these systems when called
through its Cython API from other Cython modules.

It was initially published as a code recipe here:
https://code.activestate.com/recipes/577336-fast-re-entrant-optimistic-lock-implemented-in-cyt/

FastRLock has been used and tested in `Lupa <https://github.com/scoder/lupa>`_ for several years.


How does it work?
-----------------

The FastRLock implementation optimises for the non-congested case.  It works by
exploiting the availability of the GIL.  Since it knows that it holds the GIL when
the acquire()/release() methods are called, it can safely check the lock for being
held by other threads and just count any re-entries as long as it is always the
same thread that acquires it.  This is a lot faster than actually acquiring the
underlying lock.

When a second thread wants to acquire the lock as well, it first checks the lock
count and finds out that the lock is already owned.  If the underlying lock is also
held by another thread already, it then just frees the GIL and asks for acquiring
the lock, just like RLock does.  If the underlying lock is not held, however, it
acquires it immediately and basically hands over the ownership by telling the
current owner to free it when it's done.  Then, it falls back to the normal
non-owner behaviour that asks for the lock and will eventually acquire it when it
gets released.  This makes sure that the real lock is only acquired when at least
two threads want it.

All of these operations are basically atomic because any thread that modifies the
lock state always holds the GIL.  Note that the implementation must not call any
Python code while handling the lock, as calling into Python may lead to a context
switch which hands over the GIL to another thread and thus breaks atomicity.
Therefore, the code misuses Cython's 'nogil' annotation to make sure that no Python
code slips in accidentally.

The smart reliance on the GIL is also the reason why freethreading Python is not
supported.


How fast is it?
---------------

Here are some timings for the following scenarios:

1) five acquire-release cycles ('lock_unlock')
2) five acquire calls followed by five release calls (nested locking, 'reentrant_lock_unlock')
3) a mixed and partly nested sequence of acquire and release calls ('mixed_lock_unlock')
4) five acquire-release cycles that do not block ('lock_unlock_nonblocking')
5) nested with-statement usage through a context manager

All five are benchmarked for the single threaded case and the congested multi threaded
case with 10 threads.  I also tested it with 20 threads only to see that it then takes
about twice the time for both versions.  Note also that the congested case is
substantially slower for both locks and the benchmark includes the thread
creation time, so I only looped 100x here to get useful
timings instead of 1000x for the single threaded case.

The results here are mixed.  Depending on the optimisation of the CPython
installation, it can be faster, about the same speed, or somewhat slower.
In any case, the direct Cython interface is always faster than going through
the Python API, because it avoids the Python call overhead and executes
a C call instead.

On Linux x86-64::

    Testing RLock (3.14.8)

    sequential (x1000):
    lock_unlock              :      0.47 msec
    reentrant_lock_unlock    :      0.47 msec
    mixed_lock_unlock        :      0.43 msec
    lock_unlock_nonblocking  :      0.60 msec
    context_manager          :      2.48 msec

    threaded 10T (x100):
    lock_unlock              :    356.06 msec
    reentrant_lock_unlock    :    371.20 msec
    mixed_lock_unlock        :    355.51 msec
    lock_unlock_nonblocking  :    372.06 msec
    context_manager          :    386.38 msec

    Testing FastRLock (0.8.4)

    sequential (x1000):
    lock_unlock              :      0.57 msec
    reentrant_lock_unlock    :      0.35 msec
    mixed_lock_unlock        :      0.53 msec
    lock_unlock_nonblocking  :      0.53 msec
    context_manager          :      1.65 msec

    threaded 10T (x100):
    lock_unlock              :    382.98 msec
    reentrant_lock_unlock    :    384.84 msec
    mixed_lock_unlock        :    388.89 msec
    lock_unlock_nonblocking  :    396.14 msec
    context_manager          :    393.30 msec


On Linux Aarch64 (ARM64)::

    Testing RLock (3.14.8)

    sequential (x1000):
    lock_unlock              :      0.43 msec
    reentrant_lock_unlock    :      0.38 msec
    mixed_lock_unlock        :      0.39 msec
    lock_unlock_nonblocking  :      0.57 msec
    context_manager          :      2.19 msec

    threaded 10T (x100):
    lock_unlock              :     73.74 msec
    reentrant_lock_unlock    :     77.39 msec
    mixed_lock_unlock        :     76.54 msec
    lock_unlock_nonblocking  :     77.25 msec
    context_manager          :     79.46 msec

    Testing FastRLock (0.8.4)

    sequential (x1000):
    lock_unlock              :      0.25 msec
    reentrant_lock_unlock    :      0.36 msec
    mixed_lock_unlock        :      0.25 msec
    lock_unlock_nonblocking  :      0.28 msec
    context_manager          :      1.26 msec

    threaded 10T (x100):
    lock_unlock              :     78.71 msec
    reentrant_lock_unlock    :     78.44 msec
    mixed_lock_unlock        :     78.19 msec
    lock_unlock_nonblocking  :     77.46 msec
    context_manager          :     79.48 msec


Comparing Python RLock to the Cython interface of FastRLock (0.8.4)::

    Testing RLock (3.14.4)

    sequential (x1000):
    lock_unlock              :      0.22 msec
    reentrant_lock_unlock    :      0.19 msec
    mixed_lock_unlock        :      0.20 msec
    lock_unlock_nonblocking  :      0.31 msec
    context_manager          :      1.02 msec

    threaded 10T (x100):
    lock_unlock              :     42.05 msec
    reentrant_lock_unlock    :     37.20 msec
    mixed_lock_unlock        :     41.53 msec
    lock_unlock_nonblocking  :     39.51 msec
    context_manager          :     40.21 msec

    Testing Cython interface of FastRLock (0.8.4)

    sequential (x1000):
    lock_unlock              :      0.07 msec
    reentrant_lock_unlock    :      0.06 msec
    mixed_lock_unlock        :      0.05 msec
    lock_unlock_nonblocking  :      0.06 msec

    threaded 10T (x100):
    lock_unlock              :     38.54 msec
    reentrant_lock_unlock    :     40.38 msec
    mixed_lock_unlock        :     36.31 msec
    lock_unlock_nonblocking  :     40.80 msec
