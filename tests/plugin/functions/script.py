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

# Verify examining details of functions

import gcc
from gccutils import pprint

def on_pass_execution(p, fn):
    if p.name == '*warn_function_return':
        assert isinstance(fn, gcc.Function)
        print('fn: %r' % fn)

        assert isinstance(fn.decl, gcc.FunctionDecl)
        print('fn.decl.name: %r' % fn.decl.name)

        assert isinstance(fn.decl, gcc.FunctionDecl)
        #print(fn.decl.type)
        #print(fn.decl.type.argument_types)
        #pprint(fn.decl)

        print('len(fn.local_decls): %r' % len(fn.local_decls))
        for i, local in enumerate(fn.local_decls):
            print('local_decls[%i]' % i)
            print('  type(local): %r' % type(local))
            print('  local.name: %r' % local.name)
            print('  local.context: %r' % local.context)
            # The "initial" only seems to be present for static variables
            # with initializers.  Other variables seem to get initialized
            # in explicit gimple statements (see below)
            if local.initial:
                print('  local.initial.constant: %r' % local.initial.constant)
            else:
                print('  local.initial: %r' % local.initial)
            print('  str(local.type): %r' % str(local.type))
            #pprint(local)
            #local.debug()

        print('fn.funcdef_no: %r' % fn.funcdef_no)
        print('fn.start: %r' % fn.start)
        print('fn.end: %r' % fn.end)

        assert isinstance(fn.cfg, gcc.Cfg) # None for some early passes
        assert len(fn.cfg.basic_blocks) == 3
        assert fn.cfg.basic_blocks[0] == fn.cfg.entry
        assert fn.cfg.basic_blocks[1] == fn.cfg.exit
        bb = fn.cfg.basic_blocks[2]
        for i,stmt in enumerate(bb.gimple):
            print('gimple[%i]:' % i)
            print('  str(stmt): %r' % str(stmt))
            print('  repr(stmt): %r' % repr(stmt))
            if isinstance(stmt, gcc.GimpleAssign):
                print('  str(stmt.lhs): %r' % str(stmt.lhs))
                print('  [str(stmt.rhs)]: %r' % [str(item) for item in stmt.rhs])
            #print(dir(stmt))
            #pprint(stmt)


        print('fn.decl.arguments: %r' % fn.decl.arguments)
        for i, arg in enumerate(fn.decl.arguments):
            print('  arg[%i]:' % i)
            print('    arg.name: %r' % arg.name)
            print('    str(arg.type): %r' % str(arg.type))
        print('type(fn.decl.result): %r' % type(fn.decl.result))
        print('  str(fn.decl.result.type): %r' % str(fn.decl.result.type))


gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      on_pass_execution)
