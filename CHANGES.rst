===================
fastrlock changelog
===================

0.8.2 (2023-08-27)
==================

* Rebuilt with Cython 3.0.2 to add Python 3.12 support.


0.8.1 (2022-11-02)
==================

* Rebuilt with Cython 3.0.0a11 to add Python 3.11 support.


0.8 (2021-10-22)
================

* Rebuilt with Cython 3.0.0a9 to improve the performance in recent
  Python 3.x versions.


0.7 (2021-10-21)
================

* Adapted for unsigned thread IDs, as used by Py3.7+.
  (original patch by Guilherme Dantas)

* Build with Cython 0.29.24 to support Py3.10 and later.


0.6 (2021-03-21)
================

* Rebuild with Cython 0.29.22 to support Py3.9 and later.


0.5 (2020-06-05)
================

* Rebuild with Cython 0.29.20 to support Py3.8 and later.


0.4 (2018-08-24)
================

* Rebuild with Cython 0.28.5.

* Linux wheels are faster through profile guided optimisation.

* Add missing file to sdist.
  (patch by Mark Harfouche, Github issue #5)


0.3 (2017-08-10)
================

* improve cimport support of C-API
  (patch by Naotoshi Seo, Github issue #3)

* provide ``fastrlock.__version__``


0.2 (2017-08-09)
================

* add missing readme file to sdist


0.1 (2017-06-04)
================

* initial release
