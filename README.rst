FastRLock
---------

This is a C-level implementation of a fast, re-entrant, optimistic lock for CPython.
It is a drop-in replacement for
`threading.RLock <https://docs.python.org/3/library/threading.html#threading.RLock>`_.
FastRLock is implemented in `Cython <https://cython.org>`_ and also provides a C-API
for direct use from Cython code via ``from fastrlock cimport rlock``.

Under normal conditions, it is about 10x faster than threading.RLock in Python 2.7
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


How fast is it?
---------------

Here are some timings for Python 2.7 for the following scenarios:

1) five acquire-release cycles ('lock_unlock')
2) five acquire calls followed by five release calls (nested locking, 'reentrant_lock_unlock')
3) a mixed and partly nested sequence of acquire and release calls ('mixed_lock_unlock')
4) five acquire-release cycles that do not block ('lock_unlock_nonblocking')

All four are benchmarked for the single threaded case and the multi threaded case
with 10 threads.  I also tested it with 20 threads only to see that it then takes
about twice the time for both versions.  Note also that the congested case is
substantially slower for both locks and the benchmark includes the thread
creation time, so I only looped 1000x here to get useful
timings instead of 100000x for the single threaded case.

::

    Testing _RLock (2.7.18)

    sequential (x100000):
    lock_unlock              :    853.55 msec
    reentrant_lock_unlock    :    684.52 msec
    mixed_lock_unlock        :    758.27 msec
    lock_unlock_nonblocking  :    860.40 msec
    context_manager          :   2876.00 msec

    threaded 10T (x1000):
    lock_unlock              :   2210.69 msec
    reentrant_lock_unlock    :   1864.38 msec
    mixed_lock_unlock        :   1963.10 msec
    lock_unlock_nonblocking  :   3709.91 msec
    context_manager          :   2640.32 msec

    Testing FastRLock (0.8.1)

    sequential (x100000):
    lock_unlock              :    139.76 msec
    reentrant_lock_unlock    :    137.56 msec
    mixed_lock_unlock        :    140.75 msec
    lock_unlock_nonblocking  :    164.64 msec
    context_manager          :    593.06 msec

    threaded 10T (x1000):
    lock_unlock              :   1621.13 msec
    reentrant_lock_unlock    :   1807.09 msec
    mixed_lock_unlock        :   1834.21 msec
    lock_unlock_nonblocking  :   1642.06 msec
    context_manager          :   1730.29 msec

    Testing Cython interface of FastRLock (0.8.1)

    sequential (x100000):
    lock_unlock              :     19.14 msec
    reentrant_lock_unlock    :     19.12 msec
    mixed_lock_unlock        :     16.81 msec
    lock_unlock_nonblocking  :     14.49 msec

    threaded 10T (x1000):
    lock_unlock              :   1511.85 msec
    reentrant_lock_unlock    :   1541.96 msec
    mixed_lock_unlock        :   1585.70 msec
    lock_unlock_nonblocking  :   1585.35 msec


How does it compare to Python 3.7 and later?
--------------------------------------------

The results here are more mixed.  Depending on the optimisation of the CPython
installation, it can be faster, about the same speed, or somewhat slower.
In any case, the direct Cython interface is always faster than going through
the Python API, because it avoids the Python call overhead and executes
a C call instead.

::

    Testing RLock (3.10.1)

    sequential (x100000):
    lock_unlock              :    138.36 msec
    reentrant_lock_unlock    :     95.35 msec
    mixed_lock_unlock        :    102.05 msec
    lock_unlock_nonblocking  :    131.44 msec
    context_manager          :    616.83 msec

    threaded 10T (x1000):
    lock_unlock              :   1386.60 msec
    reentrant_lock_unlock    :   1207.75 msec
    mixed_lock_unlock        :   1319.62 msec
    lock_unlock_nonblocking  :   1325.07 msec
    context_manager          :   1357.93 msec

    Testing FastRLock (0.8.1)

    sequential (x100000):
    lock_unlock              :     77.47 msec
    reentrant_lock_unlock    :     64.14 msec
    mixed_lock_unlock        :     73.51 msec
    lock_unlock_nonblocking  :     70.31 msec
    context_manager          :    393.34 msec

    threaded 10T (x1000):
    lock_unlock              :   1214.13 msec
    reentrant_lock_unlock    :   1171.75 msec
    mixed_lock_unlock        :   1184.33 msec
    lock_unlock_nonblocking  :   1207.42 msec
    context_manager          :   1232.20 msec

    Testing Cython interface of FastRLock (0.8.1)

    sequential (x100000):
    lock_unlock              :     18.70 msec
    reentrant_lock_unlock    :     15.88 msec
    mixed_lock_unlock        :     14.96 msec
    lock_unlock_nonblocking  :     13.47 msec

    threaded 10T (x1000):
    lock_unlock              :   1236.21 msec
    reentrant_lock_unlock    :   1245.77 msec
    mixed_lock_unlock        :   1194.25 msec
    lock_unlock_nonblocking  :   1206.96 msec
