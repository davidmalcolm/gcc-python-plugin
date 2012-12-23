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

from gccutils.graph import Graph, Node, Edge, Subgraph
from gccutils.graph.supergraph import Supergraph, CallToStart, \
    ExitToReturnSite, CallNode

############################################################################
# Enhancement to a Supergraph to approximate the Interprocedural Valid Paths
# (IVP), in which each node is extended to contain a callstring suffix
# (i.e. the top N callnodes on the stack), thus modelling call/return
# behavior.
# Analogous to inlining
############################################################################

class Callstring:
    """
    A callstring-suffix
    """
    __slots__ = ('callnodes', )

    def __init__(self, callnodes):
        self.callnodes = callnodes

    def __str__(self):
        def callnode_to_str(callnode):
            #return str(callnode)
            return '%s:%s' % (callnode.function.decl.name, callnode.stmt.loc.line)
        return '[%s]' % ' <| '.join(callnode_to_str(callnode)
                                    for callnode in self.callnodes)

    def __repr__(self):
        return 'Callstring(%r)' % str(self)

    def __eq__(self, other):
        return self.callnodes == other.callnodes

    def __hash__(self):
        return hash(self.callnodes)

    def to_dot_id(self):
        return '_'.join([str(id(callnode))
                         for callnode in self.callnodes])

class IvpGraph(Graph):
    __slots__ = ('sg', 'maxlength', 'ivpnodes', '_entrynodes')

    def __init__(self, sg, maxlength):
        Graph.__init__(self)
        self.sg = sg
        self.maxlength = maxlength

        # Dict mapping from (callstring, supernode) to IvpNode
        self.ivpnodes = {}

        self._entrynodes = set()

        # 1st pass: walk from the entrypoints, calling functions,
        # building nodes, and calling edges.
        # We will fill in the return edges later:
        # set of (ivpnode, inneredge) pairs deferred for later processsing:
        _pending_return_edges = set()

        def _add_node_for_key(key):
            callstring, supernode = key
            newnode = IvpNode(callstring, supernode)
            self.add_node(newnode)
            self.ivpnodes[key] = newnode
            return newnode

        # The "worklist" is a set of IvpNodes that we need to add
        # edges for.  Doing so may lead to more IvpNodes being
        # created.
        worklist = set()
        for supernode in sg.get_entry_nodes():
            key = (Callstring(tuple()), supernode)
            node = _add_node_for_key(key)
            worklist.add(node)
            self._entrynodes.add(node)

        while worklist:
            ivpnode = worklist.pop()
            if 0:
                print('ivpnode: %s' % ivpnode)
                print('ivpnode: %r' % ivpnode)

            for inneredge in ivpnode.innernode.succs:
                if 0:
                    print('  inneredge: %s' % inneredge)
                    print('  inneredge: %r' % inneredge)
                callstring = ivpnode.callstring

                def get_callstring():
                    if isinstance(inneredge, CallToStart):
                        # interprocedural call: push onto stack:
                        callnode = inneredge.srcnode
                        assert len(callstring.callnodes) <= maxlength
                        if len(callstring.callnodes) == maxlength:
                            # Truncate, losing the bottom of the stack:
                            oldstack = list(callstring.callnodes[1:])
                        else:
                            oldstack = list(callstring.callnodes)
                        return Callstring(tuple(oldstack + [callnode]))

                    elif isinstance(inneredge, ExitToReturnSite):
                        # interprocedural return: pop from stack
                        if not callstring.callnodes:
                            return None

                        # Ensure that we're returning to the correct place
                        # according to the top of the stack:
                        callnode = callstring.callnodes[-1]
                        if inneredge.dstnode == callnode.returnnode:
                            # add to the pending list
                            _pending_return_edges.add( (ivpnode, inneredge) )

                        return None
                    else:
                        # same stack depth:
                        return ivpnode.callstring

                newcallstring = get_callstring()
                if newcallstring:
                    key = (newcallstring, inneredge.dstnode)
                    if key not in self.ivpnodes:
                        dstnode = _add_node_for_key(key)
                        worklist.add( dstnode )
                    else:
                        dstnode = self.ivpnodes[key]
                    self.add_edge(ivpnode, dstnode, inneredge)

            # FIXME: in case we don't terminate, this is useful for debugging why:
            #if len(self.nodes) > 100:
            #    return

        # 2nd pass: now gather all valid callstrings:
        self.all_callstrings = set()
        for node in self.nodes:
            self.all_callstrings.add(node.callstring)

        if 0:
            print('self.all_callstrings: %s' % self.all_callstrings)

        # 3rd pass: go back and add the return edges (using the set of valid
        # callstrings to expand possible-truncated stacks):
        for srcivpnode, inneredge in _pending_return_edges:
            callstring = srcivpnode.callstring

            # We have a return edge, valid in the sense
            # that the dstnode is the call at the top of the stack
            #
            # What state should the stack end up in?
            def iter_valid_pops(callstring):
                # We could be at the top of an untruncated stack, in which
                # case we simply lose the top element:
                candidate = Callstring(callstring.callnodes[:-1])
                if candidate in self.all_callstrings:
                    yield candidate

                # Alternatively, the stack could be truncated, in which
                # case we need to generate all possible new elements for the
                # prefix part of the truncated stack
                if len(callstring.callnodes) == maxlength:
                    suffix = callstring.callnodes[0:-1]
                    for candidate in self.all_callstrings:
                        if candidate.callnodes[1:] == suffix:
                            yield candidate

            valid_pops = set(iter_valid_pops(callstring))
            for newcallstring in valid_pops:
                key = (newcallstring, inneredge.dstnode)
                dstivpnode = self.ivpnodes[key]
                self.add_edge(srcivpnode, dstivpnode, inneredge)

        # (done)

    def _make_edge(self, srcnode, dstnode, edge):
        return IvpEdge(srcnode, dstnode, edge)

    def get_functions(self):
        for fun in self.sg.get_functions():
            yield fun

    def get_entry_nodes(self):
        for node in self._entrynodes:
            yield node

class IvpNode(Node):
    """
    A node in the supergraph, wrapping a StmtNode
    """
    def __init__(self, callstring, innernode):
        Node.__init__(self)
        self.callstring = callstring
        self.innernode = innernode

    def to_dot_html(self, ctxt):
        from gccutils.dot import Table, Tr, Td, Text, Br, Font

        table = Table()
        tr = table.add_child(Tr())
        td = tr.add_child(Td(align='left'))
        td.add_child(Text('%s' % (self.callstring))) #.to_dot_id())))
        tr = table.add_child(Tr())
        td = tr.add_child(Td(align='left'))
        td.add_child(self.innernode.to_dot_html(ctxt))

        return table

    def __str__(self):
        return '%s: %s' % (self.callstring, self.innernode)

    def __repr__(self):
        return 'IvpNode(%r, %r)' % (self.callstring, self.innernode)

    @property
    def supergraphnode(self):
        return self.innernode

    @property
    def stmt(self):
        return self.innernode.stmt

    @property
    def function(self):
        return self.innernode.function

    def get_gcc_loc(self):
        return self.innernode.get_gcc_loc()

    def get_subgraph_path(self, ctxt):
        innerpath = self.innernode.get_subgraph_path(ctxt)
        if innerpath:
            sg_file, sg_func = innerpath
            return (sg_file,
                    Subgraph('callstring_%s_function_%s'
                             % (self.callstring, self.function),
                             '%s : %s()' % (self.callstring,
                                            self.function.decl.name)))
        return ()

class IvpEdge(Edge):
    """
    An edge in the supergraph, wrapping a StmtEdge,
    or None for the intraprocedual edges for function call/return
    """
    def __init__(self, srcnode, dstnode, inneredge):
        Edge.__init__(self, srcnode, dstnode)
        self.inneredge = inneredge

    def to_dot_label(self, ctxt):
        return self.inneredge.to_dot_label(ctxt)

    def to_dot_attrs(self, ctxt):
        return self.inneredge.to_dot_attrs(ctxt)

    @property
    def true_value(self):
        return self.inneredge.true_value

    @property
    def false_value(self):
        return self.inneredge.false_value

    @property
    def stmtedge(self):
        return self.inneredge.stmtedge
