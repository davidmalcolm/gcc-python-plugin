# Verify that we can lookup identifiers by name

import gcc

def on_pass_execution(p, data):
    if p.name == 'visibility':
        foo = gcc.maybe_get_identifier('foo')
        print('str(foo): %s' % foo)
        print('type(foo): %s' % type(foo))

        bar = gcc.maybe_get_identifier('bar')
        print('str(bar): %s' % bar)
        print('type(bar): %s' % type(bar))


gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      on_pass_execution)
