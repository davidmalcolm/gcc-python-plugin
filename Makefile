GCC=gcc
PLUGIN_SOURCE_FILES= gcc-python.c
PLUGIN_OBJECT_FILES= $(patsubst %.c,%.o,$(PLUGIN_SOURCE_FILES))
GCCPLUGINS_DIR:= $(shell $(GCC) --print-file-name=plugin)
CFLAGS+= -I$(GCCPLUGINS_DIR)/include -fPIC -O2 -Wall

plugin: gcc-python.so

gcc-python.so: $(PLUGIN_OBJECT_FILES)
	$(GCC) $(CFLAGS) -shared $^ -o $@

clean:
	rm -f *.so *.o

test: plugin
	gcc -fplugin=./gcc-python.so test.c

