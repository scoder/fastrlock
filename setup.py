
import sys
import os
import re
from distutils.core import setup, Extension

with open('fastrlock/__init__.py') as f:
    VERSION = re.search(
        r'^__version__ \s* = \s* ["\'] ([0-9ab.]+) ["\']',
        f.read(), re.MULTILINE|re.VERBOSE).group(1)

BASEDIR = os.path.dirname(__file__)
PKGNAME = 'fastrlock'
PKGDIR = os.path.join(BASEDIR, PKGNAME)
MODULES = [filename[:-4] for filename in os.listdir(PKGDIR)
           if filename.endswith('.pyx')]

ext_args = {}
extra_setup_args = {}


# support 'test' target if setuptools/distribute is available

if 'setuptools' in sys.modules:
    extra_setup_args['test_suite'] = 'fastrlock.tests.suite'
    extra_setup_args["zip_safe"] = False


def has_option(name):
    if name in sys.argv[1:]:
        sys.argv.remove(name)
        return True
    return False


if has_option('--without-assert'):
    ext_args['define_macros'] = [('CYTHON_WITHOUT_ASSERTIONS', None)]


use_cython = has_option('--with-cython')
if not use_cython:
    if not all(os.path.isfile(os.path.join(PKGDIR, module_name+'.c'))
               for module_name in MODULES):
        print("NOTE: generated sources not available, need Cython to build")
        use_cython = True


cythonize = None
if use_cython:
    try:
        from Cython.Build import cythonize
        import Cython.Compiler.Version
        print("building with Cython " + Cython.Compiler.Version.version)
        source_extension = ".pyx"
    except ImportError:
        print("WARNING: trying to build with Cython, but it is not installed")
        cythonize = None
        source_extension = ".c"
else:
    print("building without Cython")
    source_extension = ".c"


ext_modules = [
    Extension(
        '%s.%s' % (PKGNAME, module_name),
        sources=[os.path.join(PKGNAME, module_name+source_extension)],
        **ext_args)
    for module_name in MODULES]


if cythonize is not None:
    ext_modules = cythonize(ext_modules)


def read_file(filename):
    f = open(os.path.join(BASEDIR, filename))
    try:
        return f.read()
    finally:
        f.close()


long_description = '\n\n'.join([
    read_file(text_file)
    for text_file in ['README.rst', 'CHANGES.rst']])


if sys.version_info >= (2,6):
    extra_setup_args['license'] = 'MIT style'


setup(
    name="fastrlock",
    version=VERSION,
    author="Stefan Behnel",
    author_email="stefan_ml@behnel.de",
    url="https://github.com/scoder/fastrlock",
    description="Fast, re-entrant optimistic lock implemented in Cython",

    long_description=long_description,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Cython',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
        'Topic :: Software Development',
    ],

    packages=[PKGNAME],
    package_data = {PKGNAME: ['*.pxd']},
    ext_modules = ext_modules,
    **extra_setup_args
)
