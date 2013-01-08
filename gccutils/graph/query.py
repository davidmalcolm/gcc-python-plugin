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

# Queries on graphs, with composable filters
#   Query(graph).filters

import gcc

from gccutils.graph.supergraph import ReturnNode

__all__ = ['Query']

class BaseQuery:
    def first(self):
        results = list(self)
        if len(results) < 1:
            raise ValueError('no nodes found satisfying: %s' % self)
        return results[0]

    def one(self):
        results = list(self)
        if len(results) > 1:
            raise ValueError('more than one node found satisfying: %s' % self)
        if len(results) < 1:
            raise ValueError('no nodes found satisfying: %s' % self)
        return results[0]

    #######################################################################
    # Filters
    #######################################################################

    def get_calls_of(self, funcname):
        class GetCallsOf(CompoundQuery):
            def __init__(self, innerquery, funcname):
                CompoundQuery.__init__(self, innerquery)
                self.funcname = funcname
            def __iter__(self):
                for node in self.innerquery:
                    # For an interprocedural call, we want the CallNode, not the
                    # ReturnNode.
                    # For a call to an external function, the GimpleCall will be
                    # within a regular SupergraphNode:
                    if not isinstance(node, ReturnNode):
                        stmt = node.stmt
                        if isinstance(stmt, gcc.GimpleCall):
                            if isinstance(stmt.fn, gcc.AddrExpr):
                                if isinstance(stmt.fn.operand, gcc.FunctionDecl):
                                    if stmt.fn.operand.name == funcname:
                                        yield node
            def __repr__(self):
                return ('GetCallsOf(%r, funcname=%r)'
                        % (self.innerquery, self.funcname))
            def __str__(self):
                return '%s that are calls of %s()' % (self.innerquery, self.funcname)

        return GetCallsOf(self, funcname)

    def assigning_to(self, varname):
        class AssigningTo(CompoundQuery):
            def __init__(self, innerquery, varname):
                CompoundQuery.__init__(self, innerquery)
                self.varname = varname
            def __iter__(self):
                for node in self.innerquery:
                    stmt = node.stmt
                    if stmt.lhs.var.name == self.varname:
                        yield node
            def __repr__(self):
                return ('AssigningTo(%r, varname=%r)'
                        % (self.innerquery, self.varname))
            def __str__(self):
                return '%s in which the LHS is assigned to a variable named %s' % (self.innerquery, self.varname)
        return AssigningTo(self, varname)

    def within(self, funcname):
        class Within(CompoundQuery):
            def __init__(self, innerquery, funcname):
                CompoundQuery.__init__(self, innerquery)
                self.funcname = funcname
            def __iter__(self):
                for node in self.innerquery:
                    if node.function:
                        if node.function.decl.name == self.funcname:
                            yield node
            def __repr__(self):
                return ('Within(%r, funcname=%r)'
                        % (self.innerquery, self.funcname))
            def __str__(self):
                return '%s within %s' % (self.innerquery, self.funcname)
        return Within(self, funcname)

class CompoundQuery(BaseQuery):
    def __init__(self, innerquery):
        self.innerquery = innerquery

class Query(BaseQuery):
    def __init__(self, graph):
        self.graph = graph

    def __iter__(self):
        for node in self.graph.nodes:
            yield node

    def __repr__(self):
        return 'Query()'

    def __str__(self):
        return 'nodes'

