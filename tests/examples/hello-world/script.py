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

# Here's a callback.  We will wire it up below:
def on_pass_execution(p, fn):
    # This pass is called fairly early on, per-function, after the
    # CFG has been built:
    if p.name == '*warn_function_return':
        # For this pass, "fn" will be an instance of gcc.Function:
        print('fn: %r' % fn)
        print('fn.decl.name: %r' % fn.decl.name)

        # fn.decl is an instance of gcc.FunctionDecl:
        print('return type: %r' % str(fn.decl.type.type))
        print('argument types: %r' % [str(t) for t in fn.decl.type.argument_types])

        assert isinstance(fn.cfg, gcc.Cfg) # None for some early passes
        assert len(fn.cfg.basic_blocks) == 3
        assert fn.cfg.basic_blocks[0] == fn.cfg.entry
        assert fn.cfg.basic_blocks[1] == fn.cfg.exit
        bb = fn.cfg.basic_blocks[2]
        for i,stmt in enumerate(bb.gimple):
            print 'gimple[%i]:' % i
            print '  str(stmt): %r' % str(stmt)
            print '  repr(stmt): %r' % repr(stmt)
            if isinstance(stmt, gcc.GimpleCall):
                from gccutils import pprint
                print('  type(stmt.fn): %r' % type(stmt.fn))
                print('  str(stmt.fn): %r' % str(stmt.fn))
                for i, arg in enumerate(stmt.args):
                    print('  str(stmt.args[%i]): %r' % (i, str(stmt.args[i])))
                print('  str(stmt.lhs): %s' % str(stmt.lhs))

# Wire up our callback:
gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      on_pass_execution)

