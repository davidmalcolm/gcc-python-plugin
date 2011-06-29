#   Copyright 2011 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2011 Red Hat, Inc.
#
#   This is free software: you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful, but
#   WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see
#   <http://www.gnu.org/licenses/>.

GCC=gcc

PLUGIN_SOURCE_FILES= \
  gcc-python.c \
  gcc-python-cfg.c \
  gcc-python-closure.c \
  gcc-python-function.c \
  gcc-python-gimple.c \
  gcc-python-location.c \
  gcc-python-option.c \
  gcc-python-parameter.c \
  gcc-python-pass.c \
  gcc-python-pretty-printer.c \
  gcc-python-tree.c \
  gcc-python-variable.c \
  autogenerated-cfg.c \
  autogenerated-option.c \
  autogenerated-function.c \
  autogenerated-gimple.c \
  autogenerated-location.c \
  autogenerated-parameter.c \
  autogenerated-pass.c \
  autogenerated-pretty-printer.c \
  autogenerated-tree.c \
  autogenerated-variable.c

PLUGIN_OBJECT_FILES= $(patsubst %.c,%.o,$(PLUGIN_SOURCE_FILES))
GCCPLUGINS_DIR:= $(shell $(GCC) --print-file-name=plugin)

PYTHON_CONFIG=python-config
#PYTHON_CONFIG=python-debug-config

PYTHON_CFLAGS=$(shell $(PYTHON_CONFIG) --cflags)
PYTHON_LDFLAGS=$(shell $(PYTHON_CONFIG) --ldflags)

CFLAGS+= -I$(GCCPLUGINS_DIR)/include -fPIC -O2 -Wall -Werror -g $(PYTHON_CFLAGS) $(PYTHON_LDFLAGS)

all: testcpybuilder test-suite testcpychecker

plugin: python.so

python.so: $(PLUGIN_OBJECT_FILES)
	$(GCC) $(CFLAGS) -shared $^ -o $@

clean:
	rm -f *.so *.o
	rm -f autogenerated*

autogenerated-gimple-types.txt: gimple-types.txt.in
	cpp $(CFLAGS) $^ -o $@

autogenerated-tree-types.txt: tree-types.txt.in
	cpp $(CFLAGS) $^ -o $@

autogenerated-cfg.c: cpybuilder.py generate-cfg-c.py
	python generate-cfg-c.py > $@

autogenerated-function.c: cpybuilder.py generate-function-c.py
	python generate-function-c.py > $@

autogenerated-gimple.c: cpybuilder.py generate-gimple-c.py autogenerated-gimple-types.txt maketreetypes.py
	python generate-gimple-c.py > $@

autogenerated-location.c: cpybuilder.py generate-location-c.py
	python generate-location-c.py > $@

autogenerated-option.c: cpybuilder.py generate-option-c.py
	python generate-option-c.py > $@

autogenerated-parameter.c: cpybuilder.py generate-parameter-c.py
	python generate-parameter-c.py > $@

autogenerated-pass.c: cpybuilder.py generate-pass-c.py
	python generate-pass-c.py > $@

autogenerated-pretty-printer.c: cpybuilder.py generate-pretty-printer-c.py
	python generate-pretty-printer-c.py > $@

autogenerated-tree.c: cpybuilder.py generate-tree-c.py autogenerated-tree-types.txt maketreetypes.py
	python generate-tree-c.py > $@

autogenerated-variable.c: cpybuilder.py generate-variable-c.py autogenerated-gimple-types.txt maketreetypes.py
	python generate-variable-c.py > $@

# Hint for debugging: add -v to the gcc options 
# to get a command line for invoking individual subprocesses
# Doing so seems to require that paths be absolute, rather than relative
# to this directory
TEST_CFLAGS= \
  -fplugin=$(shell pwd)/python.so \
  -fplugin-arg-python-script=test.py

# A catch-all test for quick experimentation with the API:
test: plugin
	gcc -v $(TEST_CFLAGS) $(shell pwd)/test.c

# Selftest for the cpychecker.py code:
testcpychecker: plugin
	python testcpychecker.py -v

# Selftest for the cpybuilder code:
testcpybuilder:
	python testcpybuilder.py -v

dump_gimple:
	gcc -fdump-tree-gimple $(shell pwd)/test.c

debug: plugin
	gcc -v $(TEST_CFLAGS) $(shell pwd)/test.c

# A simple demo, to make it easy to demonstrate the cpychecker:
demo: plugin
	gcc -fplugin=$(shell pwd)/python.so -fplugin-arg-python-script=cpychecker.py $(shell python-config --cflags) demo.c

test-suite: plugin
	python run-test-suite.py

show-ssa: plugin
	./gcc-with-python show-ssa.py test.c
