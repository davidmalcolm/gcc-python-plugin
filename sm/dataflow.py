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

class AbstractValue:
    """
    Roughly speaking, an AbstractValue instance is an item of dataflow
    information at a given node; the class knows the initial value for
    entry nodes, how to compute the effect of an edge on a value (flow
    function), and how to merge together the information for multiple
    in-edges at a node.  The solver can then use this to analyze a graph,
    obtaining an instance per-node.

    More formally, an AbstractValue should be a meet-semilattice with no
    infinitely-descending chains.

    Translating the jargon somewhat: a "meet-semilattice" is a
    partially-ordered set in which every non-empty finite subset has a
    greatest lower bound (or "meet") within the set.  Informally, we have
    a set of descriptions of the program state at a particular node, and
    we can use "meet" on them when control-flow merges to obtain the best
    description of the intersection of said information: any value which is
    lower than all of the in-values is a coarser description of the program
    state than any of them, giving some description of the possible
    resulting state.  By picking the *greatest* such lower bound, meet() is
    picking the finest approximation to program state that's still safe.

    The infinitely-descending chains rule informally means that repeated
    calls to meet() should always eventually reach some fixed point after
    a finite number of steps, so that the analysis is guaranteed to
    terminate.  It also implies that there is a bottom element, less than
    all other values.

    For more information, see e.g. chapter 3 of
       "Data Flow Analysis: Theory and Practice" (2009)
       Uday Khedker, Amitabha Sanyal, Bageshri Karkare
    """
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
        assert result[node] is not None
        worklist.append(node)
        workset.add(node)

    numiters = 0
    while worklist:
        node = worklist.pop()
        workset.remove(node)
        numiters += 1
        if ctxt.options.enable_timing:
            if numiters % 1000 == 0:
                ctxt.timing('iter %i: len(worklist): %i  analyzing node: %s',
                            numiters, len(worklist), node)
        else:
            ctxt.log('iter %i: len(worklist): %i  analyzing node: %s',
                     numiters, len(worklist), node)
        with ctxt.indent():
            # Set the location so that if an unhandled
            # exception occurs, it should at least identify the
            # code that triggered it:
            stmt = node.stmt
            if stmt:
                if stmt.loc:
                    gcc.set_location(stmt.loc)

            srcvalue = result[node]
            ctxt.log('srcvalue: %s', srcvalue)
            assert srcvalue is not None

            for edge in node.succs:
                ctxt.log('analyzing out-edge: %s', edge)

                dstnode = edge.dstnode
                oldvalue = result[dstnode]

                # Get value along outedge:
                edgevalue, details = cls.get_edge_value(ctxt, srcvalue, edge)
                ctxt.log('  edge value: %s', edgevalue)
                ctxt.log('  oldvalue: %s', oldvalue)

                newvalue = cls.meet(ctxt, oldvalue, edgevalue)

                ctxt.log('  newvalue: %s', newvalue)

                if newvalue != oldvalue:
                    # strictly speaking, newvalue must be < oldvalue, but we
                    # rely on the AbstractValue to correctly implement that
                    ctxt.log('  value changed from: %s  to %s',
                             oldvalue,
                             newvalue)
                    assert newvalue is not None
                    result[dstnode] = newvalue
                    if dstnode not in workset:
                        worklist.append(dstnode)
                        workset.add(dstnode)

    ctxt.timing('took %i iterations to reach fixed point', numiters)
    return result

