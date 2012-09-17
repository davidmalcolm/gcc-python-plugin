import gcc
from libcpychecker.absinterp import Location, get_locations

from libcpychecker.interval import *

from gccutils import DotPrettyPrinter, invoke_dot

############################################################################
# State machines
############################################################################

class SmPrettyPrinter(DotPrettyPrinter):
    def __init__(self, sm, name):
        self.sm = sm
        self.name = name

    def to_dot(self):
        if hasattr(self, 'name'):
            name = self.name
        else:
            name = 'G'
        result = 'digraph %s {\n' % name
        for state in self.sm.states:
            result += ('  %s [label=<%s>];\n'
                       % (state.name, self.state_to_dot_label(state)))

            for t in state.transitions:
                result += self.transition_to_dot(t)
        result += '}\n'
        return result

    def state_to_dot_label(self, state):
        return '%s' % state.name

    def transition_to_dot(self, t):
        if t.output:
            label = '%s : <i>%s</i>' % (t.condition, t.output)
        else:
            label = t.condition
        return ('    %s -> %s [label=<%s>];\n'
                % (t.src.name,
                   t.dst.name,
                   label))

class Sm:
    def __init__(self):
        self.states = []

    def add_state(self, name):
        s = State(name)
        self.states.append(s)
        return s

    def to_dot(self):
        pp = SmPrettyPrinter(self, 'foo')
        return pp.to_dot()

class State:
    def __init__(self, name):
        self.name = name
        self.transitions = []

    def __repr__(self):
        return 'State(%r)' % self.name

    def add_transition(self, condition, dst, output = None):
        t = Transition(self, condition, dst, output)
        self.transitions.append(t)
        return t

class Transition:
    def __init__(self, src, condition, dst, output):
        assert isinstance(src, State)
        assert isinstance(condition, StmtCondition)
        assert isinstance(dst, State)
        self.src = src
        self.condition = condition
        self.dst = dst
        self.output = output

    def __repr__(self):
        return 'Transition(%s, %s, %s, %s)' % (self.src, self.condition, self.dst, self.output)

class StmtCondition:
    def matched_by(self, stmt, edge):
        print(self)
        print(stmt)
        raise NotImplementedError()

# Various conditions:

class FunctionCall(StmtCondition):
    """
    Is this a call of the form:
        ... = FNNAME(...)
    """
    def __init__(self, fnname):
        self.fnname = fnname

    def __repr__(self):
        return 'FunctionCall(%r)' % self.fnname

    def __str__(self):
        return '%s(...)' % self.fnname

    def matched_by(self, stmt, edge):
        if isinstance(stmt, gcc.GimpleCall):
            if isinstance(stmt.fn, gcc.AddrExpr):
                if isinstance(stmt.fn.operand, gcc.FunctionDecl):
                    if stmt.fn.operand.name == self.fnname:
                        # We have a matching function name
                        return True

class ResultOfFunctionCall(FunctionCall):
    """
    Is this a call of the form:
        LHS = FNNAME(...)
    """
    def __init__(self, lhs, fnname):
        FunctionCall.__init__(self, fnname)
        self.lhs = lhs

    def __repr__(self):
        return 'ResultOfFunctionCall(%r, %r)' % (self.lhs, self.fnname)

    def __str__(self):
        return '%s = %s(...)' % (self.lhs, self.fnname)

    def matched_by(self, stmt, edge):
        if not FunctionCall.matched_by(self, stmt, edge):
            return False
        # FIXME: check the lhs
        return True


class FunctionCallWithArg(FunctionCall):
    """
    Is this a call of the form:
        ... = FNNAME(..., ARG_i, ...)
    (1-based indices)
    """
    def __init__(self, fnname, idx, arg):
        FunctionCall.__init__(self, fnname)
        self.idx = idx
        self.arg = arg

    def __repr__(self):
        return 'FunctionCallWithArg(%r, %i, %r)' % (self.lhs, self.idx, self.arg)

    def __str__(self):
        return '%s(..., %s, ...)' % (self.fnname, self.arg)

    def matched_by(self, stmt, edge):
        if not FunctionCall.matched_by(self, stmt, edge):
            return False
        if stmt.args[self.idx - 1] == self.arg:
            return True

class ConditionalHasValue(StmtCondition):
    def __init__(self, lhs, op, rhs, boolval):
        self.lhs = lhs
        self.op = op
        self.rhs = rhs
        self.boolval = boolval

    def __repr__(self):
        return 'ConditionalHasValue(%r, %r, %r, %r)' % (self.lhs, self.op, self.rhs, self.boolval)

    def __str__(self):
        return '(%s %s %s) is %s' % (self.lhs, self.op, self.rhs, self.boolval)

    def matched_by(self, stmt, edge):
        if isinstance(stmt, gcc.GimpleCond):
            if 0:
                print('    %r %r %r %r %r' % (stmt.lhs, stmt.rhs, stmt.exprcode, stmt.true_label, stmt.false_label))
                print('edge: %r' % edge)
                print('edge.true_value: %r' % edge.true_value)
                print('edge.false_value: %r' % edge.false_value)

            # For now, specialcase:
            if self.op == '==':
                exprcode = gcc.EqExpr
                if stmt.exprcode == exprcode:
                    if stmt.lhs == self.lhs:
                        #raise 'bar'
                        if isinstance(stmt.rhs, gcc.IntegerCst) and stmt.rhs.constant == self.rhs:
                            if edge.true_value and self.boolval:
                                return True
                            if edge.false_value and not self.boolval:
                                return True
                            return False
            elif self.op == '!=':
                exprcode = gcc.NeExpr
                if stmt.exprcode == exprcode:
                    if stmt.lhs == self.lhs:
                        if isinstance(stmt.rhs, gcc.IntegerCst) and stmt.rhs.constant == self.rhs:
                            if edge.true_value and self.boolval:
                                return True
                            if edge.false_value and not self.boolval:
                                return True
                            return False
            else:
                raise UnhandledConditional() # FIXME
            """
            if stmt.exprcode == gcc.EqExpr:
                op = '==' if edge.true_value else '!='
            elif stmt.exprcode == gcc.LtExpr:
                op = '<' if edge.true_value else '>='
            elif stmt.exprcode == gcc.LeExpr:
                op = '<=' if edge.true_value else '>'
            """

class DummyCondition(StmtCondition):
    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return 'DummyCondition(%r)' % self.text

    def __str__(self):
        return self.text

    def matched_by(self, stmt, edge):
        return False # it's a placeholder

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


def make_exploded_graph(fun, sm):
    locations = get_locations(fun) # these will be our nodes

    # The initial state is the first block after entry (which has no statements):
    initbb = fun.cfg.entry.succs[0].dest
    initloc = Location(initbb, 0)
    expgraph = ExplodedGraph()
    expnode = expgraph.lazily_add_node(initloc, sm.states[0]) # initial state
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
            for t in srcstate.transitions:
                if t.condition.matched_by(stmt, edge):
                    dststate = t.dst
                    dstexpnode = lazily_add_node(dstloc, dststate)
                    expedge = expgraph.lazily_add_edge(srcexpnode, dstexpnode)
                    if t.output:
                        gcc.error(srcloc.get_gcc_loc(), t.output)
                    matches.append(t)
            if not matches:
                dstexpnode = lazily_add_node(dstloc, srcstate)
                expedge = expgraph.lazily_add_edge(srcexpnode, dstexpnode)
    return expgraph

def solve(fun, var):
    assert isinstance(var, (gcc.VarDecl, gcc.ParmDecl))

    # Example state machine:
    sm = Sm()
    s_all = sm.add_state('all')
    s_unknown = sm.add_state('unknown')
    s_null = sm.add_state('null')
    s_nonnull = sm.add_state('nonnull')
    s_freed = sm.add_state('freed')

    s_all.add_transition(ResultOfFunctionCall(var, 'malloc'), s_unknown)
    for s_src in s_unknown, s_null, s_nonnull:
        s_src.add_transition(ConditionalHasValue(var, '==', 0, True), s_null)
        s_src.add_transition(ConditionalHasValue(var, '==', 0, False), s_nonnull)
        s_src.add_transition(ConditionalHasValue(var, '!=', 0, True), s_nonnull)
        s_src.add_transition(ConditionalHasValue(var, '!=', 0, False), s_null)
    s_unknown.add_transition(DummyCondition('*%s' % var), s_unknown, 'use of possibly-NULL pointer %s' % var)
    s_null.add_transition(DummyCondition('*%s' % var), s_null, 'use of NULL pointer %s' % var)

    for s_src in s_all, s_unknown, s_null, s_nonnull:
        s_src.add_transition(FunctionCallWithArg('free', 1, var), s_freed)

    s_freed.add_transition(FunctionCallWithArg('free', 1, var), s_freed, 'double-free of %s' % var)
    s_freed.add_transition(DummyCondition('%s' % var), s_freed, 'use-after-free of %s' % var)

    s_unknown.add_transition(FunctionCallWithArg('memset', 1, var), s_unknown, 'use of possibly-NULL pointer %s' % var)
    s_null.add_transition(FunctionCallWithArg('memset', 1, var), s_null, 'use of NULL pointer %s' % var)
    s_freed.add_transition(FunctionCallWithArg('memset', 1, var), s_freed, 'use-after-free of %s' % var)

    if 0:
        dot = sm.to_dot()
        print(dot)
        invoke_dot(dot)

    if 0:
        solver = Solver(fun, sm)
        solver.solve()

    if 1:
        expgraph = make_exploded_graph(fun, sm)
        if 0:
            dot = expgraph.to_dot()
            # print(dot)
            invoke_dot(dot)

class SmPass(gcc.GimplePass):
    def __init__(self):
        gcc.GimplePass.__init__(self, 'sm-pass-gimple')

    def execute(self, fun):
        if 0:
            print(fun)

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

        vars_ = fun.local_decls + fun.decl.arguments
        if 0:
            print('vars_: %s' % vars_)

        for var in vars_:
            if 0:
                print(var)
                print(var.type)
            if isinstance(var.type, gcc.PointerType):
                # got pointer type
                solve(fun, var)
                #print('foo')


def main():
    gimple_ps = SmPass()
    if 1:
        # non-SSA version:
        gimple_ps.register_before('*warn_function_return')
    else:
        # SSA version:
        gimple_ps.register_after('ssa')
