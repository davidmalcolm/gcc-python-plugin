# Sample python script, to be run by our gcc plugin (see "make test")
#print "hello world"

import gcc

#import sys
#print 'sys.path:', sys.path
help(gcc)

def my_pass_execution_callback(*args, **kwargs):
    print('my_pass_execution_callback was called: args=%r  kwargs=%r' % (args, kwargs))
    #help(args[0])

def my_pre_genericize_callback(*args, **kwargs):
    print('my_pre_genericize_callback was called: args=%r  kwargs=%r' % (args, kwargs))
    #help(args[0])


#gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
#                      my_pass_execution_callback)
gcc.register_callback(gcc.PLUGIN_PRE_GENERICIZE,
                      my_pre_genericize_callback)

# Try some insane values:
#gcc.register_callback(-1, my_callback)

# Stupid hack idea: a UI for gcc:
#import gtk
#w = gtk.Window(gtk.WINDOW_TOPLEVEL)
#w.show()
#gtk.main()

