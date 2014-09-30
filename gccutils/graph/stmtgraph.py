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

import gcc

from gccutils.graph import Graph, Node, Edge

############################################################################
# A CFG, but with individual statements for nodes, rather than lumping them
# together within basic blocks
# It also has "empty" nodes i.e. those with no statements, to handle
# the empty BBs in the original CFG (entry and exit)
############################################################################
class StmtGraph(Graph):
    __slots__ = ('fun',
                 'entry', 'exit',
                 'entry_of_bb',
                 'exit_of_bb',
                 'node_for_stmt',
                 '__lastnode',
                 'supernode_for_stmtnode')

    def __init__(self, fun, split_phi_nodes, omit_complex_edges=False):
        """
        fun : the underlying gcc.Function

        split_phi_nodes:

           if true, split phi nodes so that there is one copy of each phi
           node per edge as a SplitPhiNode instance, allowing client code
           to walk the StmtGraph without having to track which edge we came
           from

           if false, create a StmtNode per phi node at the top of the BB

        """
        Graph.__init__(self)
        self.fun = fun
        self.entry = None
        self.exit = None
        # Mappings from gcc.BasicBlock to StmtNode so that we can wire up
        # the edges for the gcc.Edge:
        self.entry_of_bb = {}
        self.exit_of_bb = {}
        self.node_for_stmt = {}

        basic_blocks = fun.cfg.basic_blocks

        # 1st pass: create nodes and edges within BBs:
        for bb in basic_blocks:
            self.__lastnode = None

            def add_stmt(stmt):
                nextnode = self.add_node(StmtNode(fun, bb, stmt))
                self.node_for_stmt[stmt] = nextnode
                if self.__lastnode:
                    self.add_edge(self.__lastnode, nextnode, None)
                else:
                    self.entry_of_bb[bb] = nextnode
                self.__lastnode = nextnode

            if bb.phi_nodes and not split_phi_nodes:
                # If we're not splitting the phi nodes, add them to the top
                # of each BB:
                for stmt in bb.phi_nodes:
                    add_stmt(stmt)
                self.exit_of_bb[bb] = self.__lastnode
            if bb.gimple:
                for stmt in bb.gimple:
                    add_stmt(stmt)
                self.exit_of_bb[bb] = self.__lastnode

            if self.__lastnode is None:
                # We have a BB with neither statements nor phis
                # Create a single node for this BB:
                if bb == fun.cfg.entry:
                    cls = EntryNode
                elif bb == fun.cfg.exit:
                    cls = ExitNode
                else:
                    # gcc appears to create empty BBs for functions
                    # returning void that contain multiple "return;"
                    # statements:
                    cls = StmtNode
                node = self.add_node(cls(fun, bb, None))
                self.entry_of_bb[bb] = node
                self.exit_of_bb[bb] = node
                if bb == fun.cfg.entry:
                    self.entry = node
                elif bb == fun.cfg.exit:
                    self.exit = node

            assert self.entry_of_bb[bb] is not None
            assert self.exit_of_bb[bb] is not None

        # 2nd pass: wire up the cross-BB edges:
        for bb in basic_blocks:
            for edge in bb.succs:

                # If requested, omit "complex" edges e.g. due to
                # exception-handling:
                if omit_complex_edges:
                    if edge.complex:
                        continue

                last_node = self.exit_of_bb[bb]
                if split_phi_nodes:
                    # add SplitPhiNode instances at the end of each edge
                    # as a copy of each phi node, specialized for this edge
                    if edge.dest.phi_nodes:
                        for stmt in edge.dest.phi_nodes:
                            split_phi = self.add_node(SplitPhiNode(fun, stmt, edge))
                            self.add_edge(last_node,
                                          split_phi,
                                          edge)
                            last_node = split_phi

                # After optimization, the CFG sometimes contains edges that
                # point to blocks that are no longer within fun.cfg.basic_blocks
                # Skip them:
                if edge.dest not in basic_blocks:
                    continue

                self.add_edge(last_node,
                              self.entry_of_bb[edge.dest],
                              edge)

        # 3rd pass: set up caselabelexprs for edges within switch statements
        # There doesn't seem to be any direct association between edges in a
        # CFG and the switch labels; store this information so that it's
        # trivial to go from an edge to the set of case labels that might be
        # being followed:
        for stmt in self.node_for_stmt:
            if isinstance(stmt, gcc.GimpleSwitch):
                labels = stmt.labels
                node = self.node_for_stmt[stmt]
                for edge in node.succs:
                    caselabelexprs = set()
                    for label in labels:
                        dststmtnode_of_labeldecl = self.get_node_for_labeldecl(label.target)
                        if dststmtnode_of_labeldecl == edge.dstnode:
                            caselabelexprs.add(label)
                    edge.caselabelexprs = frozenset(caselabelexprs)

    def _make_edge(self, srcnode, dstnode, edge):
        return StmtEdge(srcnode, dstnode, edge, len(self.edges))

    def get_entry_nodes(self):
        return [self.entry]

    def get_node_for_labeldecl(self, labeldecl):
        assert isinstance(labeldecl, gcc.LabelDecl)
        bb = self.fun.cfg.get_block_for_label(labeldecl)
        return self.entry_of_bb[bb]

class StmtNode(Node):
    __slots__ = ('fun', 'bb', 'stmt')

    def __init__(self, fun, bb, stmt):
        Node.__init__(self)
        self.fun = fun
        self.bb = bb
        self.stmt = stmt # can be None for empty BBs

    def __str__(self):
        return str(self.stmt)

    def __repr__(self):
        return 'StmtNode(%r)' % self.stmt

    def __hash__(self):
        return hash(self.stmt)

    def get_stmt(self):
        return self.stmt

    def get_gcc_loc(self):
        if self.stmt:
            return self.stmt.loc
        else:
            return None

    def to_dot_html(self, ctxt):
        from gccutils.dot import Table, Tr, Td, Text, Br, Font
        from gccutils import get_src_for_loc

        loc = self.get_gcc_loc()
        if loc:
            table = Table()
            code = get_src_for_loc(loc).rstrip()
            tr = table.add_child(Tr())
            td = tr.add_child(Td(align='left'))
            td.add_child(Text('%4i %s' % (self.stmt.loc.line, code)))
            td.add_child(Br())
            td.add_child(Text(' ' * (5 + self.stmt.loc.column-1) + '^'))
            td.add_child(Br())
            td.add_child(Text(str(self)))
            return table
            # return Font([table], face="monospace")
        else:
            return Text(str(self))

    def __eq__(self, other):
        return self.stmt == other.stmt

class EntryNode(StmtNode):
    __slots__ = ()

    def to_dot_html(self, ctxt):
        from gccutils.dot import Table, Tr, Td, Text

        funtype = self.fun.decl.type
        args = ','.join(['%s %s' % (arg.type, arg.name)
                         for arg in self.fun.decl.arguments])
        signature = '%s %s(%s)' % (funtype.type, self.fun.decl.name, args)

        table = Table([
            Tr([
                Td([
                    Text('ENTRY %s' % signature)
                    ])
                ])
            ])
        for var in self.fun.local_decls:
            table.add_child(Tr([
                        Td([
                                Text('%s %s;' % (var.type, var))
                                ])
                        ]))
        return table

    def __str__(self):
        return 'ENTRY %s' % self.fun.decl.name

    def __repr__(self):
        return 'EntryNode(%r)' % self.fun.decl.name

class ExitNode(StmtNode):
    __slots__ = ()

    def __str__(self):
        return 'EXIT %s' % self.fun.decl.name

    def __repr__(self):
        return 'ExitNode(%r)' % self.fun.decl.name

    @property
    def returnnode(self):
        """
        Get the gcc.GimpleReturn statement associated with this function exit
        """
        if len(self.preds) == 1:
            node = list(self.preds)[0].srcnode
            assert isinstance(node.stmt, gcc.GimpleReturn)
            return node

    @property
    def returnval(self):
        """
        Get the gcc.Tree for the return value, or None
        """
        returnnode = self.returnnode
        if returnnode:
            assert isinstance(returnnode.stmt, gcc.GimpleReturn)
            return returnnode.stmt.retval

class SplitPhiNode(StmtNode):
    __slots__ = ('inneredge', 'rhs')

    def __init__(self, fun, stmt, inneredge):
        StmtNode.__init__(self, fun, None, stmt)
        self.inneredge = inneredge

        # Lookup the RHS for this edge:
        assert isinstance(stmt, gcc.GimplePhi)
        assert isinstance(inneredge, gcc.Edge)
        self.rhs = None
        for arg, edge in stmt.args:
            if edge == inneredge:
                self.rhs = arg
                break
        if self.rhs is None:
            raise UnknownEdge()

    def __str__(self):
        return '%s = %s (via %s)' % (self.stmt.lhs, self.rhs, self.stmt)

    def __repr__(self):
        return 'SplitPhiNode(%r, %r)' % (self.stmt, self.inneredge)

    def __eq__(self, other):
        return isinstance(other, SplitPhiNode) and self.inneredge == other.inneredge

class StmtEdge(Edge):
    __slots__ = ('cfgedge', 'sortidx', 'caselabelexprs')

    def __init__(self, srcnode, dstnode, cfgedge, sortidx):
        Edge.__init__(self, srcnode, dstnode)
        self.cfgedge = cfgedge # will be None within a BB
        self.sortidx = sortidx

        # For use in handling switch statements:
        # the set of gcc.CaseLabelExpr for this edge
        self.caselabelexprs = frozenset()


    def to_dot_label(self, ctx):
        return str(self.sortidx)
        if self.cfgedge:
            if self.cfgedge.true_value:
                return 'true'
            elif self.cfgedge.false_value:
                return 'false'

        # Edges within a switch statement:
        if self.caselabelexprs:
            def cle_to_str(cle):
                if cle.low is not None:
                    if cle.high is not None:
                        return '%s ... %s' % (cle.low, cle.high)
                    else:
                        return str(cle.low)
                else:
                    return 'default'
            return '{%s}' % ', '.join([cle_to_str(cle)
                                       for cle in self.caselabelexprs])

        return ''

    @property
    def true_value(self):
        if self.cfgedge:
            return self.cfgedge.true_value

    @property
    def false_value(self):
        if self.cfgedge:
            return self.cfgedge.false_value

    def __cmp__(self, other):
        return cmp(self.sortidx, other.sortidx)

