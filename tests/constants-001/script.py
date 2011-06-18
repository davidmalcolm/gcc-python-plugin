# Verify that we can extract constants correctly back to python

import gcc
import gccutils

def on_finish_unit():
    vars = gccutils.get_variables_as_dict()
    for name in sorted(vars):
        var = vars[name]
        assert isinstance(var.decl.initial, gcc.IntegerCst)
        print '%s: %s' % (name, hex(var.decl.initial.constant))

gcc.register_callback(gcc.PLUGIN_FINISH_UNIT,
                      on_finish_unit)
