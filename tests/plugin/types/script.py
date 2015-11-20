#   Copyright 2011 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2011 Red Hat, Inc.
#
#   This is free software: you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful, but
#   WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see
#   <http://www.gnu.org/licenses/>.

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
        assert isinstance(t.sizeof, int)
        print('  t.sizeof: %r' % t.sizeof)
        # gccutils.pprint(t)

    # Pick some types that ought to be arch-independent and thus suitable
    # for a unit test
    dump_integer_type(gcc.Type.unsigned_char())
    dump_integer_type(gcc.Type.signed_char())

    print(gcc.Type.char().const)
    print(gcc.Type.char().const_equivalent.const)
    print(gcc.Type.char().const_equivalent.restrict_equivalent.const)
    print(gcc.Type.char().const_equivalent.volatile_equivalent.const)

    def dump_real_type(t):
        print('gcc.Type: %r' % str(t))
        print('  t.const: %r' % t.const)
        print('  t.precision: %r' % t.precision)
        assert isinstance(t.sizeof, int)
        print('  t.sizeof: %r' % t.sizeof)

    dump_real_type(gcc.Type.float())
    dump_real_type(gcc.Type.double())

gcc.register_callback(gcc.PLUGIN_FINISH_UNIT,
                      on_finish_unit)
