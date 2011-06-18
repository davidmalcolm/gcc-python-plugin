# Verify the behavior of gcc.Type

import gcc
import gccutils

def on_finish_unit():
    def dump_integer_type(t):
        print('gcc.Type: %r' % str(t))
        print('  t.const: %r' % t.const)
        print('  t.unsigned: %r' % t.unsigned)
        print('  t.precision: %r' % t.precision)
        assert isinstance(t.min_value, gcc.IntegerCst)
        assert isinstance(t.max_value, gcc.IntegerCst)
        print('  t.min_value.constant: %r' % t.min_value.constant)
        print('  t.max_value.constant: %r' % t.max_value.constant)
        # gccutils.pprint(t)

    # Pick some types that ought to be arch-independent and thus suitable
    # for a unit test
    dump_integer_type(gcc.Type.unsigned_char())
    dump_integer_type(gcc.Type.signed_char())

gcc.register_callback(gcc.PLUGIN_FINISH_UNIT,
                      on_finish_unit)
