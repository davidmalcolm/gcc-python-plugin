# Verify that libcpychecker can categorize C functions as Python methods
# (and thus know which refcounting rules to apply)
import gcc
from libcpychecker import get_all_PyMethodDef_methods

def on_pass_execution(p, data):
    if p.name == 'visibility':
        methods = get_all_PyMethodDef_methods()
        print('len(methods): %s' % len(methods))
        for i, m in enumerate(methods):
            print('m[%i]:' % i)
            print('  decl: %s' % m[0])
            print('  loc: %s' % m[1])

gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      on_pass_execution)
