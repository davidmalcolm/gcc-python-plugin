# Sample python script, to be run by our gcc plugin (see "make test")
print "hello world"

import gcc

help(gcc)

gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION)


