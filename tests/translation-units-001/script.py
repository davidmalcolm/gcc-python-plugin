# Verify that we can lookup identifiers by name

import gcc

def on_pass_execution(p, data):
    if p.name == 'visibility':
        print 'len(gcc.get_translation_units()): %i' % len(gcc.get_translation_units())
        u = gcc.get_translation_units()[0]
        print 'type(u): %s' % type(u)
        print 'u.language: %r' % u.language
        print 'type(u.block): %s' % type(u.block)
        for v in u.block.vars:
            if v.name == 'test_typedef':
                print 'v.name: %r' % v.name
                print 'type(v): %s' % v

            if v.name == 'test_var':
                print 'v.name: %r' % v.name
                print 'type(v): %s' % v
        #print 'u.block: %s' % u.block
        #u.block.debug()


gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      on_pass_execution)
