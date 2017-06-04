#if PY_VERSION_HEX < 0x03020000 && !defined(PY_LOCK_FAILURE)
#  define PY_LOCK_FAILURE 0
#  define PY_LOCK_ACQUIRED 1
#  define PY_LOCK_INTR -1
#endif
