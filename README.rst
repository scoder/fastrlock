FastRLock
---------

This is a C-level implementation of a fast, re-entrant, optimistic lock for CPython.
It is a drop-in replacement for
`threading.RLock <https://docs.python.org/3/library/threading.html#threading.RLock>`_.
FastRLock is implemented in `Cython <http://cython.org>`_ and also provides a C-API
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
substantially slower for both locks, so I only looped 1000x here to get useful
timings instead of 100000x for the single threaded case.

::

    Testing threading.RLock (2.7)

    sequential (x100000):
    lock_unlock              : 1.408 sec
    reentrant_lock_unlock    : 1.089 sec
    mixed_lock_unlock        : 1.212 sec
    lock_unlock_nonblocking  : 1.415 sec

    threaded 10T (x1000):
    lock_unlock              : 1.188 sec
    reentrant_lock_unlock    : 1.039 sec
    mixed_lock_unlock        : 1.068 sec
    lock_unlock_nonblocking  : 1.199 sec

    Testing FastRLock

    sequential (x100000):
    lock_unlock              : 0.122 sec
    reentrant_lock_unlock    : 0.124 sec
    mixed_lock_unlock        : 0.137 sec
    lock_unlock_nonblocking  : 0.156 sec

    threaded 10T (x1000):
    lock_unlock              : 0.911 sec
    reentrant_lock_unlock    : 0.938 sec
    mixed_lock_unlock        : 0.953 sec
    lock_unlock_nonblocking  : 0.916 sec


How does it compare to Python 3.7 and later?
--------------------------------------------

The results here are more mixed.  Depending on the optimisation of the CPython
installation, it can be faster, about the same speed, or somewhat slower.
In any case, the direct Cython interface is always faster than going through
the Python API, because it avoids the Python call overhead and executes
a C call instead.

::

    Testing threading.RLock (3.9.7)

    sequential (x1000):
    lock_unlock              :      1.00 msec
    reentrant_lock_unlock    :      0.80 msec
    mixed_lock_unlock        :      0.88 msec
    lock_unlock_nonblocking  :      1.23 msec
    context_manager          :      5.29 msec

    threaded 10T (x100):
    lock_unlock              :     65.54 msec
    reentrant_lock_unlock    :     65.49 msec
    mixed_lock_unlock        :     86.61 msec
    lock_unlock_nonblocking  :     66.30 msec
    context_manager          :     84.27 msec

    Testing FastRLock (0.8)

    sequential (x1000):
    lock_unlock              :      0.60 msec
    reentrant_lock_unlock    :      0.53 msec
    mixed_lock_unlock        :      0.51 msec
    lock_unlock_nonblocking  :      0.54 msec
    context_manager          :      3.56 msec

    threaded 10T (x100):
    lock_unlock              :     63.64 msec
    reentrant_lock_unlock    :     69.93 msec
    mixed_lock_unlock        :     64.66 msec
    lock_unlock_nonblocking  :     69.28 msec
    context_manager          :     80.07 msec
