# Verify that we can use gcc.get_translation_units()
import gcc

from gccutils import get_global_typedef

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

        td = get_global_typedef('test_typedef')
        print 'td: %s' % td



gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      on_pass_execution)
