GCC=gcc
PLUGIN_SOURCE_FILES= gcc-python.c
PLUGIN_OBJECT_FILES= $(patsubst %.c,%.o,$(PLUGIN_SOURCE_FILES))
GCCPLUGINS_DIR:= $(shell $(GCC) --print-file-name=plugin)

PYTHON_CONFIG=python-config
PYTHON_CFLAGS=$(shell $(PYTHON_CONFIG) --cflags)
PYTHON_LDFLAGS=$(shell $(PYTHON_CONFIG) --ldflags)

CFLAGS+= -I$(GCCPLUGINS_DIR)/include -fPIC -O2 -Wall -Werror -g $(PYTHON_CFLAGS) $(PYTHON_LDFLAGS)

plugin: gcc-python.so

gcc-python.so: $(PLUGIN_OBJECT_FILES)
	$(GCC) $(CFLAGS) -shared $^ -o $@

clean:
	rm -f *.so *.o

# Hint for debugging: add -v to the gcc options 
# to get a command line for invoking individual subprocesses
# Doing so seems to require that paths be absolute, rather than relative
# to this directory
test: plugin
	gcc -v -fplugin=$(shell pwd)/gcc-python.so $(shell pwd)/test.c

