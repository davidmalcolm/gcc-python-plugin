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

############################################################################
# Solver: what states are possible at each location?
############################################################################

ENABLE_LOG=0
ENABLE_DEBUG=0
SHOW_SUPERGRAPH=0
SHOW_SOLUTION=0
SHOW_ERROR_GRAPH=0

import sys
import time

import gcc

from gccutils import DotPrettyPrinter, invoke_dot
from gccutils.graph import Graph, Node, Edge, \
    ExitNode, SplitPhiNode, \
    CallToReturnSiteEdge, CallToStart, ExitToReturnSite
from gccutils.dot import to_html

import sm.checker
import sm.error
import sm.parser
import sm.solution

VARTYPES = (gcc.VarDecl, gcc.ParmDecl, )

class Timer:
    """
    Context manager for logging the start/finish of a particular activity
    and how long it takes
    """
    def __init__(self, ctxt, name):
        self.ctxt = ctxt
        self.name = name
        self.starttime = time.time()

    def get_elapsed_time(self):
        """Get elapsed time in seconds as a float"""
        curtime = time.time()
        return curtime - self.starttime

    def elapsed_time_as_str(self):
        """Get elapsed time as a string (with units)"""
        return '%0.3f seconds' % self.get_elapsed_time()

    def __enter__(self):
        self.ctxt.log('START: %s', self.name)
        self.ctxt._indent += 1

    def __exit__(self, exc_type, exc_value, traceback):
        self.ctxt._indent -= 1
        self.ctxt.log('%s: %s  TIME TAKEN: %s',
                      'STOP' if exc_type is None else 'ERROR',
                      self.name,
                      self.elapsed_time_as_str())

class State:
    """
    States are normally just names (strings), but potentially can have extra
    named attributes
    """
    def __init__(self, name, **kwargs):
        self.name = name
        self.kwargs = kwargs

    def __repr__(self):
        if self.kwargs:
            kwargs = ', '.join('%r=%r' % (k, v)
                               for k, v in self.kwargs.iteritems())
            return 'State(%r, %s)' % (self.name, kwargs)
        else:
            return 'State(%r)' % self.name

    def __str__(self):
        if self.kwargs:
            return repr(self)
        else:
            return self.name

    def __eq__(self, other):
        if self.name == other.name:
            if self.kwargs == other.kwargs:
                return True

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        result = hash(self.name)
        for k, v in self.kwargs.iteritems():
            result ^= hash(k) ^ hash(v)
        return result

    def __getattr__(self, name):
        if name in self.kwargs:
            return self.kwargs[name]
        if name in self.__dict__:
            return self.__dict[name]
        raise AttributeError('%s' % name)

class MatchContext:
    """
    A match of a specific rule, to be supplied to Outcome.apply()
    """
    def __init__(self, ctxt, match, srcnode, edge, srcstate):
        from sm.checker import Match
        from gccutils.graph import SupergraphNode, SupergraphEdge
        assert isinstance(match, Match)
        assert isinstance(srcnode, SupergraphNode)
        assert isinstance(edge, SupergraphEdge)
        self.ctxt = ctxt
        self.match = match
        self.srcnode = srcnode
        self.edge = edge
        self.srcstate = srcstate

    @property
    def dstnode(self):
        return self.edge.dstnode

    def get_stateful_gccvar(self):
        return self.match.get_stateful_gccvar(self.ctxt)

def simplify(gccexpr):
    if isinstance(gccexpr, gcc.SsaName):
        return gccexpr.var
    return gccexpr

def consider_edge(ctxt, solution, item, edge):
    """
    yield any WorklistItem instances that may need further consideration
    """
    srcnode = item.node
    expr = item.expr
    state = item.state

    stmt = srcnode.get_stmt()
    assert edge.srcnode == srcnode
    dstnode = edge.dstnode
    ctxt.debug('edge from: %s', srcnode)
    ctxt.debug('       to: %s', dstnode)

    # Set the location so that if an unhandled exception occurs, it should
    # at least identify the code that triggered it:
    if stmt:
        if stmt.loc:
            gcc.set_location(stmt.loc)

    # Handle interprocedural edges:
    if isinstance(edge, CallToReturnSiteEdge):
        # Ignore the intraprocedural edge for a function call:
        return
    elif isinstance(edge, CallToStart):
        # Alias the parameters with the arguments as necessary, so
        # e.g. a function that free()s an arg has the caller's expr
        # marked as free also:
        assert isinstance(srcnode.stmt, gcc.GimpleCall)
        # ctxt.debug(srcnode.stmt)
        if expr:
            for param, arg  in zip(srcnode.stmt.fndecl.arguments,
                                   srcnode.stmt.args):
                # FIXME: change fndecl.arguments to fndecl.parameters
                if 1:
                    ctxt.debug('  param: %r', param)
                    ctxt.debug('  arg: %r', arg)
                #if ctxt.is_stateful_var(arg):
                #    shapechange.assign_var(param, arg)
                arg = simplify(arg)
                if expr == arg:
                    # Propagate state of the argument to the parameter:
                    yield WorklistItem(dstnode, param, state, None)
        else:
            yield WorklistItem(dstnode, None, state, None) # FIXME
        # Stop iterating, effectively purging state outside that of the
        # called function:
        return
    elif isinstance(edge, ExitToReturnSite):
        # Propagate state through the return value:
        # ctxt.debug('edge.calling_stmtnode: %s', edge.calling_stmtnode)
        if edge.calling_stmtnode.stmt.lhs:
            exitsupernode = edge.srcnode
            assert isinstance(exitsupernode.innernode, ExitNode)
            retval = simplify(exitsupernode.innernode.returnval)
            ctxt.debug('retval: %s', retval)
            ctxt.debug('edge.calling_stmtnode.stmt.lhs: %s', edge.calling_stmtnode.stmt.lhs)
            if expr == retval:
                # Propagate state of the return value to the LHS of the caller:
                yield WorklistItem(dstnode, simplify(edge.calling_stmtnode.stmt.lhs), state, None)

        # FIXME: we also need to backpatch the params, in case they've
        # changed state
        callsite = edge.dstnode.callnode.innernode
        ctxt.debug('callsite: %s', callsite)
        for param, arg  in zip(callsite.stmt.fndecl.arguments,
                               callsite.stmt.args):
            if 1:
                ctxt.debug('  param: %r', param)
                ctxt.debug('  arg: %r', arg)
            if expr == param:
                yield WorklistItem(dstnode, simplify(arg), state, None)

        # Stop iterating, effectively purging state local to the called
        # function:
        return

    matches = []

    # Handle simple assignments so that variables inherit state:
    if isinstance(stmt, gcc.GimpleAssign):
        if 1:
            ctxt.debug('gcc.GimpleAssign: %s', stmt)
            ctxt.debug('  stmt.lhs: %r', stmt.lhs)
            ctxt.debug('  stmt.rhs: %r', stmt.rhs)
            ctxt.debug('  stmt.exprcode: %r', stmt.exprcode)
        if stmt.exprcode == gcc.VarDecl:
            rhs = simplify(stmt.rhs[0])
            if rhs == expr:
                if isinstance(stmt.lhs, gcc.SsaName):
                    yield WorklistItem(dstnode, simplify(stmt.lhs), state, None)
        elif stmt.exprcode == gcc.ComponentRef:
            # Field lookup
            compref = stmt.rhs[0]
            if 0:
                ctxt.debug(compref.target)
                ctxt.debug(compref.field)
            # The LHS potentially inherits state from the compref
            if expr == compref.target:
                ctxt.log('%s inheriting state "%s" from "%s" via field "%s"'
                    % (stmt.lhs,
                       state,
                       compref.target,
                       compref.field))
                yield WorklistItem(dstnode, simplify(stmt.lhs), state, None)
                # matches.append(stmt)
    elif isinstance(stmt, gcc.GimplePhi):
        if 1:
            ctxt.debug('gcc.GimplePhi: %s', stmt)
            ctxt.debug('  srcnode: %s', srcnode)
            ctxt.debug('  srcnode: %r', srcnode)
            ctxt.debug('  srcnode.innernode: %s', srcnode.innernode)
            ctxt.debug('  srcnode.innernode: %r', srcnode.innernode)
        assert isinstance(srcnode.innernode, SplitPhiNode)
        rhs = srcnode.innernode.rhs
        if isinstance(rhs, gcc.VarDecl):
            shapechange = ShapeChange(srcshape)
            shapechange.assign_var(stmt.lhs, rhs)
            dstexpnode = expgraph.lazily_add_node(dstnode, shapechange.dstshape)
            expedge = expgraph.lazily_add_edge(srcexpnode, dstexpnode,
                                               edge, None, shapechange)
            matches.append(stmt)

    for sc in ctxt._stateclauses:
        # Locate any rules that could apply, regardless of the current
        # state:
        for pr in sc.patternrulelist:
            with ctxt.indent():
                # ctxt.debug('%r: %r', (srcshape, pr))
                # For now, skip interprocedural calls and the
                # ENTRY/EXIT nodes:
                if not stmt:
                    continue
                # Now see if the rules apply for the current state:
                ctxt.debug('considering pattern %s for stmt: %s', pr.pattern, stmt)
                ctxt.debug('considering pattern %r for stmt: %r', pr.pattern, stmt)
                for match in pr.pattern.iter_matches(stmt, edge, ctxt):
                    ctxt.debug('pr.pattern: %r', pr.pattern)
                    ctxt.debug('match: %r', match)
                    ctxt.debug('expr: %r', expr)
                    ctxt.debug('match.get_stateful_gccvar(ctxt): %r', match.get_stateful_gccvar(ctxt))
                    #srcstate = srcshape.get_state(match.get_stateful_gccvar(ctxt))
                    ctxt.debug('state: %r', (state, ))
                    assert isinstance(state, State)
                    if state.name in sc.statelist and (expr is None or expr == match.get_stateful_gccvar(ctxt)):
                        assert len(pr.outcomes) > 0
                        ctxt.log('got match in state %r of %r at %r: %s',
                                 state,
                                 str(pr.pattern),
                                 str(stmt),
                                 match)
                        with ctxt.indent():
                            mctxt = MatchContext(ctxt, match, srcnode, edge, state)
                            for outcome in pr.outcomes:
                                ctxt.log('applying outcome to %s => %s',
                                         mctxt.get_stateful_gccvar(),
                                         outcome)
                                for item in outcome.apply(mctxt):
                                    ctxt.log('yielding item: %s', item)
                                    yield item
                            matches.append(pr)
                    else:
                        ctxt.debug('got match for wrong state %r of %r at %r: %s',
                                 state,
                                 str(pr.pattern),
                                 str(stmt),
                                 match)
    # FIXME: the "expr is None" here continues the analysis for the
    # the wildcard case, but isn't working well:
    # (looking at tests/sm/checkers/malloc-checker/two_ptrs )
    if not matches or expr is None:
        yield WorklistItem(dstnode, expr, state, None)

class WorklistItem:
    """
    An item within the worklist, indicating a reachable node in which the
    given expression has a particular state, potentially indicating a Match
    instance also

    expr and state can also both be None, indicating the default state

    match is typically None (apart from those items in which a pattern
    matched).
    """
    __slots__ = ('node', 'expr', 'state', 'match')

    def __init__(self, node, expr, state, match):
        self.node = node
        self.expr = expr
        self.state = state
        self.match = match

    def __hash__(self):
        return hash(self.node) ^ hash(self.expr) ^ hash(self.state) ^ hash(self.match)

    def __eq__(self, other):
        if self.node == other.node:
            if self.expr == other.expr:
                if self.state == other.state:
                    if self.match == other.match:
                        return True

    def __str__(self):
        return 'node: %s   expr: %s   state: %s   match: %s' % (self.node, self.expr, self.state, self.match)

    def __repr__(self):
        return '(%r, %r, %r, %r)' % (self.node, self.expr, self.state, self.match)

class Context:
    # An sm.checker.Sm (do we need any other context?)

    # in context, with a mapping from its vars to gcc.VarDecl
    # (or ParmDecl) instances
    def __init__(self, ch, sm, graph, options):
        self.options = options

        self.ch = ch
        self.sm = sm
        self.graph = graph

        # The Context caches some information about the sm to help
        # process it efficiently:
        #
        #   all state names:
        self.statenames = list(sm.iter_states())

        #   a mapping from str (decl names) to Decl instances
        self._decls = {}

        #   the stateful decl, if any:
        self._stateful_decl = None

        #   a mapping from str (pattern names) to NamedPattern instances
        self._namedpatterns = {}

        #   all StateClause instance, in order:
        self._stateclauses = []

        # Does any Python code call set_state()?
        # (If so, we can't detect unreachable states)
        self._uses_set_state = False

        self._indent = 0

        reachable_statenames = set([self.statenames[0]])

        # Set up the above attributes:
        from sm.checker import Decl, NamedPattern, StateClause, \
            PythonFragment, PythonOutcome
        for clause in sm.clauses:
            if isinstance(clause, Decl):
                self._decls[clause.name] = clause
                if clause.has_state:
                    self._stateful_decl = clause
            elif isinstance(clause, NamedPattern):
                self._namedpatterns[clause.name] = clause
            elif isinstance(clause, PythonFragment):
                if 'set_state' in clause.src:
                    self._uses_set_state = True
            elif isinstance(clause, StateClause):
                self._stateclauses.append(clause)
                for pr in clause.patternrulelist:
                    for outcome in pr.outcomes:
                        for statename in outcome.iter_reachable_statenames():
                            reachable_statenames.add(statename)
                    if isinstance(outcome, PythonOutcome):
                        if 'set_state' in outcome.src:
                            self._uses_set_state = True

        # 2nd pass: validate the sm:
        for clause in sm.clauses:
            if isinstance(clause, StateClause):
                for statename in clause.statelist:
                    if statename not in reachable_statenames \
                            and not self._uses_set_state:
                        class UnreachableState(Exception):
                            def __init__(self, statename):
                                self.statename = statename
                            def __str__(self):
                                return str(self.statename)
                        raise UnreachableState(statename)

        # Store the errors so that we can play them back in source order
        # (for greater predicability of selftests):
        self._errors = []

        # Run any initial python code:
        self.python_locals = {}
        self.python_globals = {}
        for clause in sm.clauses:
            if isinstance(clause, PythonFragment):
                filename = self.ch.filename
                if not filename:
                    filename = '<string>'
                expr = clause.get_source()
                code = compile(expr, filename, 'exec')
                # FIXME: the filename of the .sm file is correct, but the line
                # numbers will be wrong
                result = eval(code, self.python_globals, self.python_locals)

    def __repr__(self):
        return 'Context(%r)' % (self.statenames, )

    def indent(self):
        class IndentCM:
            # context manager for indenting/outdenting the log
            def __init__(self, ctxt):
                self.ctxt = ctxt

            def __enter__(self):
                self.ctxt._indent += 1

            def __exit__(self, exc_type, exc_value, traceback):
                self.ctxt._indent -= 1
        return IndentCM(self)

    def _get_indent(self):
        # Indent by the stack depth plus self._indent:
        depth = 0
        f = sys._getframe()
        while f:
            depth += 1
            f = f.f_back
        return ' ' * (depth + self._indent)

    def log(self, msg, *args):
        # High-level logging
        if ENABLE_LOG:
            formattedmsg = msg % args
            sys.stderr.write('LOG  : %s: %s%s\n'
                             % (self.sm.name, self._get_indent(), formattedmsg))

    def debug(self, msg, *args):
        # Lower-level logging
        if ENABLE_DEBUG:
            formattedmsg = msg % args
            sys.stderr.write('DEBUG: %s: %s%s\n'

                             % (self.sm.name, self._get_indent(), formattedmsg))

    def lookup_decl(self, declname):
        class UnknownDecl(Exception):
            def __init__(self, declname):
                self.declname = declname
            def __str__(self):
                return repr(declname)
        if declname not in self._decls:
            raise UnknownDecl(declname)
        return self._decls[declname]

    def lookup_pattern(self, patname):
        '''Lookup a named pattern'''
        class UnknownNamedPattern(Exception):
            def __init__(self, patname):
                self.patname = patname
            def __str__(self):
                return repr(patname)
        if patname not in self._namedpatterns:
            raise UnknownNamedPattern(patname)
        return self._namedpatterns[patname]

    def add_error(self, srcnode, match, msg, state):
        self.log('add_error(%r, %r, %r, %r)', srcnode, match, msg, state)
        err = sm.error.Error(srcnode, match, msg, state)
        if self.options.cache_errors:
            self._errors.append(err)
        else:
            # Easier to debug tracebacks this way:
            err.emit(self, solution)

    def emit_errors(self, solution):
        curfun = None
        curfile = None
        for error in sorted(self._errors):
            gccloc = error.gccloc
            if error.function != curfun or gccloc.file != curfile:
                # Fake the function-based output
                # e.g.:
                #    "tests/sm/examples/malloc-checker/input.c: In function 'use_after_free':"
                import sys
                sys.stderr.write("%s: In function '%s':\n"
                                 % (gccloc.file, error.function.decl.name))
                curfun = error.function
                curfile = gccloc.file
            error.emit(self, solution)

    def compare(self, gccexpr, smexpr):
        if 0:
            self.debug('  compare(%r, %r)', gccexpr, smexpr)

        if isinstance(gccexpr, (gcc.VarDecl, gcc.ParmDecl, gcc.SsaName)):
            #if gccexpr == self.var:
            # self.debug '%r' % self.sm.varclauses.name
            #if smexpr == self.sm.varclauses.name:
            if isinstance(smexpr, str):
                decl = self.lookup_decl(smexpr)
                if decl.matched_by(gccexpr):
                    return gccexpr

        if isinstance(gccexpr, gcc.IntegerCst):
            if isinstance(smexpr, (int, long)):
                if gccexpr.constant == smexpr:
                    return gccexpr
            if isinstance(smexpr, str):
                decl = self.lookup_decl(smexpr)
                if decl.matched_by(gccexpr):
                    return gccexpr

        if isinstance(gccexpr, gcc.AddrExpr):
            # Dereference:
            return self.compare(gccexpr.operand, smexpr)

        if isinstance(gccexpr, gcc.ComponentRef):
            # Dereference:
            return self.compare(gccexpr.target, smexpr)

        return None

    def get_default_state(self):
        return State(self.statenames[0])

    def is_stateful_var(self, gccexpr):
        '''
        Is this gcc.Tree of a kind that has state according to the current sm?
        '''
        if isinstance(gccexpr, gcc.SsaName):
            if isinstance(gccexpr.type, gcc.PointerType):
                # TODO: the sm may impose further constraints
                return True

    def set_state(self, mctxt, name, **kwargs):
        dststate = State(name, **kwargs)
        dstshape, shapevars = mctxt.srcshape._copy()
        dstshape.set_state(mctxt.get_stateful_gccvar(), dststate)
        dstexpnode = mctxt.expgraph.lazily_add_node(mctxt.dstnode, dstshape)
        expedge = mctxt.expgraph.lazily_add_edge(mctxt.srcexpnode, dstexpnode,
                                                 mctxt.inneredge, mctxt.match, None)

    def solve(self, name):
        # Preprocessing phase: gather simple per-node "facts", for use in
        # giving better names for temporaries, and for identifying the return
        # values of functions
        from sm.facts import find_facts
        with Timer(self, 'find_facts'):
            find_facts(self, self.graph)

        # Preprocessing phase: locate places where rvalues are leaked, for
        # later use by $leaked/LeakedPattern
        from sm.leaks import find_leaks
        with Timer(self, 'find_leaks'):
            find_leaks(self)

        solution = sm.solution.Solution(self)
        worklist = [WorklistItem(node, None, self.get_default_state(), None)
                    for node in self.graph.get_entry_nodes()]
        done = set()
        while worklist:
            item = worklist.pop()
            done.add(item)
            statedict = solution.states[item.node]
            if item.expr in statedict:
                statedict[item.expr].add(item.state)
            else:
                statedict[item.expr] = set([item.state])
            with self.indent():
                self.debug('considering %s', item)
                for edge in item.node.succs:
                    self.debug('considering edge %s', edge)
                    assert edge.srcnode == item.node
                    for nextitem in consider_edge(self, solution, item, edge):
                        assert isinstance(nextitem, WorklistItem)
                        if nextitem not in done:
                            worklist.append(nextitem)
                        # FIXME: we can also handle *transitions* here,
                        # adding them to the per-node dict.
                        # We can use them when reporting errors in order
                        # to reconstruct paths
                        changesdict = solution.changes[item.node]
                        key = (item.expr, item.state)
                        if key in changesdict:
                            changesdict[key].add(nextitem)
                        else:
                            changesdict[key] = set([nextitem])
                        # FIXME: what exactly should we be storing?
        return solution

def solve(ctxt, name):
    ctxt.log('running %s', ctxt.sm.name)
    ctxt.log('len(ctxt.graph.nodes): %i', len(ctxt.graph.nodes))
    ctxt.log('len(ctxt.graph.edges): %i', len(ctxt.graph.edges))
    with Timer(ctxt, 'generating solution'):
        solution = ctxt.solve(name)
    if SHOW_SOLUTION:
        dot = solution.to_dot(name)
        # Debug: view the solution:
        if 0:
            ctxt.debug(dot)
        invoke_dot(dot, name)

    ctxt.log('len(ctxt._errors): %i', len(ctxt._errors))

    # Now report the errors, grouped by function, and in source order:
    ctxt._errors.sort()

    with Timer(ctxt, 'emitting errors'):
        ctxt.emit_errors(solution)
