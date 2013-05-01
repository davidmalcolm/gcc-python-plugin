#   Copyright 2013 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2013 Red Hat, Inc.
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
from gccutils import get_src_for_loc

DEBUG=0

def is_const(type_):
    if DEBUG:
        type_.debug()

    if hasattr(type_, 'const'):
        if type_.const:
            return True

    # Don't bother warning about an array of const e.g.
    # const char []
    if isinstance(type_, gcc.ArrayType):
        item_type = type_.dereference
        if is_const(item_type):
            return True


class StateFinder:
    def __init__(self):
        # Locate all declarations of variables holding "global" state:
        self.global_decls = set()

        for var in gcc.get_variables():
            type_ = var.decl.type

            if DEBUG:
                print('var.decl: %r' % var.decl)
                print(type_)

            # Don't bother warning about const data:
            if is_const(type_):
                continue

            self.global_decls.add(var.decl)
        if DEBUG:
            print('self.global_decls: %r' % self.global_decls)

        self.state_users = set()

    def find_state_users(self, node, loc):
        if isinstance(node, gcc.VarDecl):
            if node in self.global_decls:
                # store the state users for later replay, so that
                # we can eliminate duplicates
                #   e.g. two references to "q" in "q += p"
                # and replay in source-location order:
                self.state_users.add( (loc, node) )

    def flush(self):
        # Emit warnings, sorted by source location:
        for loc, node in sorted(self.state_users,
                                key=lambda pair:pair[0]):
            gcc.inform(loc,
                       'use of global state "%s %s" here'
                       % (node.type, node))

def on_pass_execution(p, fn):
    if p.name == '*free_lang_data':
        sf = StateFinder()

        # Locate uses of such variables:
        for node in gcc.get_callgraph_nodes():
            fun = node.decl.function
            if fun:
                cfg = fun.cfg
                if cfg:
                    for bb in cfg.basic_blocks:
                        stmts = bb.gimple
                        if stmts:
                            for stmt in stmts:
                                stmt.walk_tree(sf.find_state_users,
                                               stmt.loc)

        # Flush the data that was found:
        sf.flush()

gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      on_pass_execution)
