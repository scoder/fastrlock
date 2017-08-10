
from threading import Thread
from threading import RLock
from fastrlock.rlock import FastRLock as FLock

def lock_unlock(l):
    l.acquire()
    l.release()
    l.acquire()
    l.release()
    l.acquire()
    l.release()
    l.acquire()
    l.release()
    l.acquire()
    l.release()

def reentrant_lock_unlock(l):
    l.acquire()
    l.acquire()
    l.acquire()
    l.acquire()
    l.acquire()
    l.release()
    l.release()
    l.release()
    l.release()
    l.release()

def mixed_lock_unlock(l):
    l.acquire()
    l.release()
    l.acquire()
    l.acquire()
    l.release()
    l.acquire()
    l.release()
    l.acquire()
    l.release()
    l.release()

def lock_unlock_nonblocking(l):
    if l.acquire(False):
        l.release()
    if l.acquire(False):
        l.release()
    if l.acquire(False):
        l.release()
    if l.acquire(False):
        l.release()
    if l.acquire(False):
        l.release()


def threaded(l, test_func, tcount=10):
    threads = [ Thread(target=test_func, args=(l,)) for _ in range(tcount) ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


if __name__ == '__main__':
    functions = [
        lock_unlock,
        reentrant_lock_unlock,
        mixed_lock_unlock,
        lock_unlock_nonblocking,
        ]

    from timeit import Timer
    from functools import partial

    for name, lock in [('RLock', RLock()), ('FLock', FLock())]:
        print('Testing %s' % name)
        repeat_count = 100000
        print("sequential (x%d):" % repeat_count)
        for function in functions:
            timer = Timer(partial(function, lock))
            print('%-25s: %.3f sec' % (function.__name__, max(timer.repeat(repeat=4, number=repeat_count))))

        repeat_count = 1000
        print("threaded 10T (x%d):" % repeat_count)
        for function in functions:
            timer = Timer(partial(threaded, lock, function))
            print('%-25s: %.3f sec' % (function.__name__, max(timer.repeat(repeat=4, number=repeat_count))))
