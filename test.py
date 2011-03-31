# Sample python script, to be run by our gcc plugin (see "make test")
print "hello world"

import gcc

help(gcc)

def my_callback(*args, **kwargs):
    print('my_callback was called: args=%r  kwargs=%r' % (args, kwargs))

gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION, my_callback)

# Try some insane values:
#gcc.register_callback(-1, my_callback)

# Stupid hack idea: a UI for gcc:
#import gtk
#w = gtk.Window(gtk.WINDOW_TOPLEVEL)
#w.show()
#gtk.main()

