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

############################################################################
# Solver: what states are possible at each location?
############################################################################

from collections import Counter
import sys

import gcc

from gccutils import DotPrettyPrinter, invoke_dot
from gccutils.dot import to_html
from gccutils.graph import Graph, Node, Edge
from gccutils.graph.stmtgraph import ExitNode, SplitPhiNode
from gccutils.graph.supergraph import \
    CallToReturnSiteEdge, CallToStart, ExitToReturnSite, \
    SupergraphNode, SupergraphEdge, CallNode, ReturnNode, FakeEntryEdge
from gccutils.graph.query import Query

import sm.checker
from sm.checker import Match, BooleanOutcome, \
    Decl, NamedPattern, StateClause, \
    PythonFragment, PythonOutcome
import sm.dataflow
import sm.error
import sm.parser
from sm.reporter import StderrReporter, JsonReporter
import sm.solution
from sm.utils import Timer, simplify, stateset_to_str, equivcls_to_str

VARTYPES = (gcc.VarDecl, gcc.ParmDecl, )

class State(object):
    """
    States are normally just names (strings), but potentially can have extra
    named attributes
    """
    __slots__ = ('name', 'kwargs')

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

class StateNameSet(frozenset):
    __slots__ = ('has_wildcard', )

    def __init__(self, statenames):
        frozenset.__init__(self, statenames)
        self.has_wildcard = False
        for statename in statenames:
            if statename.endswith('*'):
                self.has_wildcard = True
                break

    def __contains__(self, key):
        if self.has_wildcard:
            return True
        return frozenset.__contains__(self, key)

class PossibleMatch(object):
    __slots__ = ('expr',
                 'statenames',
                 'sc',
                 'pattern',
                 'outcomes',
                 'match')

    def __init__(self, expr, sc, pattern, outcomes, match):
        self.expr = expr
        self.statenames = StateNameSet(sc.statelist)
        self.sc = sc
        self.pattern = pattern
        self.outcomes = outcomes
        self.match = match

    def describe(self, ctxt):
        stateliststr = ', '.join([str(state)
                                  for state in self.statenames])
        outcomeliststr = ', '.join([str(outcome)
                                    for outcome in self.outcomes])
        return '%r: %s => %s due to %s' % (str(self.expr), stateliststr,
                                           outcomeliststr, self.pattern)

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

                    # Filter the list of outcomes to those that actually apply:
                    outcomes = []
                    for outcome in pr.outcomes:
                        # Resolve any booleans for the edge, either going
                        # directly to the guarded outcome, or discarding
                        # this one:
                        if isinstance(outcome, BooleanOutcome):
                            if edge.true_value and outcome.guard:
                                outcome = outcome.outcome
                            elif edge.false_value and not outcome.guard:
                                outcome = outcome.outcome
                            else:
                                continue
                        outcomes.append(outcome)

                    yield PossibleMatch(match.get_stateful_gccvar(ctxt),
                                        sc,
                                        pr.pattern,
                                        outcomes,
                                        match)

class StatesForNode(sm.dataflow.AbstractValue):
    """
    The possible states that data can be in at a particular node in the
    graph, tracked by equivalence classes (which themselves come from
    sm.facts.Facts for the node).

    * topmost value: None signifies "unreachable": empty set of possible
      states

    * intermediate values: mapping from equivalence classes to sets of
      possible states that the given equivalence class can be in

    * bottommost value: each mapping has the set of *all* possible states

    * the "meet" of two values is the set of all possible states from
      either, hence keywise-union of the possible states for each
      equivalence class.
    """
    def __init__(self, node, _dict):
        assert isinstance(node, SupergraphNode)
        self.node = node

        # dict from equivcls to set of states
        self._dict = _dict

    def __str__(self):
        kvstrs = []
        for equivcls, states in self._dict.iteritems():
            kvstrs.append('%s=%s' % (equivcls_to_str(equivcls),
                                     stateset_to_str(states)))
        return '{%s}' % ', '.join(kvstrs)

    def __eq__(self, other):
        if isinstance(other, StatesForNode):
            if self.node == other.node:
                return self._dict == other._dict

    def __ne__(self, other):
        return not self == other

    def get_combo_count(self):
        """
        How many possible subsets does this have?
        """
        result = 1
        for equivcls, states in self._dict.iteritems():
            result *= len(states)
        return result

    def get_equivcls_for_expr(self, ctxt, expr):
        return ctxt.get_aliases(self.node, expr)

    def match_states_by_name(self, ctxt, expr, statenames):
        equivcls = self.get_equivcls_for_expr(ctxt, expr)
        if equivcls in self._dict:
            # Do the state sets intersect?
            # (returning the intersection, which will be true if non-empty)
            result = [state
                      for state in self._dict[equivcls]
                      if state.name in statenames]
            return frozenset(result)

    def get_states_for_expr(self, ctxt, expr):
        equivcls = self.get_equivcls_for_expr(ctxt, expr)
        if equivcls in self._dict:
            return self._dict[equivcls]
        return frozenset([ctxt.get_default_state()])

    def is_subset_of(self, other):
        assert isinstance(other, StatesForNode)
        assert self.node == other.node
        for equivcls, states in self._dict.iteritems():
            if not states.issubset(other._dict[equivcls]):
                return False
        return True

    def assign_to_from(self, ctxt, dstnode, lhs, rhs):
        assert isinstance(dstnode, SupergraphNode)
        result = self.propagate_to(ctxt, dstnode)
        result._dict[ctxt.get_aliases(dstnode, lhs)] = \
            self.get_states_for_expr(ctxt, rhs)
        return result

    def set_state_for_expr(self, ctxt, dstnode, expr, state):
        assert isinstance(dstnode, SupergraphNode)
        assert isinstance(state, State)
        result = self.propagate_to(ctxt, dstnode)
        result._dict[ctxt.get_aliases(dstnode, expr)] = frozenset([state])
        return result

    def propagate_to(self, ctxt, dstnode):
        assert isinstance(dstnode, SupergraphNode)
        _dict = {}
        for equivcls, states in self._dict.iteritems():
            for expr in equivcls:
                _dict[ctxt.get_aliases(dstnode, expr)] = states
        return StatesForNode(dstnode, _dict)

    @classmethod
    def make_entry_point(cls, ctxt, node):
        _dict = {}
        function = node.function
        if function:
            for expr in ctxt.smexprs[function]:
                if isinstance(expr, (gcc.VarDecl, gcc.ParmDecl)):
                    _dict[ctxt.get_aliases(node, expr)] = \
                        frozenset([ctxt.get_default_state()])
        return StatesForNode(node, _dict)

    @classmethod
    def get_edge_value(cls, ctxt, srcvalue, edge):
        assert isinstance(srcvalue, StatesForNode) # not None
        srcnode = edge.srcnode
        dstnode = edge.dstnode
        stmt = srcnode.get_stmt()
        ctxt.debug('edge from: %s', srcnode)
        ctxt.debug('       to: %s', dstnode)

        # Handle interprocedural edges:
        if isinstance(edge, CallToReturnSiteEdge):
            # Ignore the intraprocedural edge for a function call:
            return None, None
        elif isinstance(edge, CallToStart):
            # Alias the parameters with the arguments as necessary, so
            # e.g. a function that free()s an arg has the caller's expr
            # marked as free also:
            assert isinstance(srcnode.stmt, gcc.GimpleCall)
            # ctxt.debug(srcnode.stmt)
            _dict = {}
            for expr in ctxt.smexprs[dstnode.function]:
                if isinstance(expr, gcc.VarDecl):
                    _dict[ctxt.get_aliases(dstnode, expr)] = \
                        frozenset([ctxt.get_default_state()])
            for param, arg  in zip(srcnode.stmt.fndecl.arguments,
                                   srcnode.stmt.args):
                # FIXME: change fndecl.arguments to fndecl.parameters
                if 1:
                    ctxt.debug('  param: %r', param)
                    ctxt.debug('  arg: %r', arg)
                #if ctxt.is_stateful_var(arg):
                #    shapechange.assign_var(param, arg)
                arg = simplify(arg)
                _dict[ctxt.get_aliases(dstnode, param)] = \
                    srcvalue.get_states_for_expr(ctxt, arg)
            return StatesForNode(dstnode, _dict), None
        elif isinstance(edge, FakeEntryEdge):
            _dict = {}
            for expr in ctxt.smexprs[dstnode.function]:
                if isinstance(expr, (gcc.VarDecl, gcc.ParmDecl)):
                    _dict[ctxt.get_aliases(dstnode, expr)] = \
                        frozenset([ctxt.get_default_state()])
            return StatesForNode(dstnode, _dict), None
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
                _dict[ctxt.get_aliases(dstnode, simplify(edge.calling_stmtnode.stmt.lhs))] = \
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
                _dict[ctxt.get_aliases(dstnode, simplify(arg))] = \
                    srcvalue.get_states_for_expr(ctxt, simplify(param))
            return StatesForNode(dstnode, _dict), None

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
                return srcvalue.assign_to_from(ctxt, dstnode, lhs, rhs), None
            elif stmt.exprcode == gcc.ComponentRef:
                # Field lookup
                lhs = simplify(stmt.lhs)
                compref = stmt.rhs[0]
                if 1:
                    ctxt.debug('compref.target: %s', compref.target)
                    ctxt.debug('compref.field: %s', compref.field)

                # Do we already have a state for the field?
                if ctxt.get_aliases(srcnode, compref) in srcvalue._dict:
                    return srcvalue.assign_to_from(ctxt, dstnode, lhs, compref), None
                else:
                    # Inherit the state from the struct:
                    if ctxt.options.enable_log:
                        ctxt.log('%s inheriting states %s from "%s" via field "%s"',
                                 lhs,
                                 stateset_to_str(srcvalue.get_states_for_expr(ctxt, compref.target)),
                                 compref.target,
                                 compref.field)
                    return srcvalue.assign_to_from(ctxt, dstnode, lhs, compref.target), None
        elif isinstance(stmt, gcc.GimplePhi):
            if 1:
                ctxt.debug('gcc.GimplePhi: %s', stmt)
                ctxt.debug('  srcnode: %s', srcnode)
                ctxt.debug('  srcnode: %r', srcnode)
                ctxt.debug('  srcnode.innernode: %s', srcnode.innernode)
                ctxt.debug('  srcnode.innernode: %r', srcnode.innernode)
            assert isinstance(srcnode.innernode, SplitPhiNode)
            rhs = simplify(srcnode.innernode.rhs)
            ctxt.debug('  rhs: %r', rhs)
            lhs = simplify(srcnode.stmt.lhs)
            ctxt.debug('  lhs: %r', lhs)
            return srcvalue.assign_to_from(ctxt, dstnode, lhs, rhs), None

        # Check to see if any of the precalculated matches from the sm script
        # apply:
        for pm in ctxt.possible_matches_for_edge[edge]:
            if ctxt.options.enable_log:
                ctxt.log('possible match: %s', pm.describe(ctxt))
            matchingstates = srcvalue.match_states_by_name(ctxt, pm.expr, pm.statenames)
            if matchingstates:
                if ctxt.options.enable_log:
                    ctxt.log('matchingstates: %s' % stateset_to_str(matchingstates))
                    ctxt.log('got match in states %s of %s at %s',
                             stateset_to_str(matchingstates),
                             pm.describe(ctxt),
                             stmt)

                # What state changes happen in the outcomes?
                # Apply the outcomes in order, merging the result of any
                # that lead to state changes.
                result = None
                for state in matchingstates:
                    oldstate = state
                    for outcome in pm.outcomes:
                        if ctxt.options.enable_log:
                            ctxt.log('applying outcome to %s => %s with %s',
                                     pm.expr,
                                     outcome,
                                     state)
                        effect = outcome.get_effect_for_state(ctxt, edge,
                                                              pm.match, state)

                        # Update the effective state as seen by subsequent
                        # outcomes for this pattern match:
                        state = effect.dststate

                    # Extract state changes from the effect:
                    newresult = srcvalue.set_state_for_expr(ctxt,
                                                            edge.dstnode,
                                                            pm.expr,
                                                            state)
                    ctxt.log('newresult: %s' % newresult)
                    result = StatesForNode.meet(ctxt, result, newresult)

                # "result" is now the merger of all possible result states
                # for all input states

                # If none of the outcomes caused state changes, propagate
                # them:
                if result is None:
                    raise foo
                    #result = srcvalue.propagate_to(ctxt, edge.dstnode)

                ctxt.log('got result: %s', result)
                return result, pm.match
            else:
                if ctxt.options.enable_log:
                    ctxt.log('matchingstates: %s', matchingstates)
                    ctxt.log('got match for wrong state {%s} for %s at %s',
                             stateset_to_str(srcvalue.get_states_for_expr(ctxt, pm.expr)),
                             pm.describe(ctxt), stmt)

        # Nothing matched:
        return srcvalue.propagate_to(ctxt, dstnode), None

    @classmethod
    def meet(cls, ctxt, lhs, rhs):
        ctxt.log('meet of %s and %s', lhs, rhs)
        if lhs is None:
            return rhs
        if rhs is None:
            return lhs
        assert isinstance(lhs, StatesForNode)
        assert isinstance(rhs, StatesForNode)
        assert lhs.node == rhs.node
        _dict = lhs._dict.copy()
        for expr, states in rhs._dict.iteritems():
            if expr in _dict:
                _dict[expr] |= states
            else:
                _dict[expr] = states
        return StatesForNode(lhs.node, _dict)

def show_state_histogram(ctxt):
    # Show an ASCII-art histogram to analyze how many state combinations
    # there are: how many nodes have each number of valid state
    # combinations (including None)
    cnt = Counter()
    for node in ctxt.graph.nodes:
        states = ctxt.states_for_node[node]
        if states:
            cnt[states.get_combo_count()] += 1
        else:
            cnt[None] += 1
    extent = cnt.most_common(1)[0][1]
    scale = 40.0 / extent
    ctxt.timing('%6s : %5s :', 'COMBOS', 'NODES')
    for key in sorted(cnt.keys()):
        ctxt.timing('%6s : %5s : %s',
                    key, cnt[key],
                    '*' * int(cnt[key] * scale))

def generate_errors_from_fixed_point(ctxt):
    """
    Rerun all reachable matches on the fixed point states in order to allow
    any Python fragments to emit any errors on the reachable states.

    The errors are added to ctxt.errors_from_fixed_point
    """
    for node in ctxt.graph.nodes:
        ctxt.debug('analyzing node: %s', node)
        states = ctxt.states_for_node[node]
        if states is None:
            continue
        with ctxt.indent():
            stmt = node.stmt
            for edge in node.succs:
                ctxt.debug('analyzing out-edge: %s', edge)
                with ctxt.indent():
                    for pm in ctxt.possible_matches_for_edge[edge]:
                        if ctxt.options.enable_log:
                            ctxt.debug('possible match: %s', pm.describe(ctxt))
                        matchingstates = states.match_states_by_name(ctxt, pm.expr, pm.statenames)
                        if matchingstates:
                            if ctxt.options.enable_log:
                                ctxt.debug('matchingstates: %s' % stateset_to_str(matchingstates))
                                ctxt.debug('got match in states %s of %s at %s',
                                           stateset_to_str(matchingstates),
                                           pm.describe(ctxt),
                                           stmt)
                            for outcome in pm.outcomes:
                                for state in matchingstates:
                                    if ctxt.options.enable_log:
                                        ctxt.debug('applying outcome to %s => %s with %s',
                                                   pm.expr,
                                                   outcome,
                                                   states)
                                    effect = outcome.get_effect_for_state(ctxt, edge,
                                                                          pm.match, state)
                                    # Extract errors from the effect:
                                    for err in effect.errors:
                                        ctxt.errors_from_fixed_point.add(err)

class Context(object):
    # An sm.checker.Sm (do we need any other context?)

    # in context, with a mapping from its vars to gcc.VarDecl
    # (or ParmDecl) instances
    __slots__ = ('options',
                 'ch',
                 'sm',
                 'graph',
                 'statenames',

                 # A mapping from str (decl names) to Decl instances:
                 '_decls',

                 # The stateful decl, if any:
                 '_stateful_decl',

                 # A mapping from str (pattern names) to NamedPattern
                 # instances:
                 '_namedpatterns',

                 # All StateClause instance, in order:
                 '_stateclauses',

                 # Does any Python code call set_state()?
                 # (If so, we can't detect unreachable states)
                 '_uses_set_state',

                 '_indent',

                 # State instance for the default state
                 '_default_state',

                 'errors_from_fixed_point',

                 'python_locals',
                 'python_globals',

                 'allexprs',
                 'smexprs',

                 'facts_for_node',
                 'leaks_for_edge',
                 'possible_matches_for_edge',
                 'states_for_node',
                 'expgraph',
                 'facts_for_expnode',
                 '_errors',
                 )

    def __init__(self, ch, sm, graph, options):
        self.options = options

        self.ch = ch
        self.sm = sm
        self.graph = graph

        # The Context caches some information about the sm to help
        # process it efficiently:
        #
        #   all state names:
        self.statenames = list(sm.iter_statenames())

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

        # Set up self._decls and self._stateful_decl:
        for clause in sm.clauses:
            if isinstance(clause, Decl):
                self._decls[clause.name] = clause
                if clause.has_state:
                    self._stateful_decl = clause

        self._default_state = State(self.get_default_statename())

        reachable_statenames = set([self.get_default_statename()])

        # Set up the other above attributes:
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
                    if statename.endswith('*'):
                        continue
                    if statename not in reachable_statenames \
                            and not self._uses_set_state:
                        class UnreachableState(Exception):
                            def __init__(self, statename):
                                self.statename = statename
                            def __str__(self):
                                return str(self.statename)
                        raise UnreachableState(statename)

        self.errors_from_fixed_point = set()

        # Run any initial python code:
        self.python_locals = {}
        self.python_globals = {}
        for clause in sm.clauses:
            if isinstance(clause, PythonFragment):
                code = clause.get_code()
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
        if self.options.enable_timing:
            formattedmsg = msg % args
            sys.stderr.write('TIMING: %s: %s%s\n'
                             % (self.sm.name, self._get_indent(), formattedmsg))

    def log(self, msg, *args):
        # High-level logging
        if self.options.enable_log:
            formattedmsg = msg % args
            sys.stderr.write('LOG  : %s: %s%s\n'
                             % (self.sm.name, self._get_indent(), formattedmsg))

    def debug(self, msg, *args):
        # Lower-level logging
        if self.options.enable_debug:
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

    def emit_errors(self, solution):
        if self.options.dump_json:
            reporter = JsonReporter()
        else:
            reporter = StderrReporter()

        for err in sorted(self._errors):
            report = err.make_report(self, solution)
            if report:
                reporter.add(report)

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

    def get_default_statename(self):
        return '%s.start' % self._stateful_decl.name

    def get_default_state(self):
        return self._default_state

    def is_stateful_var(self, gccexpr):
        '''
        Is this gcc.Tree of a kind that has state according to the current sm?
        '''
        if isinstance(gccexpr, gcc.SsaName):
            if isinstance(gccexpr.type, gcc.PointerType):
                # TODO: the sm may impose further constraints
                return True

    def find_scopes(self):
        """
        Set up per-function dictionaries on the Context:

           * allexprs: the set of all tree expressions visible in that
                       function

           * smexprs: the subset of the above that match the stateful sm
                      expression type
        """
        self.allexprs = {}
        self.smexprs = {}
        for function in self.graph.get_functions():
            smexprs = set()
            allexprs = set()
            def add_to_scope(node):
                if isinstance(node, gcc.FunctionDecl):
                    return
                if isinstance(node, gcc.SsaName):
                    add_to_scope(node.var)

                if isinstance(node, (gcc.VarDecl, gcc.ParmDecl, gcc.ComponentRef)):
                    allexprs.add(node)
                    if self._stateful_decl.matched_by(node):
                        smexprs.add(node)

            for bb in function.cfg.basic_blocks:
                if bb.gimple:
                    for stmt in bb.gimple:
                        stmt.walk_tree(add_to_scope)
            self.allexprs[function] = allexprs
            self.smexprs[function] = smexprs

    def get_aliases(self, node, expr):
        facts = self.facts_for_node[node]
        if facts is not None:
            return facts.get_aliases(expr)
        else:
            return frozenset([expr])

    def solve(self, name):
        # Preprocessing phase: identify the scope of expressions within each
        # function
        with Timer(self, 'find_scopes'):
            self.find_scopes()

        # Preprocessing phase: gather simple per-node "facts", for use in
        # giving better names for temporaries, and for identifying the return
        # values of functions
        from sm.facts import Facts
        with Timer(self, 'sm.dataflow.fixed_point_solver(Facts)'):
            self.facts_for_node = sm.dataflow.fixed_point_solver(self, self.graph, Facts)

        # Preprocessing: set up possible_matches_for_edge dict:
        with Timer(self, 'find_possible_matches'):
            self.possible_matches_for_edge = {}
            for edge in self.graph.edges:
                self.possible_matches_for_edge[edge] = \
                    list(find_possible_matches(self, edge))

        # Find the all possible states reachable for each in-scope expr at
        # each node:
        with Timer(self, 'sm.dataflow.fixed_point_solver(StatesForNode)'):
            self.states_for_node = sm.dataflow.fixed_point_solver(self, self.graph, StatesForNode)

        if self.options.enable_timing:
            show_state_histogram(self)

        self.timing('len(graph.nodes): %i', len(self.graph.nodes))
        self.timing('len(graph.edges): %i', len(self.graph.edges))

        solution = sm.solution.Solution(self)

        # Generate self.errors_from_fixed_point:
        with Timer(self, 'generate_errors'):
            generate_errors_from_fixed_point(self)
        self.timing('len(self.errors_from_fixed_point): %i', len(self.errors_from_fixed_point))

        # Work-in-progress:
        # Build exploded graph:
        with Timer(self, 'build_exploded_graph'):
            from sm.expgraph import build_exploded_graph
            self.expgraph = build_exploded_graph(self)

            self.timing('len(expgraph.nodes): %i', len(self.expgraph.nodes))
            self.timing('len(expgraph.edges): %i', len(self.expgraph.edges))

            self.facts_for_expnode = None

            if self.options.show_exploded_graph:
                from gccutils import invoke_dot
                dot = self.expgraph.to_dot('exploded_graph', self)
                # Debug: view the exploded graph:
                if 0:
                    ctxt.debug(dot)
                invoke_dot(dot, 'exploded_graph')

            # Now prune the exploded graph, removing impossible paths:
            with Timer(self, 'pruning exploded graph'):
                from sm.facts import remove_impossible, Facts

                with Timer(self, 'sm.dataflow.fixed_point_solver(Facts for expgraph)'):
                    self.facts_for_expnode = \
                        sm.dataflow.fixed_point_solver(self,
                                                       self.expgraph,
                                                       Facts)

                # Remove nodes that the factfinder thinks are unreachable:
                with Timer(self, 'removing unreachable expnodes'):
                    pruned = 0
                    for expnode in list(self.expgraph.nodes):
                        if self.facts_for_expnode[expnode] is None:
                            pruned += self.expgraph.remove_node(expnode)
                    self.timing('pruned %i expnodes', pruned)

            if self.options.show_exploded_graph:
                from gccutils import invoke_dot
                dot = self.expgraph.to_dot('pruned_graph', self)
                invoke_dot(dot, 'pruned_graph')

        self._errors = list(self.errors_from_fixed_point)

        return solution

    #######################################################################
    # Utility methods for writing selftests
    #######################################################################
    def _is_within(self, node, within):
        if within:
            if node.function:
                if node.function.decl.name == within:
                    return True
            return False
        return True

    def _error_at_node(self, node):
        if node.stmt:
            if node.stmt.loc:
                gcc.set_location(node.stmt.loc)

    def get_nodes(self):
        query = Query(self.graph)
        return query

    def find_call_of(self, funcname, within=None):
        query = Query(self.graph).get_calls_of(funcname)
        if within:
            query = query.within(funcname=within)
        return query.first()

    def find_implementation_of(self, funcname):
        for fun in self.graph.stmtg_for_fun:
            if fun.decl.name == funcname:
                return self.graph.supernode_for_stmtnode[self.graph.stmtg_for_fun[fun].entry]
        raise ValueError('implementation of %s() not found' % funcname)

    def find_exit_of(self, funcname):
        for fun in self.graph.stmtg_for_fun:
            if fun.decl.name == funcname:
                return self.graph.supernode_for_stmtnode[self.graph.stmtg_for_fun[fun].exit]
        raise ValueError('implementation of %s() not found' % funcname)

    def find_comparison_against(self, exprcode, const, within=None):
        for node in self.graph.nodes:
            if not self._is_within(node, within):
                continue
            stmt = node.stmt
            if isinstance(stmt, gcc.GimpleCond):
                if stmt.exprcode == exprcode:
                    if isinstance(stmt.rhs, gcc.Constant):
                        if stmt.rhs.constant == const:
                            return node
        raise ValueError('comparison %s %s not found' % (exprcode, const))

    def get_inedge(self, node):
        if len(node.preds) > 1:
            self._error_at_node(node)
            raise ValueError('node %s has more than one inedge' % node)
        return list(node.preds)[0]

    def get_successor(self, node):
        if len(node.succs) > 1:
            self._error_at_node(node)
            raise ValueError('node %s has more than one successor' % node)
        return list(node.succs)[0].dstnode

    def get_true_successor(self, node):
        assert isinstance(node.stmt, gcc.GimpleCond)
        for edge in node.succs:
            if edge.true_value:
                return edge.dstnode
        self._error_at_node(node)
        raise ValueError('could not find true successor of node %s' % node)

    def get_intraprocedural_successor(self, node):
        """
        Given a callsite, get the next node within that function
        i.e. the second half of the callsite: wrapping the assignment of the
        return value to the LHS
        """
        assert isinstance(node, CallNode)
        assert isinstance(node.stmt, gcc.GimpleCall)
        for edge in node.succs:
            if isinstance(edge, CallToReturnSiteEdge):
                assert isinstance(edge.dstnode, ReturnNode)
                assert isinstance(edge.dstnode.stmt, gcc.GimpleCall)
                return edge.dstnode
        self._error_at_node(node)
        raise ValueError('could not find intraprocedural successor of node %s'
                         % node)

    def find_var(self, node, varname):
        for var in self.allexprs[node.function]:
            if isinstance(var, (gcc.VarDecl, gcc.ParmDecl)):
                if var.name == varname:
                    return var
        self._error_at_node(node)
        raise ValueError('variable %s not found' % varname)

    def get_expr_by_str(self, node, exprstr):
        for expr in self.allexprs[node.function]:
            if str(expr) == exprstr:
                return expr
        self._error_at_node(node)
        raise ValueError('expression %s not found' % exprstr)

    def assert_fact(self, node, lhs, op, rhs):
        from sm.facts import Fact
        if isinstance(lhs, str):
            lhs = self.get_expr_by_str(node, lhs)
        expectedfact = Fact(lhs, op, rhs)
        actualfacts = self.facts_for_node[node]
        if expectedfact not in actualfacts.set_:
            self._error_at_node(node)
            raise ValueError('%s not in %s' % (expectedfact, actualfacts))

    def assert_no_facts(self, node):
        actualfacts = self.facts_for_node[node]
        if actualfacts.set_:
            raise ValueError('unexpectedly found facts: %s' % (actualfacts, ))

    def assert_not_fact(self, node, lhs, op, rhs):
        from sm.facts import Fact
        if isinstance(lhs, str):
            lhs = self.get_expr_by_str(node, lhs)
        expectedfact = Fact(lhs, op, rhs)
        actualfacts = self.facts_for_node[node]
        if expectedfact in actualfacts.set_:
            self._error_at_node(node)
            raise ValueError('%s unexpectedly within %s' % (expectedfact, actualfacts))

    def assert_states_for_expr(self, node, expr, expectedstates):
        expr = simplify(expr)
        actualstates = self.states_for_node[node].get_states_for_expr(self, expr)
        if actualstates != expectedstates:
            self._error_at_node(node)
            raise ValueError('wrong states for %s at %r: expected %s but got %s'
                             % (expr,
                                str(node),
                                stateset_to_str(expectedstates),
                                stateset_to_str(actualstates)))

    def assert_states_for_varname(self, node, varname, expectedstates):
        var = self.find_var(node, varname)
        self.assert_states_for_expr(node, var, expectedstates)

    def assert_statenames_for_expr(self, node, expr, expectedstatenames):
        expectedstates = set([State(name)
                              for name in expectedstatenames])
        self.assert_states_for_expr(node, expr, expectedstates)

    def assert_statenames_for_varname(self, node, varname, expectedstatenames):
        var = self.find_var(node, varname)
        self.assert_statenames_for_expr(node, var, expectedstatenames)

    def assert_error_is_impossible(self, err, solution):
        stateful_gccvar = err.match.get_stateful_gccvar(self)
        equivcls = self.get_aliases(err.srcnode, stateful_gccvar)
        path = solution.get_shortest_path_to(err.srcnode,
                                             equivcls,
                                             err.state)
        if path is not None:
            raise ValueError('expected %r to be impossible due to there'
                             ' being no possible path to %s:%s at %s\n'
                             'but found path: %s'
                             % (err.msg, equivcls, err.state, err.srcnode,
                                path))

    def assert_edge_matches_pattern(self, edge, patternsrc):
        for pm in self.possible_matches_for_edge[edge]:
            if patternsrc == str(pm.match.pattern):
                # We have a match
                return pm
        srcs = [str(pm.match.pattern)
                for pm in edge.possible_matches]
        raise ValueError('pattern %r not found in %s'
                         % (patternsrc, srcs))

def solve(ctxt, name, selftest):
    ctxt.log('running %s', ctxt.sm.name)
    ctxt.log('len(ctxt.graph.nodes): %i', len(ctxt.graph.nodes))
    ctxt.log('len(ctxt.graph.edges): %i', len(ctxt.graph.edges))
    with Timer(ctxt, 'generating solution'):
        solution = ctxt.solve(name)
    if ctxt.options.dump_solution:
        solution.dump(sys.stderr)
    if ctxt.options.show_solution:
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
