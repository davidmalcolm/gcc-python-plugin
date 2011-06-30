#   Copyright 2011 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2011 Red Hat, Inc.
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
import sys
from gccutils import get_src_for_loc
from collections import OrderedDict
from PyArg_ParseTuple import log

class AbstractValue:
    def __init__(self, gcctype, stmt):
        self.gcctype = gcctype
        self.stmt = stmt

    def __str__(self):
        return '%s from %s' % (self.gcctype, self.stmt)

    def __repr__(self):
        return 'AbstractValue(%r, %r)' % (self.gcctype, self.stmt)

class PredictedError(Exception):
    pass

class InvalidlyNullParameter(PredictedError):
    # Use this when we can predict that a function is called with NULL as an
    # argument for an argument that must not be NULL
    def __init__(self, fnname, paramidx, nullvalue):
        self.fnname = fnname
        self.paramidx = paramidx # starts at 1
        self.nullvalue = nullvalue

    def __str__(self):
        return ('%s can be called with NULL as parameter %i; %s'
                % (self.fnname, self.paramidx, self.nullvalue))


class UnknownValue(AbstractValue):
    def __str__(self):
        return 'unknown %s from %s' % (self.gcctype, self.stmt)

    def __repr__(self):
        return 'UnknownValue(%r, %r)' % (self.gcctype, self.stmt)

class PtrValue:
    """An abstract (PyObject*) value"""
    def __init__(self, nonnull):
        self.nonnull = nonnull

class NullPtrValue(PtrValue):
    def __init__(self, stmt=None):
        PtrValue.__init__(self, False)
        self.stmt = stmt

    def __str__(self):
        if self.stmt:
            return 'NULL value from %s' % get_src_for_loc(self.stmt.loc)
        else:
            return 'NULL'

    def __repr__(self):
        return 'NullPtrValue()'

def describe_stmt(stmt):
    if isinstance(stmt, gcc.GimpleCall):
        if isinstance(stmt.fn.operand, gcc.FunctionDecl):
            fnname = stmt.fn.operand.name
            return 'call to %s at line %i' % (fnname, stmt.loc.line)
    else:
        return str(stmt.loc)

class NonNullPtrValue(PtrValue):
    def __init__(self, refdelta, stmt):
        PtrValue.__init__(self, True)
        self.refdelta = refdelta
        self.stmt = stmt

    def __str__(self):
        return ('non-NULL(%s refs) acquired at %s'
                % (self.refdelta, describe_stmt(self.stmt)))

    def __repr__(self):
        return 'NonNullPtrValue(%i)' % self.refdelta

class PtrToGlobal(NonNullPtrValue):
    def __init__(self, refdelta, stmt, name):
        NonNullPtrValue.__init__(self, refdelta, stmt)
        self.name = name

    def __str__(self):
        if self.stmt:
            return ('&%s acquired at %s'
                    % (self.name, describe_stmt(self.stmt)))
        else:
            return ('&%s' % self.name)

class Location:
    """A location within a CFG: a gcc.BasicBlock together with an index into
    the gimple list.  (We don't support SSA passes)"""
    def __init__(self, bb, idx):
        self.bb = bb
        self.idx = idx

    def __str__(self):
        stmt = self.get_stmt()
        return ('block %i stmt:%i : %20r : %s'
                % (self.bb.index, self.idx, stmt, stmt))

    def next_locs(self):
        """Get a list of Location instances, for what can happen next"""
        if self.bb.gimple and len(self.bb.gimple) > self.idx + 1:
            # Next gimple statement:
            return [Location(self.bb, self.idx + 1)]
        else:
            # At end of gimple statements: successor BBs:
            return [Location.get_block_start(outedge.dest) for outedge in self.bb.succs]

    def next_loc(self):
        """Get the next Location, for when it's unique"""
        if self.bb.gimple:
            if len(self.bb.gimple) > self.idx + 1:
                # Next gimple statement:
                return Location(self.bb, self.idx + 1)
            else:
                assert len(self.bb.succs) == 1
                return Location.get_block_start(self.bb.succs[0].dest)

    @classmethod
    def get_block_start(cls, bb):
        # Don't bother iterating through phi_nodes if there aren't any:
        return Location(bb, 0)

    def get_stmt(self):
        if self.bb.gimple:
            return self.bb.gimple[self.idx]
        else:
            return None

class State:
    """A Location with a dict of vars and values"""
    def __init__(self, loc, data):
        self.loc = loc
        self.data = data

    def copy(self):
        return self.__class__(loc, self.data.copy())

    def __str__(self):
        return '%s: %s%s' % (self.data, self.loc, self._extra())

    def __repr__(self):
        return '%s: %s%s' % (self.data, self.loc, self._extra())

    def log(self, logger, indent):
        logger('data: %s' % (self.data, ), indent)
        logger('extra: %s' % (self._extra(), ), indent)

        # FIXME: derived class/extra:
        self.resources.log(logger, indent)

        logger('loc: %s' % self.loc, indent)
        if self.loc.get_stmt():
            logger('%s' % self.loc.get_stmt().loc, indent + 1)

    def get_key_for_lvalue(self, lvalue):
        return str(lvalue) # FIXME

    def make_assignment(self, lvalue, value, desc):
        if desc:
            assert isinstance(desc, str)
        new = self.copy()
        new.loc = self.loc.next_loc()
        if lvalue:
            assert isinstance(lvalue, gcc.VarDecl) # for now
            key = self.get_key_for_lvalue(lvalue)
            new.data[key] = value
        return Transition(new, desc)

    def update_loc(self, newloc):
        new = self.copy()
        new.loc = newloc
        return new

    def use_next_loc(self):
        newloc = self.loc.next_loc()
        return self.update_loc(newloc)

class Transition:
    def __init__(self, nextstate, desc):
        self.nextstate = nextstate
        self.desc = desc

    def __repr__(self):
        return 'Transition(%r, %r)' % (self.nextstate, self.desc)

class Trace:
    """A sequence of State"""
    def __init__(self):
        self.states = []
        self.err = None

    def add(self, state):
        assert isinstance(state, State)
        self.states.append(state)
        return self

    def add_error(self, err):
        self.err = err

    def copy(self):
        t = Trace()
        t.states = self.states[:]
        t.err = self.err # FIXME: should this be a copy?
        return t

    def log(self, logger, name, indent):
        logger('%s:' % name, indent)
        for i, state in enumerate(self.states):
            logger('%i:' % i, indent + 1)
            state.log(logger, indent + 2)
        if self.err:
            logger('  Trace ended with error: %s' % self.err, indent + 1)

    def get_last_stmt(self):
        return self.states[-1].loc.get_stmt()

    def return_value(self):
        last_stmt = self.get_last_stmt()
        if isinstance(last_stmt, gcc.GimpleReturn):
            return self.states[-1].eval_expr(last_stmt.retval)
        else:
            return None

    def final_references(self):
        return self.states[-1].owned_refs

def true_edge(bb):
    for e in bb.succs:
        if e.true_value:
            return e

def false_edge(bb):
    for e in bb.succs:
        if e.false_value:
            return e

class Resources:
    # Resource tracking for a state
    def __init__(self):
        # Resources that we've acquired:
        self._acquisitions = []

        # Resources that we've released:
        self._releases = []

    def copy(self):
        new = Resources()
        new._acquisitions = self._acquisitions[:]
        new._releases = self._releases[:]
        return new

    def acquire(self, resource):
        self._acquisitions.append(resource)

    def release(self, resource):
        self._releases.append(resource)

    def log(self, logger, indent):
        logger('resources:', indent)
        logger('acquisitions: %s' % self._acquisitions, indent + 1)
        logger('releases: %s' % self._releases, indent + 1)

def iter_traces(fun, stateclass, prefix=None):
    # Traverse the tree of traces of program state
    # FIXME: this code can't cope with loops yet
    log('iter_traces(%r, %r, %r)' % (fun, stateclass, prefix))
    if prefix is None:
        prefix = Trace()
        curstate = stateclass(Location.get_block_start(fun.cfg.entry),
                              OrderedDict(),
                              [],
                              Resources())
    else:
        curstate = prefix.states[-1]

    # We need the prevstate to handle Phi nodes
    if len(prefix.states) > 1:
        prevstate = prefix.states[-2]
    else:
        prevstate = None

    prefix.log(log, 'PREFIX', 1)
    log('  %s:%s' % (fun.decl.name, curstate.loc))
    try:
        transitions = curstate.get_transitions(prevstate)
        assert isinstance(transitions, list)
    except PredictedError, err:
        # We're at a terminating state:
        err.loc = prefix.get_last_stmt().loc
        trace_with_err = prefix.copy()
        trace_with_err.add_error(err)
        trace_with_err.log(log, 'FINISHED TRACE WITH ERROR: %s' % err, 1)
        return [trace_with_err]

    log('transitions: %s' % transitions, 2)

    if len(transitions) > 0:
        result = []
        for transition in transitions:
            # Recurse:
            for trace in iter_traces(fun, stateclass, prefix.copy().add(transition.nextstate)):
                result.append(trace)
        return result
    else:
        # We're at a terminating state:
        prefix.log(log, 'FINISHED TRACE', 1)
        return [prefix]

class StateEdge:
    def __init__(self, src, dest, transition):
        assert isinstance(src, State)
        assert isinstance(dest, State)
        assert isinstance(transition, Transition)
        self.src = src
        self.dest = dest
        self.transition = transition

class StateGraph:
    """
    A graph of states, representing the various routes through a function,
    tracking state.

    For now, we give up when we encounter a loop, as an easy way to ensure
    termination of the analysis
    """
    def __init__(self, fun, logger, stateclass):
        assert isinstance(fun, gcc.Function)
        self.fun = fun
        self.states = []
        self.edges = []
        self.stateclass = stateclass

        logger('StateGraph.__init__(%r)' % fun)

        # Recursively gather states:
        initial = stateclass(Location.get_block_start(fun.cfg.entry),
                             OrderedDict(),
                             [],
                             Resources())
        self.states.append(initial)
        self._gather_states(initial, None, logger)

    def _gather_states(self, curstate, prevstate, logger):
        logger('  %s:%s' % (self.fun.decl.name, curstate.loc))
        try:
            transitions = curstate.get_transitions(prevstate)
            print transitions
            assert isinstance(transitions, list)
        except PredictedError, err:
            # We're at a terminating state:
            raise "foo" # FIXME
            err.loc = prefix.get_last_stmt().loc
            trace_with_err = prefix.copy()
            trace_with_err.add_error(err)
            trace_with_err.log(log, 'FINISHED TRACE WITH ERROR: %s' % err, 1)
            return [trace_with_err]

        logger('transitions: %s' % transitions, 2)

        if len(transitions) > 0:
            for transition in transitions:
                # FIXME: what about loops???
                assert isinstance(transition, Transition)
                self.states.append(transition.nextstate)
                self.edges.append(StateEdge(curstate, transition.nextstate, transition))

                # Recurse:
                self._gather_states(transition.nextstate, curstate, logger)
        else:
            # We're at a terminating state:
            logger('FINISHED TRACE')

def extra_text(msg, indent):
    sys.stderr.write('%s%s\n' % ('  ' * indent, msg))

def describe_trace(trace):
    # Print more details about the path through the function that
    # leads to the error:
    awaiting_target = None
    for j in range(len(trace.states)-1):
        state = trace.states[j]
        nextstate = trace.states[j+1]
        stmt = state.loc.get_stmt()
        next_stmt = nextstate.loc.get_stmt()
        if state.loc.bb != nextstate.loc.bb:
            if stmt:
                extra_text('%s: taking %s path at %s'
                           % (stmt.loc,
                              nextstate.prior_bool,
                              get_src_for_loc(stmt.loc)), 1)
            first_loc_in_next_bb = get_first_loc_in_block(nextstate.loc.bb)
            if first_loc_in_next_bb:
                        extra_text('%s: reaching here %s'
                                   % (first_loc_in_next_bb,
                                      get_src_for_loc(first_loc_in_next_bb)),
                                   2)

