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

import gcc
import gccutils

def on_finish_unit():
    fn_type_decl = gccutils.get_global_typedef('example_fn_type')
    assert isinstance(fn_type_decl, gcc.TypeDecl)

    print('fn_type_decl.name: %r' % fn_type_decl.name)

    fn_type = fn_type_decl.type
    assert isinstance(fn_type, gcc.FunctionType)
    print('str(fn_type): %r' % str(fn_type))
    print('str(fn_type.type): %r' % str(fn_type.type))
    assert isinstance(fn_type.argument_types, tuple)
    print('argument_types: %r' % [str(t) for t in fn_type.argument_types])
    try:
        fn_type.sizeof
        assert 0 # an exception should have been raised
    except:
        err = sys.exc_info()[1]
        print('err: %s' % err)



gcc.register_callback(gcc.PLUGIN_FINISH_UNIT,
                      on_finish_unit)
