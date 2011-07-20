# -*- coding: utf-8 -*-
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
from gccutils import pprint

def on_pass_execution(p, fn):
    if p.name == '*warn_function_return':
        assert isinstance(fn, gcc.Function)
        print('fn: %r' % fn)

        assert isinstance(fn.cfg, gcc.Cfg) # None for some early passes
        for bb in fn.cfg.basic_blocks:
            if bb.gimple:
                for i,stmt in enumerate(bb.gimple):
                    print 'gimple[%i]:' % i
                    print '  str(stmt): %r' % str(stmt)
                    print '  repr(stmt): %r' % repr(stmt)
                    if isinstance(stmt, gcc.GimpleAssign):
                        print('  str(stmt.lhs): %r' % str(stmt.lhs))
                        print('  [str(stmt.rhs)]: %r' % [str(item) for item in stmt.rhs])
                        print('  [type(stmt.rhs)]: %r' % [type(item) for item in stmt.rhs])
                        if isinstance(stmt.rhs[0], gcc.AddrExpr):
                            operand = stmt.rhs[0].operand
                            print('    operand: %s' % operand)
                            print('    type(operand): %s' % type(operand))
                            assert isinstance(operand, gcc.ArrayRef)

                            # Verify properties of gcc.ArrayRef:
                            print('    operand.array: %r' % operand.array)
                            assert isinstance(operand.index, gcc.IntegerCst)
                            print('    operand.index: %s' % operand.index)

                        if isinstance(stmt.rhs[0], gcc.ArrayRef):
                            # Verify properties of gcc.ArrayRef:
                            print('    stmt.rhs[0].array: %r' % stmt.rhs[0].array)
                            assert isinstance(stmt.rhs[0].index, gcc.IntegerCst)
                            print('    stmt.rhs[0].index: %s' % stmt.rhs[0].index)

gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      on_pass_execution)

