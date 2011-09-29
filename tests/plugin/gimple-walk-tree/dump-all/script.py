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

# Selftest for gcc.Gimple.walk_tree
import gcc

class DumpTreeNodesPass(gcc.GimplePass):
    def execute(self, fun):
        # This is called per-function during compilation:
        print('fun: %s' % fun)
        for bb in fun.cfg.basic_blocks:
            if bb.gimple:
                for stmt in bb.gimple:
                    print('  stmt: %s' % stmt)
                    stmt.walk_tree(self.dump_node, stmt.loc)

    def dump_node(self, node, loc):
        print('    node: %r (%s)' % (node, node))

ps = DumpTreeNodesPass(name='dump-tree-nodes')
ps.register_after('cfg')
