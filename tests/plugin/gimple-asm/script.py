#   Copyright 2012 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2012 Red Hat, Inc.
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

        if fn.cfg: # None for some early passes
            print('CFG:')
            for bb in fn.cfg.basic_blocks:
                print('  BLOCK %i' % bb.index)
                if bb.gimple:
                    for i,stmt in enumerate(bb.gimple):
                        print('  gimple[%i]:' % i)
                        print('    str(stmt): %r' % str(stmt))
                        print('    repr(stmt): %r' % repr(stmt))
                        if isinstance(stmt, gcc.GimpleAsm):
                            # (see dump_gimple_asm in gcc/gimple-pretty-print.c)
                            print('     stmt.string: %r' % stmt.string)

gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      on_pass_execution)
