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

ENABLE_TIMING=0
ENABLE_LOG=0
ENABLE_DEBUG=0
SHOW_SUPERGRAPH=0
DUMP_SOLUTION=0
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
        self.ctxt.timing('START: %s', self.name)
        self.ctxt._indent += 1

    def __exit__(self, exc_type, exc_value, traceback):
        self.ctxt._indent -= 1
        self.ctxt.timing('%s: %s  TIME TAKEN: %s',
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
        if isinstance(other, State):
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
    equivcls = item.equivcls
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
        # e.g. a function that free()s an arg has the caller's equivcls
        # marked as free also:
        assert isinstance(srcnode.stmt, gcc.GimpleCall)
        # ctxt.debug(srcnode.stmt)
        if equivcls:
            for param, arg  in zip(srcnode.stmt.fndecl.arguments,
                                   srcnode.stmt.args):
                # FIXME: change fndecl.arguments to fndecl.parameters
                if 1:
                    ctxt.debug('  param: %r', param)
                    ctxt.debug('  arg: %r', arg)
                #if ctxt.is_stateful_var(arg):
                #    shapechange.assign_var(param, arg)
                arg = simplify(arg)
                if arg in equivcls:
                    # Propagate state of the argument to the parameter:
                    yield WorklistItem.from_expr(dstnode, param, state, None)
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
            if equivcls and retval in equivcls:
                # Propagate state of the return value to the LHS of the caller:
                yield WorklistItem.from_expr(dstnode,
                                             simplify(edge.calling_stmtnode.stmt.lhs),
                                             state, None)

        # FIXME: we also need to backpatch the params, in case they've
        # changed state
        callsite = edge.dstnode.callnode.innernode
        ctxt.debug('callsite: %s', callsite)
        for param, arg  in zip(callsite.stmt.fndecl.arguments,
                               callsite.stmt.args):
            if 1:
                ctxt.debug('  param: %r', param)
                ctxt.debug('  arg: %r', arg)
            if equivcls and param in equivcls:
                yield WorklistItem.from_expr(dstnode, simplify(arg), state, None)

        if equivcls is None:
            yield WorklistItem(dstnode, None, state, None)

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
            if equivcls and rhs in equivcls:
                if isinstance(stmt.lhs, gcc.SsaName):
                    yield WorklistItem.from_expr(dstnode, simplify(stmt.lhs), state, None)
        elif stmt.exprcode == gcc.ComponentRef:
            # Field lookup
            compref = stmt.rhs[0]
            if 0:
                ctxt.debug(compref.target)
                ctxt.debug(compref.field)

            if equivcls and compref in equivcls:
                yield WorklistItem.from_expr(dstnode, compref, state, None)

            # The LHS potentially inherits state from the compref
            elif equivcls and compref.target in equivcls:
                ctxt.log('%s inheriting state "%s" from "%s" via field "%s"'
                    % (stmt.lhs,
                       state,
                       compref.target,
                       compref.field))
                yield WorklistItem.from_expr(dstnode, simplify(stmt.lhs), state, None)
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

    # Check to see if any of the precalculated matches from the sm script
    # apply:
    for pm in edge.possible_matches:
        ctxt.debug('possible match: %s' % pm)
        if state.name in pm.statenames and (equivcls is None or pm.expr in equivcls):
            ctxt.log('got match in state %r of %s at %s',
                     state, pm.describe(ctxt), stmt)
            with ctxt.indent():
                mctxt = MatchContext(ctxt, pm.match, srcnode, edge, state)
                ctxt.log('applying outcome to %s => %s',
                         mctxt.get_stateful_gccvar(),
                         pm.outcome)
                for item in pm.outcome.apply(mctxt):
                    ctxt.log('yielding item: %s', item)
                    yield item
                matches.append(pm)
        else:
            ctxt.debug('got match for wrong state %r of %s at %s',
                     state, pm.describe(ctxt), stmt)

    # Did nothing match, or are we expanding the "everything is in the
    # initial state" case?
    if not matches or equivcls is None:
        if equivcls:
            # Split the equivalence class, since the dstnode may have a
            # different partitioning from the srcnode:
            for expr in equivcls:
                yield WorklistItem.from_expr(dstnode, expr, state, None)
        else:
            yield WorklistItem(dstnode, equivcls, state, None)

class WorklistItem:
    """
    An item within the worklist, indicating a reachable node in which the
    given expression has a particular state, potentially indicating a Match
    instance also

    equivcls and state can also both be None, indicating the default state

    match is typically None (apart from those items in which a pattern
    matched).
    """
    __slots__ = ('node', 'equivcls', 'state', 'match')

    def __init__(self, node, equivcls, state, match):
        assert isinstance(equivcls, (frozenset, type(None)))
        self.node = node
        self.equivcls = equivcls
        self.state = state
        self.match = match

    @classmethod
    def from_expr(cls, node, expr, state, match):
        assert isinstance(expr, gcc.Tree)
        return WorklistItem(node, node.facts.get_aliases(expr),
                            state, match)

    def __hash__(self):
        return hash(self.node) ^ hash(self.equivcls) ^ hash(self.state) ^ hash(self.match)

    def __eq__(self, other):
        if self.node == other.node:
            if self.equivcls == other.equivcls:
                if self.state == other.state:
                    if self.match == other.match:
                        return True

    def __str__(self):
        from sm.facts import equivcls_to_str
        return 'node: %s   equivcls: %s   state: %s   match: %s' % (self.node, equivcls_to_str(self.equivcls), self.state, self.match)

    def __repr__(self):
        return '(%r, %r, %r, %r)' % (self.node, self.equivcls, self.state, self.match)

class PossibleMatch:
    def __init__(self, expr, sc, pattern, outcome, match):
        self.expr = expr
        self.statenames = frozenset(sc.statelist)
        self.sc = sc
        self.pattern = pattern
        self.outcome = outcome
        self.match = match

    def describe(self, ctxt):
        stateliststr = ', '.join([str(state)
                                  for state in self.statenames])
        return '%r: %s => %s due to %s' % (str(self.expr), stateliststr,
                                           self.outcome, self.pattern)

def find_possible_matches(ctxt, edge):
    result = []
    srcnode = edge.srcnode
    stmt = srcnode.stmt
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
                    ctxt.debug('match.get_stateful_gccvar(ctxt): %r', match.get_stateful_gccvar(ctxt))
                    for outcome in pr.outcomes:
                        # Resolve any booleans for the edge, either going
                        # directly to the guarded outcome, or discarding
                        # this one:
                        from sm.checker import BooleanOutcome
                        if isinstance(outcome, BooleanOutcome):
                            if edge.true_value and outcome.guard:
                                outcome = outcome.outcome
                            elif edge.false_value and not outcome.guard:
                                outcome = outcome.outcome
                            else:
                                continue
                        yield PossibleMatch(match.get_stateful_gccvar(ctxt),
                                            sc,
                                            pr.pattern,
                                            outcome,
                                            match)

class FixedPointMatchContext:
    """
    An actual match of a PossibleMatch, to be supplied to Outcome.get_result()
    """
    def __init__(self, ctxt, pm, edge, matchingstates):
        self.ctxt = ctxt
        self.pm = pm
        self.edge = edge
        self.matchingstates = matchingstates

class AbstractValue:
    def __init__(self, _dict):
        # dict from expr to set of states
        self._dict = _dict

    def __str__(self):
        kvstrs = []
        for expr, states in self._dict.iteritems():
            kvstrs.append('%s: %s' % (expr,
                                      stateset_to_str(states)))
        return '{%s}' % ', '.join(kvstrs)

    def __eq__(self, other):
        if isinstance(other, AbstractValue):
            return self._dict == other._dict

    def __ne__(self, other):
        return not self == other

    def match_states_by_name(self, expr, statenames):
        if expr in self._dict:
            # Do the state sets intersect?
            # (returning the intersection, which will be true if non-empty)
            result = [state
                      for state in self._dict[expr]
                      if state.name in statenames]
            return frozenset(result)

    def get_states_for_expr(self, ctxt, expr):
        if expr in self._dict:
            return self._dict[expr]
        return frozenset([ctxt.get_default_state()])

    def assign_to_from(self, ctxt, lhs, rhs):
        _dict = self._dict.copy()
        _dict[lhs] = self.get_states_for_expr(ctxt, rhs)
        return AbstractValue(_dict)

    def set_state_for_expr(self, expr, state):
        _dict = self._dict.copy()
        _dict[expr] = frozenset([state])
        return AbstractValue(_dict)

    @classmethod
    def make_entry_point(cls, ctxt, node):
        _dict = {}
        for expr in ctxt.scopes[node.function]:
            if isinstance(expr, (gcc.VarDecl, gcc.ParmDecl)):
                _dict[expr] = frozenset([ctxt.get_default_state()])
        return AbstractValue(_dict)

    @classmethod
    def get_edge_value(cls, ctxt, srcvalue, edge):
        assert isinstance(srcvalue, AbstractValue) # not None
        srcnode = edge.srcnode
        dstnode = edge.dstnode
        stmt = srcnode.get_stmt()
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
            return None
        elif isinstance(edge, CallToStart):
            # Alias the parameters with the arguments as necessary, so
            # e.g. a function that free()s an arg has the caller's expr
            # marked as free also:
            assert isinstance(srcnode.stmt, gcc.GimpleCall)
            # ctxt.debug(srcnode.stmt)
            _dict = {}
            for expr in ctxt.scopes[dstnode.function]:
                if isinstance(expr, gcc.VarDecl):
                    _dict[expr] = frozenset([ctxt.get_default_state()])
            for param, arg  in zip(srcnode.stmt.fndecl.arguments,
                                   srcnode.stmt.args):
                # FIXME: change fndecl.arguments to fndecl.parameters
                if 1:
                    ctxt.debug('  param: %r', param)
                    ctxt.debug('  arg: %r', arg)
                #if ctxt.is_stateful_var(arg):
                #    shapechange.assign_var(param, arg)
                arg = simplify(arg)
                _dict[param] = srcvalue.get_states_for_expr(ctxt, arg)
            return AbstractValue(_dict)
        elif isinstance(edge, ExitToReturnSite):
            # Propagate state through the return value:
            # ctxt.debug('edge.calling_stmtnode: %s', edge.calling_stmtnode)
            _dict = {}
            if edge.calling_stmtnode.stmt.lhs:
                exitsupernode = edge.srcnode
                assert isinstance(exitsupernode.innernode, ExitNode)
                retval = simplify(exitsupernode.innernode.returnval)
                ctxt.debug('retval: %s', retval)
                ctxt.debug('edge.calling_stmtnode.stmt.lhs: %s',
                           edge.calling_stmtnode.stmt.lhs)
                _dict[simplify(edge.calling_stmtnode.stmt.lhs)] = \
                    srcvalue.get_states_for_expr(ctxt, retval)

            # FIXME: we also need to backpatch the params, in case they've
            # changed state
            callsite = edge.dstnode.callnode.innernode
            ctxt.debug('callsite: %s', callsite)
            for param, arg  in zip(callsite.stmt.fndecl.arguments,
                                   callsite.stmt.args):
                if 1:
                    ctxt.debug('  param: %r', param)
                    ctxt.debug('  arg: %r', arg)
                _dict[simplify(arg)] = srcvalue.get_states_for_expr(ctxt, simplify(param))
            return AbstractValue(_dict)

        matches = []

        # Handle simple assignments so that variables inherit state:
        if isinstance(stmt, gcc.GimpleAssign):
            if 1:
                ctxt.debug('gcc.GimpleAssign: %s', stmt)
                ctxt.debug('  stmt.lhs: %r', stmt.lhs)
                ctxt.debug('  stmt.rhs: %r', stmt.rhs)
                ctxt.debug('  stmt.exprcode: %r', stmt.exprcode)
            if stmt.exprcode == gcc.VarDecl:
                lhs = simplify(stmt.lhs)
                rhs = simplify(stmt.rhs[0])
                return srcvalue.assign_to_from(ctxt, lhs, rhs)
            elif stmt.exprcode == gcc.ComponentRef:
                # Field lookup
                lhs = simplify(stmt.lhs)
                compref = stmt.rhs[0]
                if 1:
                    ctxt.debug('compref.target: %s', compref.target)
                    ctxt.debug('compref.field: %s', compref.field)

                # Do we already have a state for the field?
                if compref in srcvalue._dict:
                    return srcvalue.assign_to_from(ctxt, lhs, compref)
                else:
                    # Inherit the state from the struct:
                    _dict = srcvalue._dict.copy()
                    ctxt.log('%s inheriting states %s from "%s" via field "%s"'
                             % (lhs,
                                stateset_to_str(srcvalue.get_states_for_expr(ctxt, compref.target)),
                                compref.target,
                                compref.field))
                    return srcvalue.assign_to_from(ctxt, lhs, compref.target)
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

        # Check to see if any of the precalculated matches from the sm script
        # apply:
        for pm in edge.possible_matches:
            ctxt.log('possible match: %s', pm.describe(ctxt))
            matchingstates = srcvalue.match_states_by_name(pm.expr, pm.statenames)
            if matchingstates:
                ctxt.log('matchingstates: %s' % stateset_to_str(matchingstates))
                ctxt.log('got match in states %s of %s at %s',
                         stateset_to_str(matchingstates),
                         pm.describe(ctxt),
                         stmt)
                fpmctxt = FixedPointMatchContext(ctxt, pm, edge, matchingstates)
                ctxt.log('applying outcome to %s => %s',
                         fpmctxt.pm.expr,
                         pm.outcome)
                result = pm.outcome.get_result(fpmctxt, srcvalue)
                ctxt.log('got result: %s' % result)
                return result
            else:
                ctxt.log('matchingstates: %s' % matchingstates)
                ctxt.log('got match for wrong state {%s} for %s at %s',
                         stateset_to_str(srcvalue.get_states_for_expr(ctxt, pm.expr)),
                         pm.describe(ctxt), stmt)

        # Nothing matched:
        return srcvalue

    @classmethod
    def union(cls, ctxt, lhs, rhs):
        ctxt.log('union of %s and %s' % (lhs, rhs))
        if lhs is None:
            return rhs
        if rhs is None:
            return lhs
        assert isinstance(lhs, AbstractValue)
        assert isinstance(rhs, AbstractValue)
        _dict = lhs._dict.copy()
        for expr, states in rhs._dict.iteritems():
            if expr in _dict:
                _dict[expr] |= states
            else:
                _dict[expr] = states
        return AbstractValue(_dict)

def fixed_point_solver(ctxt):
    # Store "states" attribute on nodes giving a description of the possible
    # states that can reach this node.
    # Use "None" as the bottom element: unreachable
    # otherwise, an AbstractValue instance
    for node in ctxt.graph.nodes:
        node.states = None

    # FIXME: make this a priority queue, in the node's topological order?

    # Set up worklist:
    workset = set()
    worklist = []
    for node in ctxt.graph.get_entry_nodes():
        node.states = AbstractValue.make_entry_point(ctxt, node)
        for edge in node.succs:
            worklist.append(edge.dstnode)
            workset.add(edge.dstnode)

    numiters = 0
    while worklist:
        node = worklist.pop()
        workset.remove(node)
        numiters += 1
        ctxt.log('iter %i: analyzing node: %s', numiters, node)
        with ctxt.indent():
            oldvalue = node.states
            ctxt.log('old value: %s' % oldvalue)
            newvalue = None
            for edge in node.preds:
                ctxt.log('analyzing in-edge: %s', edge)
                with ctxt.indent():
                    srcvalue = edge.srcnode.states
                    ctxt.log('srcvalue: %s', srcvalue)
                    if srcvalue:
                        edgevalue = AbstractValue.get_edge_value(ctxt, srcvalue, edge)
                        ctxt.log('  edge value: %s', edgevalue)
                        newvalue = AbstractValue.union(ctxt, newvalue, edgevalue)
                        ctxt.log('  new value: %s', newvalue)
            if newvalue != oldvalue:
                ctxt.log('  value changed from: %s  to %s',
                         oldvalue,
                         newvalue)
                node.states = newvalue
                for edge in node.succs:
                    dstnode = edge.dstnode
                    if dstnode not in workset:
                        worklist.append(dstnode)
                        workset.add(dstnode)


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

    def timing(self, msg, *args):
        # Highest-level logging: how long does each stage take to run?
        if ENABLE_TIMING:
            formattedmsg = msg % args
            sys.stderr.write('TIMING: %s: %s%s\n'
                             % (self.sm.name, self._get_indent(), formattedmsg))

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

    def find_scopes(self):
        self.scopes = {}
        for function in self.graph.get_functions():
            scope = set()
            def add_to_scope(node):
                if isinstance(node, gcc.FunctionDecl):
                    return
                if isinstance(node, gcc.SsaName):
                    scope.add(node.var)
                if isinstance(node, (gcc.VarDecl, gcc.ParmDecl, gcc.ComponentRef)):
                    scope.add(node)
            for bb in function.cfg.basic_blocks:
                if bb.gimple:
                    for stmt in bb.gimple:
                        stmt.walk_tree(add_to_scope)
            self.scopes[function] = scope
        #self.log('scopes: %r' % self.scopes)

    def solve(self, name):
        # Preprocessing phase: identify the scope of expressions within each
        # function
        with Timer(self, 'find_scopes'):
            self.find_scopes()

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

        # Preprocessing: set up "matches" attribute for every edge in the
        # graph.  Although this is per-checker state, it's OK to store on
        # the graph itself as it will be overwritten for any subsequent
        # checkers:
        with Timer(self, 'find_possible_matches'):
            for edge in self.graph.edges:
                edge.possible_matches = list(find_possible_matches(self, edge))

        # Work-in-progress: find the fixed point of all possible states
        # reachable for each in-scope expr at each node.  This isn't yet
        # wired up to anything:
        with Timer(self, 'fixed_point_solver'):
            fixed_point_solver(self)

        # The "real" solver: an older implementation, which generates the
        # errors for later processing:
        solution = sm.solution.Solution(self)
        solution.find_states(self)

        return solution

    #######################################################################
    # Utility methods for writing selftests
    #######################################################################
    def find_call_of(self, funcname):
        for node in self.graph.nodes:
            stmt = node.stmt
            if isinstance(stmt, gcc.GimpleCall):
                if isinstance(stmt.fn, gcc.AddrExpr):
                    if isinstance(stmt.fn.operand, gcc.FunctionDecl):
                        if stmt.fn.operand.name == funcname:
                            return node

    def get_successor(self, node):
        if len(node.succs) > 1:
            raise ValueError('node %s has more than one successor' % node)
        return node.succs[0].dstnode

    def find_var(self, node, varname):
        for var in self.scopes[node.function]:
            if var.name == varname:
                return var
        raise ValueError('variable %s not found' % varname)

    def assert_states_for_var(self, node, varname, expectedstatenames):
        var = self.find_var(node, varname)
        expectedstates = set([State(name)
                              for name in expectedstatenames])
        actualstates = node.states.get_states_for_expr(self, var)
        assert actualstates == expectedstates

def solve(ctxt, name, selftest):
    ctxt.log('running %s', ctxt.sm.name)
    ctxt.log('len(ctxt.graph.nodes): %i', len(ctxt.graph.nodes))
    ctxt.log('len(ctxt.graph.edges): %i', len(ctxt.graph.edges))
    with Timer(ctxt, 'generating solution'):
        solution = ctxt.solve(name)
    if DUMP_SOLUTION:
        solution.dump(sys.stderr)
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

    if selftest:
        selftest(ctxt, solution)

def stateset_to_str(states):
    return '{%s}' % ', '.join([str(state) for state in states])

def equivcls_to_str(equivcls):
    return '{%s}' % ', '.join([str(expr) for expr in equivcls])
