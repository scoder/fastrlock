PYTHON2?=python
PYTHON?=python3
SETUPFLAGS=
PACKAGENAME=fastrlock
VERSION=$(shell python -c 'import re; f=open("fastrlock/__init__.py"); print(re.search("__version__\s*=\s*[\x27\x22](.+)[\x27\x22]", f.read()).group(1)); f.close()')

PYTHON_WITH_CYTHON=$(shell $(PYTHON)  -c 'import Cython.Compiler' >/dev/null 2>/dev/null && echo " --with-cython" || true)
PY2_WITH_CYTHON=$(shell $(PYTHON2) -c 'import Cython.Compiler' >/dev/null 2>/dev/null && echo " --with-cython" || true)

# manylinux1 images still include Python 2.7
MANYLINUX_IMAGES= \
	manylinux1_x86_64 \
	manylinux1_i686 \
    manylinux_2_24_x86_64 \
    manylinux_2_24_i686 \
    manylinux_2_24_aarch64 \
    musllinux_1_1_x86_64 \
    musllinux_1_1_aarch64

.PHONY: all version inplace sdist build clean wheel_manylinux wheel

all: inplace


version:
	@echo $(VERSION)

inplace:
	$(PYTHON) setup.py $(SETUPFLAGS) build_ext -i $(PYTHON_WITH_CYTHON)

sdist dist/$(PACKAGENAME)-$(VERSION).tar.gz:
	$(PYTHON) setup.py $(SETUPFLAGS) sdist $(PYTHON_WITH_CYTHON)

build:
	$(PYTHON) setup.py $(SETUPFLAGS) build $(PYTHON_WITH_CYTHON)

wheel:
	$(PYTHON) setup.py $(SETUPFLAGS) bdist_wheel $(PYTHON_WITH_CYTHON)

qemu-user-static:
	docker run --rm --privileged hypriot/qemu-register

wheel_manylinux: sdist $(addprefix wheel_,$(MANYLINUX_IMAGES))
$(addprefix wheel_,$(filter-out %_x86_64, $(filter-out %_i686, $(MANYLINUX_IMAGES)))): qemu-user-static

wheel_%: dist/$(PACKAGENAME)-$(VERSION).tar.gz
	echo "Building wheels for $(PACKAGENAME) $(VERSION)"
	mkdir -p wheelhouse_$(subst wheel_,,$@)
	time docker run --rm -t \
		-v $(shell pwd):/io \
		-e CFLAGS="-O3 -g1 -mtune=generic -pipe -fPIC" \
		-e LDFLAGS="$(LDFLAGS) -fPIC" \
		-e WHEELHOUSE=wheelhouse_$(subst wheel_,,$@) \
		quay.io/pypa/$(subst wheel_,,$@) \
		bash -c '\
			rm -fr $(PACKAGENAME)-$(VERSION)/; \
			tar zxf /io/$< && cd $(PACKAGENAME)-$(VERSION)/ || exit 1; \
			for PYBIN in /opt/python/cp*/bin; do \
				PYVER="$$($$PYBIN/python -V)"; \
				PROFDIR="prof-$${PYVER// /_}"; \
				echo $$PYVER; \
				$$PYBIN/pip install -U pip setuptools; \
				make clean; rm -fr $$PROFDIR; \
				CFLAGS="$$CFLAGS -fprofile-generate -fprofile-dir=$$PROFDIR" $$PYBIN/python setup.py build_ext -i; \
				$$PYBIN/python lockbench.py flock quick; \
				CFLAGS="$$CFLAGS -fprofile-use -fprofile-correction -fprofile-dir=$$PROFDIR" $$PYBIN/python setup.py build_ext -i -f; \
				$$PYBIN/python lockbench.py rlock flock quick; \
				CFLAGS="$$CFLAGS -fprofile-use -fprofile-correction -fprofile-dir=$$PROFDIR" $$PYBIN/python setup.py bdist_wheel; \
		    done; \
		    for whl in dist/$(PACKAGENAME)-$(VERSION)-*-linux_*.whl; do auditwheel repair $$whl -w /io/$$WHEELHOUSE; done; \
		    '

clean:
	find . \( -name '*.o' -o -name '*.so' -o -name '*.py[cod]' -o -name '*.dll' \) -exec rm -f {} \;
	rm -rf build
