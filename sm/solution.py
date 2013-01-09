#   Copyright 2012, 2013 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2012, 2013 Red Hat, Inc.
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


# We could create a separate graph, but it's probably easier
# to simply add the state information directly to the node
# It's the dot visualization we want, though, that makes it easy to debug

from gccutils import invoke_dot, get_src_for_loc
from gccutils.dot import Table, Tr, Td, Text, Br, Font
from gccutils.graph import Graph, Node, Edge

import sm.dataflow
from sm.utils import Timer, stateset_to_str, equivcls_to_str

class Solution:
    def __init__(self, ctx):
        self.ctxt = ctx

    def dump(self, out):
        global _indent
        _indent = 0
        def writeln(line, indent=0):
            global _indent
            _indent += indent
            out.write(' ' * _indent)
            out.write(line)
            out.write('\n')
            _indent -= indent

        writeln('SOLUTION FOR %s' % self.ctxt.sm.name)
        _indent += 2

        writeln('; underlying graph has: %i nodes  %i edges'
                  % (len(self.ctxt.graph.nodes),
                     len(self.ctxt.graph.edges)))

        # 1st pass: enumerate nodes in topologically-sorted order:
        nodes = self.ctxt.graph.topologically_sorted_nodes()
        index_for_node = {}
        node_for_index = {}
        for i, node in enumerate(nodes):
            index_for_node[node] = i
            node_for_index[i] = node

        # 2nd pass: write out the nodes with their edges:
        for i, node in enumerate(nodes):
            # Write the node:
            writeln('%i: %s' % (i, node))
            _indent += 4
            if node.stmt:
                if node.stmt.loc:
                    writeln('src: %s: %s' % (node.stmt.loc, get_src_for_loc(node.stmt.loc)))
            facts = self.ctxt.facts_for_node[node]
            writeln('facts: %s' % facts)
            if facts is not None:
                writeln('partitions: {%s}'
                        % ', '.join(['{%s}' % ', '.join([str(expr)
                                                         for expr in equivcls])
                                     for equivcls in facts.get_equiv_classes()]))
            # Write out state information from fixed point solver:
            writeln('fixed point states:')
            states = self.ctxt.states_for_node[node]
            if states:
                for equivcls in states._dict:
                    writeln('%s: %s'
                            % (equivcls_to_str(equivcls),
                               stateset_to_str(states._dict[equivcls])),
                            indent=2)
            else:
                writeln('None', indent=2)

            _indent -= 2

            for edge in node.succs:
                if edge.true_value:
                    boolstr = "true: "
                elif edge.false_value:
                    boolstr = "false: "
                else:
                    boolstr = ""
                possible_matches = self.ctxt.possible_matches_for_edge[edge]
                if possible_matches:
                    writeln('possible matches:',
                            indent=4)
                    for match in possible_matches:
                        writeln(match.describe(self.ctxt),
                                indent=6)
            _indent -= 2

    def to_dot(self, name):
        # (a handy debug method is essential)
        # basically we want to reuse the underlying graph's to_dot, but
        # use some diferent policy...
        class SolutionRenderer:
            def __init__(self, solution):
                self.solution = solution
            def node_to_dot_html(self, node):
                # raise foo # FIXME: we'll annotate this:

                inner = node.to_dot_html(self)
                table = Table(cellborder=1)
                states = self.solution.ctxt.states_for_node[node]
                if states:
                    for equivcls in states._dict:
                        tr = table.add_child(Tr())
                        td = tr.add_child(Td(align='left'))
                        td.add_child(Text('%s: %s'
                                          % (equivcls_to_str(equivcls),
                                             stateset_to_str(states._dict[equivcls]))))
                else:
                    tr = table.add_child(Tr())
                    td = tr.add_child(Td(align='left'))
                    td.add_child(Text('NOT REACHED'))

                facts = self.solution.ctxt.facts_for_node[node]
                if facts is not None:
                    for fact in facts.set_:
                        tr = table.add_child(Tr())
                        td = tr.add_child(Td(align='left'))
                        td.add_child(Text('FACT: %s' % (fact, )))
                        #td.add_child(Text('FACT: %r' % fact))
                else:
                    tr = table.add_child(Tr())
                    td = tr.add_child(Td(align='left'))
                    td.add_child(Text('NO FACTS'))
                tr = table.add_child(Tr())
                td = tr.add_child(Td(align='left'))
                td.add_child(inner)
                return table

        return self.ctxt.graph.to_dot(name, SolutionRenderer(self))

    def get_shortest_path_to(self, dstnode, equivcls, state):
        # backtrack from destination until you reach a srcnode whilst
        # obeying various restrictions:
        #   * equivcls/states have to match (or have state transitions)
        #   * call stack has to be obeyed: return to correct caller
        #   * perhaps some simple rules about known "state", to suppress
        #   the most obvious false positives

        ctxt = self.ctxt

        ctxt.debug('get_shortest_path_to:')
        ctxt.debug('  dstnode: %s', dstnode)
        ctxt.debug('  equivcls: %s', equivcls)
        ctxt.debug('  state: %s', state)

        ctxt.log('building error graph')
        with ctxt.indent():
            expgraph = ctxt.expgraph
            with Timer(ctxt, 'calculating shortest path through exploded graph'):
                dstexpnode = expgraph.get_expnode_with_state(dstnode, equivcls, state)
                if dstexpnode is None:
                    return None
                srcexpnode = expgraph.get_entry_node()

                return expgraph.get_shortest_path(srcexpnode, dstexpnode)

