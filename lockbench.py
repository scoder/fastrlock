import sys

from threading import Thread
from threading import RLock
from fastrlock.rlock import FastRLock as FLock

# Benchmark functions:

cython_code = []

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


cython_code.append("""
def lock_unlock(lock):
    lock_fastrlock(lock, -1, True)
    unlock_fastrlock(lock)
    lock_fastrlock(lock, -1, True)
    unlock_fastrlock(lock)
    lock_fastrlock(lock, -1, True)
    unlock_fastrlock(lock)
    lock_fastrlock(lock, -1, True)
    unlock_fastrlock(lock)
    lock_fastrlock(lock, -1, True)
    unlock_fastrlock(lock)
""")


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


cython_code.append("""
def reentrant_lock_unlock(lock):
    lock_fastrlock(lock, -1, True)
    lock_fastrlock(lock, -1, True)
    lock_fastrlock(lock, -1, True)
    lock_fastrlock(lock, -1, True)
    lock_fastrlock(lock, -1, True)
    unlock_fastrlock(lock)
    unlock_fastrlock(lock)
    unlock_fastrlock(lock)
    unlock_fastrlock(lock)
    unlock_fastrlock(lock)
""")


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


cython_code.append("""
def mixed_lock_unlock(lock):
    lock_fastrlock(lock, -1, True)
    unlock_fastrlock(lock)
    lock_fastrlock(lock, -1, True)
    lock_fastrlock(lock, -1, True)
    unlock_fastrlock(lock)
    lock_fastrlock(lock, -1, True)
    unlock_fastrlock(lock)
    lock_fastrlock(lock, -1, True)
    unlock_fastrlock(lock)
    unlock_fastrlock(lock)
""")


def context_manager(l):
    with l: pass
    with l:
        with l:
            with l: pass
            with l: pass
        with l:
            with l: pass
        with l:
            with l: pass
            with l: pass
    with l: pass
    with l:
        with l:
            with l: pass
            with l: pass
            with l:
                with l: pass
    with l: pass


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


cython_code.append("""
def lock_unlock_nonblocking(lock):
    if lock_fastrlock(lock, -1, False):
        unlock_fastrlock(lock)
    if lock_fastrlock(lock, -1, False):
        unlock_fastrlock(lock)
    if lock_fastrlock(lock, -1, False):
        unlock_fastrlock(lock)
    if lock_fastrlock(lock, -1, False):
        unlock_fastrlock(lock)
    if lock_fastrlock(lock, -1, False):
        unlock_fastrlock(lock)
""")


# End of benchmark functions


def threaded(l, test_func, tcount=10):
    threads = [ Thread(target=test_func, args=(l,)) for _ in range(tcount) ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


def run_benchmark(name, lock, version, functions, repeat_count, repeat_count_t):
    print('Testing %s (%s)' % (name, version))

    from timeit import Timer
    from functools import partial

    print("sequential (x%d):" % repeat_count)
    for function in functions:
        timer = Timer(partial(function, lock))
        print('%-25s: %9.2f msec' % (function.__name__, max(timer.repeat(repeat=4, number=repeat_count)) * 1000.0))

    print("threaded 10T (x%d):" % repeat_count_t)
    for function in functions:
        timer = Timer(partial(threaded, lock, function))
        print('%-25s: %9.2f msec' % (function.__name__, max(timer.repeat(repeat=4, number=repeat_count_t)) * 1000.0))


if sys.version_info < (3, 5):
    import imp

    def load_dynamic(name, module_path):
        return imp.load_dynamic(name, module_path)
else:
    import importlib.util as _importlib_util

    def load_dynamic(name, module_path):
        spec = _importlib_util.spec_from_file_location(name, module_path)
        module = _importlib_util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


def main():
    functions = [
        lock_unlock,
        reentrant_lock_unlock,
        mixed_lock_unlock,
        lock_unlock_nonblocking,
        context_manager,
        ]

    import fastrlock

    import glob
    import os.path
    import re
    import tempfile

    repeat_count = 100000
    repeat_count_t = 1000

    rlock = (RLock(), "%d.%d.%d" % sys.version_info[:3])
    flock = (FLock(), fastrlock.__version__)

    locks = []
    args = sys.argv[1:]
    if 'rlock' in args:
        locks.append(rlock)
    if 'flock' in args:
        locks.append(flock)
    if not args:
        locks = [rlock, flock]

    for _ in range(args.count('quick')):
        repeat_count = max(10, repeat_count // 100)
        repeat_count_t = max(5, repeat_count_t // 10)

    for lock, version in locks:
        name = type(lock).__name__
        run_benchmark(name, lock, version, functions, repeat_count, repeat_count_t)

    if 'cython' in args or not args:
        lock, version = flock

        from Cython.Build.Cythonize import cython_compile, parse_args

        basepath = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix='.pyx') as f:
                code = '\n'.join(cython_code)
                cy_function_names = re.findall(r"def (\w+)\(", code)
                f.write("from fastrlock.rlock cimport lock_fastrlock, unlock_fastrlock\n\n")
                f.write(code)
                f.flush()

                options, _ = parse_args(["", f.name, "-3", "--force", "--inplace"])
                cython_compile(f.name, options)

            basepath = os.path.splitext(f.name)[0]
            for ext in [".*.so", ".*.pyd", ".so", ".pyd"]:
                so_paths = glob.glob(basepath + ext)
                if so_paths:
                    so_path = so_paths[0]
                    break
            else:
                print("Failed to find Cython compiled module")
                sys.exit(1)

            module = load_dynamic(os.path.basename(basepath), so_path)

            cy_functions = [getattr(module, name) for name in cy_function_names]

            run_benchmark("Cython interface of %s" % type(lock).__name__, lock, version,
                          cy_functions, repeat_count, repeat_count_t)

        finally:
            if basepath:
                files = glob.glob(basepath + ".*")  # .c, .so / .pyd
                if len(files) > 3:
                    print("Found too many artefacts, not deleting temporary files")
                else:
                    for filename in files:
                        os.unlink(filename)


if __name__ == '__main__':
    main()
