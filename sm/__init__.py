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
from libcpychecker.absinterp import Location, get_locations

from libcpychecker.interval import *

from gccutils import DotPrettyPrinter, invoke_dot

import sm.parser

############################################################################
# Solver: what states are possible at each location?
############################################################################

def get_states_for_edge(srcloc, srcstates, dstloc, edge):
    class NewObj:
        def __repr__(self):
            return 'NewObj()'
        def __str__(self):
            return 'NewObj()'
    class DerefField:
        def __init__(self, ptr, fieldname):
            self.ptr = ptr
            self.fieldname = fieldname
        def __repr__(self):
            return 'DerefField(%r, %r)' % (self.ptr, self.fieldname)
        def __str__(self):
            return '%s->%s' % (self.ptr, self.fieldname)

    stmt = srcloc.get_stmt()
    print('  %s ' % stmt)

    print('srcstates: %s' % srcstates)
    dststates = set()
    for state in srcstates:
        print('    %s' % state)
        for t in state.transitions:
            print('      %s' % t)
            if t.condition.matched_by(stmt, edge):
                print 'got match'
                dststates.add(t.dst)
                if t.output:
                    gcc.error(srcloc.get_gcc_loc(), t.output)
            else:
                print 'not matched'
    if not(dststates):
        dststates = srcstates
    print('dststates: %s' % dststates)
    return dststates

class Solution:
    def __init__(self, fun, sm):
        # a mapping from Location to set(State)
        # i.e. a snapshot of what states we know are possible at each location
        # within the function
        self.fun = fun
        self.locations = get_locations(fun)
        self.loc_to_states = {loc:set() for loc in self.locations}

        # The initial state is the first block after entry (which has no statements):
        initbb = fun.cfg.entry.succs[0].dest
        initloc = Location(initbb, 0)
        self.loc_to_states[initloc] = set([sm.states[0]]) # initial state

    def __eq__(self, other):
        if not isinstance(other, Solution):
            return False
        return self.loc_to_states == other.loc_to_states

    def as_html_tr(self, out, stage, oldsol):
        out.write('<tr>')
        out.write('<td>%s</td>' % stage)
        for loc in self.locations:
            if oldsol:
                oldstates = oldsol.loc_to_states[loc]
            else:
                oldstates = None
            states = self.loc_to_states[loc]
            if not (states == oldstates):
                out.write('<td><b><pre>%s</pre></b></td>' % self.states_as_html(states))
            else:
                out.write('<td><pre>%s</pre></td>' % self.states_as_html(states))
        out.write('</tr>\n')

    def states_as_html(self, states):
        return str(states)

class HtmlLog:
    def __init__(self, out, solver):
        self.out = out
        out.write('<table border="1">\n')

        # Write headings:
        out.write('<tr>')
        out.write('<td>Stage</td>')
        for loc in solver.locations:
            out.write('<th>block %i stmt:%i</th>'
                      % (loc.bb.index, loc.idx))
        out.write('</tr>\n')
        out.write('<tr>')
        out.write('<td>Stage</td>')
        for loc in solver.locations:
            out.write('<th>%r</th>' % loc.get_stmt())
        out.write('</tr>\n')
        out.write('<tr>')
        out.write('<td>Stage</td>')
        for loc in solver.locations:
            out.write('<th>%s</th>' % loc.get_stmt())
        out.write('</tr>\n')

class Solver:
    def __init__(self, fun, sm):
        self.fun = fun
        self.sm = sm
        self.locations = get_locations(fun)
        self.solutions = []

    def solve(self):
        # calculate least fixed point
        with open('states-%s.html' % self.fun.decl.name, 'w') as out:
            html = HtmlLog(out, self)
            while True:
                idx = len(self.solutions)
                if self.solutions:
                    oldsol = self.solutions[-1]
                else:
                    oldsol = None
                newsol = Solution(self.fun, self.sm)
                if oldsol:
                    # FIXME: optimize using a worklist:
                    for loc in self.locations:
                        newval = oldsol.loc_to_states[loc]
                        print('newval: %r' % newval)
                        for prevloc, edge in loc.prev_locs():
                            print('  edge from: %s' % prevloc)
                            print('         to: %s' % loc)
                            value = get_states_for_edge(prevloc,
                                                        oldsol.loc_to_states[prevloc],
                                                        loc, edge)
                            print(' str(value): %s' % value)
                            print('repr(value): %r' % value)
                            newval = newval.union(value)
                            print('  new value: %s' % newval)

                        newsol.loc_to_states[loc] = newval
                        # TODO: update based on transfer functions
                self.solutions.append(newsol)
                print(newsol.loc_to_states)
                newsol.as_html_tr(out, idx, oldsol)
                if oldsol == newsol:
                    # We've reached a fixed point
                        break

                if len(self.solutions) > 20:
                    # bail out: termination isn't working for some reason
                    raise BailOut()


class ExplodedGraphPrettyPrinter(DotPrettyPrinter):
    def __init__(self, expgraph, name):
        self.expgraph = expgraph
        self.name = name

    def to_dot(self):
        if hasattr(self, 'name'):
            name = self.name
        else:
            name = 'G'
        result = 'digraph %s {\n' % name
        for expnode in self.expgraph.iter_nodes():
            result += ('  %s [label=<%s>];\n'
                       % (self.expnode_to_id(expnode),
                          self.expnode_to_dot_label(expnode)))

        for expedge in self.expgraph.edges:
            result += self.expedge_to_dot(expedge)
        result += '}\n'
        return result

    def expnode_to_id(self, expnode):
        return '%s' % id(expnode)

    def expnode_to_dot_label(self, expnode):
        result = '<font face="monospace"><table cellborder="0" border="0" cellspacing="0">\n'
        result += ('<tr> <td>%s</td> <td>%s</td> </tr>\n'
                   % (self.to_html(str(expnode.node)), expnode.state))
        from gccutils import get_src_for_loc
        stmt = expnode.node.get_stmt()
        loc = expnode.node.get_gcc_loc()
        if loc:
            code = get_src_for_loc(loc).rstrip()
            pseudohtml = self.to_html(code)
            result += ('<tr><td align="left">'
                       + self.to_html('%4i ' % stmt.loc.line)
                       + pseudohtml
                       + '<br/>'
                       + (' ' * (5 + stmt.loc.column-1)) + '^'
                       + '</td></tr>')
        #result += '<tr><td></td>' + to_html(stmt, stmtidx) + '</tr>\n'
        result += '</table></font>\n'
        return result

    def expedge_to_dot(self, expedge):
        if expedge.srcexpnode.state != expedge.dstexpnode.state:
            label = self.to_html('%s -> %s' % (expedge.srcexpnode.state.name, expedge.dstexpnode.state.name))
        else:
            label = ''
        return ('    %s -> %s [label=<%s>];\n'
                % (self.expnode_to_id(expedge.srcexpnode),
                   self.expnode_to_id(expedge.dstexpnode),
                   label))

class ExplodedGraph:
    """Like a CFG, but with (node, state) pairs"""
    def __init__(self):
        # Mapping from (node, state) to ExplodedNode:
        self.nodedict = {}
        self.edges = set()

    def lazily_add_node(self, node, state):
        key = (node, state)
        if key not in self.nodedict:
            self.nodedict[key] = ExplodedNode(node, state)
        return self.nodedict[key]

    def lazily_add_edge(self, srcnode, dstnode):
        self.edges.add(ExplodedEdge(srcnode, dstnode))

    def iter_nodes(self):
        for key in self.nodedict:
            yield self.nodedict[key]

    def to_dot(self):
        pp = ExplodedGraphPrettyPrinter(self, 'foo')
        return pp.to_dot()

class ExplodedNode:
    def __init__(self, node, state):
        self.node = node
        self.state = state

class ExplodedEdge:
    def __init__(self, srcexpnode, dstexpnode):
        self.srcexpnode = srcexpnode
        self.dstexpnode = dstexpnode


def make_exploded_graph(fun, ctxt):
    locations = get_locations(fun) # these will be our nodes

    # The initial state is the first block after entry (which has no statements):
    initbb = fun.cfg.entry.succs[0].dest
    initloc = Location(initbb, 0)
    expgraph = ExplodedGraph()
    expnode = expgraph.lazily_add_node(initloc, ctxt.statenames[0]) # initial state
    worklist = [expnode]
    while worklist:
        def lazily_add_node(loc, state):
            if (loc, state) not in expgraph.nodedict:
                expnode = expgraph.lazily_add_node(loc, state)
                worklist.append(expnode)
            else:
                # (won't do anything)
                expnode = expgraph.lazily_add_node(loc, state)
            return expnode
        srcexpnode = worklist.pop()
        srcloc = srcexpnode.node
        stmt = srcloc.get_stmt()
        for dstloc, edge in srcloc.next_locs():
            if 0:
                print('  edge from: %s' % srcloc)
                print('         to: %s' % dstloc)
            srcstate = srcexpnode.state
            matches = []
            for sc in ctxt.sm.stateclauses:
                if srcstate in sc.statelist:
                    for pr in sc.patternrulelist:
                        # print('%r: %r' %(srcstate, pr))
                        if pr.pattern.matched_by(stmt, edge, ctxt):
                            assert len(pr.outcomes) > 0
                            for outcome in pr.outcomes:
                                # print 'outcome: %r' % outcome
                                def handle_outcome(outcome):
                                    # print('handle_outcome(%r)' % outcome)
                                    if isinstance(outcome, sm.parser.BooleanOutcome):
                                        if 0:
                                            print(edge.true_value)
                                            print(edge.false_value)
                                            print(outcome.guard)
                                        if edge.true_value and outcome.guard:
                                            handle_outcome(outcome.outcome)
                                        if edge.false_value and not outcome.guard:
                                            handle_outcome(outcome.outcome)
                                    elif isinstance(outcome, sm.parser.TransitionTo):
                                        # print('transition to %s' % outcome.state)
                                        dststate = outcome.state
                                        dstexpnode = lazily_add_node(dstloc, dststate)
                                        expedge = expgraph.lazily_add_edge(srcexpnode, dstexpnode)
                                    elif isinstance(outcome, sm.parser.PythonOutcome):
                                        ctxt.srcloc = srcloc
                                        outcome.run(ctxt)
                                    else:
                                        print(outcome)
                                        raise UnknownOutcome(outcome)
                                handle_outcome(outcome)
                            matches.append(pr)
            if not matches:
                dstexpnode = lazily_add_node(dstloc, srcstate)
                expedge = expgraph.lazily_add_edge(srcexpnode, dstexpnode)
    return expgraph

def solve(fun, ctxt):
    if 0:
        solver = Solver(fun, ctxt)
        solver.solve()

    if 1:
        expgraph = make_exploded_graph(fun, ctxt)
        if 0:
            # Debug: view the exploded graph:
            dot = expgraph.to_dot()
            # print(dot)
            invoke_dot(dot, fun.decl.name)

class Context:
    # An sm.parser.Sm in contect, with a mapping from its vars to gcc.VarDecl
    # (or ParmDecl) instances
    def __init__(self, sm, var):
        assert isinstance(var, (gcc.VarDecl, gcc.ParmDecl))
        self.sm = sm
        self.var = var
        self.statenames = list(sm.iter_states())

    def __repr__(self):
        return 'Context(%r)' % (self.statenames, )

    def compare(self, gccexpr, smexpr):
        if gccexpr == self.var:
            # print '%r' % self.sm.varclauses.name
            if smexpr == self.sm.varclauses.name:
                return True

        if isinstance(gccexpr, gcc.IntegerCst) and isinstance(smexpr, (int, long)):
            if gccexpr.constant == smexpr:
                return True

        return False
        print('compare:')
        print('  gccexpr: %r' % gccexpr)
        print('  smexpr: %r' % smexpr)
        raise UnhandledComparison()

class SmPass(gcc.GimplePass):
    def __init__(self, checkers):
        gcc.GimplePass.__init__(self, 'sm-pass-gimple')
        self.checkers = checkers

    def execute(self, fun):
        if 0:
            print(fun)
            print(self.checkers)

        if 0:
            # Dump location information
            for loc in get_locations(fun):
                print(loc)
                for prevloc in loc.prev_locs():
                    print('  prev: %s' % prevloc)
                for nextloc in loc.next_locs():
                    print('  next: %s' % nextloc)

        #print('locals: %s' % fun.local_decls)
        #print('args: %s' % fun.decl.arguments)
        for checker in self.checkers:
            for sm in checker.sms:
                vars_ = fun.local_decls + fun.decl.arguments
                if 0:
                    print('vars_: %s' % vars_)

                for var in vars_:
                    if 0:
                        print(var)
                        print(var.type)
                    if isinstance(var.type, gcc.PointerType):
                        # got pointer type
                        ctxt = Context(sm, var)
                        #print('ctxt: %r' % ctxt)
                        solve(fun, ctxt)

def main(checkers):
    gimple_ps = SmPass(checkers)
    if 1:
        # non-SSA version:
        gimple_ps.register_before('*warn_function_return')
    else:
        # SSA version:
        gimple_ps.register_after('ssa')
