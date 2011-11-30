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

class TestPass(gcc.GimplePass):
    def execute(self, fn):
        print('fn: %r' % fn)
        print('  fn.decl.name: %r' % fn.decl.name)
        print('  fn.decl.fullname: %r' % fn.decl.fullname)
        print('  str(fn.decl): %s' % fn.decl)
        print('    type(fn): %r' % type(fn))
        print('    type(fn.decl): %r' % type(fn.decl))
        print('    type(fn.decl.type): %r' % type(fn.decl.type))

        for attr in ('public', 'private', 'protected', 'static'):
            print('  fn.decl.is_%s: %r' % (attr, getattr(fn.decl, 'is_%s' % attr)))

        #fn.decl.debug()

        # fn.decl is an instance of gcc.FunctionDecl:
        print('  return type: %r' % str(fn.decl.type.type))
        # fn.decl.type is an instance of gcc.MethodType for the methods:
        print('  argument types: %r' % [str(t) for t in fn.decl.type.argument_types])

        assert isinstance(fn.cfg, gcc.Cfg) # None for some early passes
        assert fn.cfg.basic_blocks[0] == fn.cfg.entry
        assert fn.cfg.basic_blocks[1] == fn.cfg.exit
        for blockidx, bb in enumerate(fn.cfg.basic_blocks):
            if bb.gimple:
                print('  block %i' % blockidx)
                for i,stmt in enumerate(bb.gimple):
                    print('    gimple[%i]:' % i)
                    print('      str(stmt): %r' % str(stmt))
                    print('      repr(stmt): %r' % repr(stmt))
                    if isinstance(stmt, gcc.GimpleCall):
                        print('    type(stmt.fn): %r' % type(stmt.fn))
                        print('    str(stmt.fn): %r' % str(stmt.fn))
                        print('    stmt.fn: %r' % stmt.fn)
                        if isinstance(stmt.fn, gcc.AddrExpr):
                            print('      stmt.fn.operand: %r' % stmt.fn.operand)
                            print('      stmt.fn.operand.fullname: %r' % stmt.fn.operand.fullname)
                        for i, arg in enumerate(stmt.args):
                            print('    str(stmt.args[%i]): %r' % (i, str(stmt.args[i])))
                        print('    str(stmt.lhs): %s' % str(stmt.lhs))

test_pass = TestPass(name='test-pass')
test_pass.register_after('cfg')
