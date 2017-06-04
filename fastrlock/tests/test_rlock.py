# -*- coding: utf-8 -*-

try:
    from thread import start_new_thread, get_ident
except ImportError:
    # Python 3?
    from _thread import start_new_thread, get_ident
import threading
import unittest
import time
import sys
import gc

from fastrlock import rlock

IS_PYTHON3 = sys.version_info[0] >= 3

try:
    _next = next
except NameError:
    def _next(o):
        return o.next()

unicode_type = type(IS_PYTHON3 and 'abc' or 'abc'.decode('ASCII'))


def _wait():
    # A crude wait/yield function not relying on synchronization primitives.
    time.sleep(0.01)


class Bunch(object):
    """
    A bunch of threads.
    """
    def __init__(self, f, n, wait_before_exit=False):
        """
        Construct a bunch of `n` threads running the same function `f`.
        If `wait_before_exit` is True, the threads won't terminate until
        do_finish() is called.
        """
        self.f = f
        self.n = n
        self.started = []
        self.finished = []
        self._can_exit = not wait_before_exit
        def task():
            tid = get_ident()
            self.started.append(tid)
            try:
                f()
            finally:
                self.finished.append(tid)
                while not self._can_exit:
                    _wait()
        for i in range(n):
            start_new_thread(task, ())

    def wait_for_started(self):
        while len(self.started) < self.n:
            _wait()

    def wait_for_finished(self):
        while len(self.finished) < self.n:
            _wait()

    def do_finish(self):
        self._can_exit = True


################################################################################
# tests for the FastRLock implementation

class TestFastRLock(unittest.TestCase):
    """Copied from CPython's test.lock_tests module
    """
    locktype = rlock.FastRLock
    Bunch = Bunch

    def tearDown(self):
        gc.collect()

    # the locking tests

    """
    Tests for both recursive and non-recursive locks.
    """

    def test_constructor(self):
        lock = self.locktype()
        del lock

    def test_acquire_destroy(self):
        lock = self.locktype()
        lock.acquire()
        del lock

    def test_acquire_release(self):
        lock = self.locktype()
        lock.acquire()
        lock.release()
        del lock

    def test_try_acquire(self):
        lock = self.locktype()
        self.assertTrue(lock.acquire(False))
        lock.release()

    def test_try_acquire_contended(self):
        lock = self.locktype()
        lock.acquire()
        result = []
        def f():
            result.append(lock.acquire(False))
        self.Bunch(f, 1).wait_for_finished()
        self.assertFalse(result[0])
        lock.release()

    def test_acquire_contended(self):
        lock = self.locktype()
        lock.acquire()
        N = 5
        def f():
            lock.acquire()
            lock.release()

        b = self.Bunch(f, N)
        b.wait_for_started()
        _wait()
        self.assertEqual(len(b.finished), 0)
        lock.release()
        b.wait_for_finished()
        self.assertEqual(len(b.finished), N)

    def test_with(self):
        lock = self.locktype()
        def f():
            lock.acquire()
            lock.release()
        def _with(err=None):
            with lock:
                if err is not None:
                    raise err
        _with()
        # Check the lock is unacquired
        self.Bunch(f, 1).wait_for_finished()
        self.assertRaises(TypeError, _with, TypeError)
        # Check the lock is unacquired
        self.Bunch(f, 1).wait_for_finished()

    def test_thread_leak(self):
        # The lock shouldn't leak a Thread instance when used from a foreign
        # (non-threading) thread.
        lock = self.locktype()
        def f():
            lock.acquire()
            lock.release()
        n = len(threading.enumerate())
        # We run many threads in the hope that existing threads ids won't
        # be recycled.
        self.Bunch(f, 15).wait_for_finished()
        self.assertEqual(n, len(threading.enumerate()))

    """
    Tests for non-recursive, weak locks
    (which can be acquired and released from different threads).
    """

    def _test_reacquire_nonrecursive(self):
        # Lock needs to be released before re-acquiring.
        lock = self.locktype()
        phase = []
        def f():
            lock.acquire()
            phase.append(None)
            lock.acquire()
            phase.append(None)
        start_new_thread(f, ())
        while len(phase) == 0:
            _wait()
        _wait()
        self.assertEqual(len(phase), 1)
        lock.release()
        while len(phase) == 1:
            _wait()
        self.assertEqual(len(phase), 2)

    def test_different_thread_release_succeeds(self):
        # Lock can be released from a different thread.
        lock = self.locktype()
        lock.acquire()
        def f():
            lock.release()
        b = self.Bunch(f, 1)
        b.wait_for_finished()
        lock.acquire()
        lock.release()

    """
    Tests for recursive locks.
    """

    def test_reacquire(self):
        lock = self.locktype()
        lock.acquire()
        lock.acquire()
        lock.release()
        lock.acquire()
        lock.release()
        lock.release()

    def test_release_unacquired(self):
        # Cannot release an unacquired lock
        lock = self.locktype()
        self.assertRaises(RuntimeError, lock.release)
        lock.acquire()
        lock.acquire()
        lock.release()
        lock.acquire()
        lock.release()
        lock.release()
        self.assertRaises(RuntimeError, lock.release)

    def test_different_thread_release_fails(self):
        # Cannot release from a different thread
        lock = self.locktype()
        def f():
            lock.acquire()
        b = self.Bunch(f, 1, True)
        try:
            self.assertRaises(RuntimeError, lock.release)
        finally:
            b.do_finish()

    def test__is_owned(self):
        lock = self.locktype()
        self.assertFalse(lock._is_owned())
        lock.acquire()
        self.assertTrue(lock._is_owned())
        lock.acquire()
        self.assertTrue(lock._is_owned())
        result = []
        def f():
            result.append(lock._is_owned())
        self.Bunch(f, 1).wait_for_finished()
        self.assertFalse(result[0])
        lock.release()
        self.assertTrue(lock._is_owned())
        lock.release()
        self.assertFalse(lock._is_owned())


if __name__ == '__main__':
    import doctest
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(rlock))
    suite.addTest(unittest.defaultTestLoader.loadTestsFromName('__main__'))
    suite.addTest(doctest.DocFileSuite('../../README.rst'))
    runner = unittest.TextTestRunner(verbosity=2)
    if not runner.run(suite).wasSuccessful():
        sys.exit(1)
