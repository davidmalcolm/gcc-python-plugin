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
        assert isinstance(fn.decl, gcc.FunctionDecl)
        print('fn.decl.name: %r' % fn.decl.name)

        assert isinstance(fn.cfg, gcc.Cfg) # None for some early passes
        assert fn.cfg.basic_blocks[0] == fn.cfg.entry
        assert fn.cfg.basic_blocks[1] == fn.cfg.exit
        for bb in fn.cfg.basic_blocks:
            if bb.gimple:
                for i,stmt in enumerate(bb.gimple):
                    print('gimple[%i]:' % i)
                    print('  str(stmt): %r' % str(stmt))
                    print('  repr(stmt): %r' % repr(stmt))
                    if isinstance(stmt, gcc.GimpleSwitch):
                        print('    stmt.indexvar: %r' % stmt.indexvar)
                        print('    stmt.labels: %r' % stmt.labels)
                        for j, label in enumerate(stmt.labels):
                            print('      label[%i].low: %r' % (j, label.low))
                            print('      label[%i].high: %r' % (j, label.high))
                            print('      label[%i].target: %r' % (j, label.target))

gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      on_pass_execution)
