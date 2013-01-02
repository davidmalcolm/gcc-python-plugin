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

# Dataflow solver: finds the maximum fixed point (MFP) of a set of dataflow
# equations on a graph.

import gcc

from sm.solver import ENABLE_TIMING

class AbstractValue:
    @classmethod
    def make_entry_point(cls, ctxt, node):
        raise NotImplementedError

    @classmethod
    def get_edge_value(cls, ctxt, srcvalue, edge):
        """
        Generate a (dstvalue, details) pair, where "details" can be of an
        arbitrary type (per AbstractValue) and could be None
        """
        raise NotImplementedError

    @classmethod
    def meet(cls, ctxt, lhs, rhs):
        raise NotImplementedError

def fixed_point_solver(ctxt, graph, cls):
    # Given an AbstractValue subclass "cls", find the fixed point,
    # generating a dict from Node to cls instance
    # Use "None" as the bottom element: unreachable
    # otherwise, a cls instance
    result = {}
    for node in graph.nodes:
        result[node] = None

    # FIXME: make this a priority queue, in the node's topological order?

    # Set up worklist:
    workset = set()
    worklist = []
    for node in graph.get_entry_nodes():
        result[node] = cls.make_entry_point(ctxt, node)
        for edge in node.succs:
            worklist.append(edge.dstnode)
            workset.add(edge.dstnode)

    numiters = 0
    while worklist:
        node = worklist.pop()
        workset.remove(node)
        numiters += 1
        if ENABLE_TIMING:
            if numiters % 1000 == 0:
                ctxt.timing('iter %i: len(worklist): %i  analyzing node: %s',
                            numiters, len(worklist), node)
        else:
            ctxt.log('iter %i: len(worklist): %i  analyzing node: %s',
                     numiters, len(worklist), node)
        with ctxt.indent():
            oldvalue = result[node]
            ctxt.log('old value: %s', oldvalue)
            newvalue = None
            for edge in node.preds:
                ctxt.log('analyzing in-edge: %s', edge)
                with ctxt.indent():
                    srcvalue = result[edge.srcnode]
                    ctxt.log('srcvalue: %s', srcvalue)
                    if srcvalue is not None:

                        # Set the location so that if an unhandled
                        # exception occurs, it should at least identify the
                        # code that triggered it:
                        stmt = edge.srcnode.stmt
                        if stmt:
                            if stmt.loc:
                                gcc.set_location(stmt.loc)

                        edgevalue, details = cls.get_edge_value(ctxt, srcvalue, edge)
                        ctxt.log('  edge value: %s', edgevalue)
                        newvalue = cls.meet(ctxt, newvalue, edgevalue)
                        ctxt.log('  new value: %s', newvalue)
            if newvalue != oldvalue:
                ctxt.log('  value changed from: %s  to %s',
                         oldvalue,
                         newvalue)
                result[node] = newvalue
                for edge in node.succs:
                    dstnode = edge.dstnode
                    if dstnode not in workset:
                        worklist.append(dstnode)
                        workset.add(dstnode)

    ctxt.timing('took %i iterations to reach fixed point', numiters)
    return result

