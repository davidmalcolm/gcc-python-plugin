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

# Verify that we can inspect the initialization of arrays of structures.

import gcc

def on_pass_execution(p, data):
    if p.name == 'visibility':
        
        vars = gcc.get_variables()
        print('len(gcc.get_variables()) is %i' % len(gcc.get_variables()))
        for i, var in enumerate(vars):
            print('%i: var.decl.name = %r' % (i, var.decl.name))

            assert isinstance(var.decl, gcc.VarDecl)
            print('   var.decl.type: %s' % var.decl.type)

            assert isinstance(var.decl.type, gcc.ArrayType)
            print('   var.decl.type.type: %s' % var.decl.type.type)
        
            if var.decl.initial:
                assert isinstance(var.decl.initial, gcc.Constructor)
                print('   len(var.decl.initial.elements): %s' % len(var.decl.initial.elements))
                assert isinstance(var.decl.initial.elements, list)
                for j, (idx, value) in enumerate(var.decl.initial.elements):
                    assert isinstance(idx, gcc.IntegerCst) # FIXME: value ought to be j
                    print('     elements[%i]:' % j)
                    print('       value: %s' % value)
                    for k, (idx2, value2) in enumerate(value.elements):
                        print('       elements[%i].elements[%i]:' % (j, k))
                        print('         idx2: %s' % idx2)
                        print('         value2: %s' % value2)
                        if isinstance(idx2, gcc.Declaration):
                            print('         idx2.name: %r' % idx2.name)
                                    

gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      on_pass_execution)
