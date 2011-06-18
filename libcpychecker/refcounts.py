# Attempt to check that C code is implementing CPython's reference-counting
# rules.  See:
#   http://docs.python.org/c-api/intro.html#reference-counts
# for a description of how such code is meant to be written

import sys
import gcc

from gccutils import cfg_to_dot, invoke_dot, get_src_for_loc

from absinterp import *
from PyArg_ParseTuple import log

def stmt_is_assignment_to_count(stmt):
    if hasattr(stmt, 'lhs'):
        if stmt.lhs:
            if isinstance(stmt.lhs, gcc.ComponentRef):
                # print 'stmt.lhs.target: %s' % stmt.lhs.target
                # print 'stmt.lhs.target.type: %s' % stmt.lhs.target.type
                # (presumably we need to filter these to structs that are
                # PyObject, or subclasses)
                if stmt.lhs.field.name == 'ob_refcnt':
                    return True

def type_is_pyobjptr(t):
    assert t is None or isinstance(t, gcc.Type)
    if str(t) == 'struct PyObject *':
        return True

def stmt_is_assignment_to_objptr(stmt):
    if hasattr(stmt, 'lhs'):
        if stmt.lhs:
            if type_is_pyobjptr(stmt.lhs.type):
                return True

def stmt_is_return_of_objptr(stmt):
    if isinstance(stmt, gcc.GimpleReturn):
        if stmt.retval:
            if type_is_pyobjptr(stmt.retval.type):
                return True

class Location:
    """A location within a CFG: a gcc.BasicBlock together with an index into
    either the gimple list, or the phi_nodes list"""
    def __init__(self, bb, idx, within_phi=False):
        self.bb = bb
        self.idx = idx
        self.within_phi = within_phi

    def __str__(self):
        stmt = self.get_stmt()
        if self.within_phi:
            kind = '   phi'
        else:
            kind = 'gimple'
        return ('block %i  %s[%i]: %20r : %s'
                % (self.bb.index, kind, self.idx, stmt, stmt))

    def next_locs(self):
        """Get a list of Location instances, for what can happen next"""
        if self.within_phi:
            if self.bb.phi_nodes and len(self.bb.phi_nodes) > self.idx + 1:
                # Next phi node:
                return [Location(self.bb, self.idx + 1, self.within_phi)]
            else:
                # At end of phi nodes; start the gimple statements
                return [Location(self.bb, 0, False)]
        else:
            if self.bb.gimple and len(self.bb.gimple) > self.idx + 1:
                # Next gimple statement:
                return [Location(self.bb, self.idx + 1, self.within_phi)]
            else:
                # At end of gimple statements: successor BBs:
                return [Location.get_block_start(outedge.dest) for outedge in self.bb.succs]

    def next_loc(self):
        """Get the next Location, for when it's unique"""
        if self.within_phi:
            if self.bb.phi_nodes and len(self.bb.phi_nodes) > self.idx + 1:
                # Next phi node:
                return Location(self.bb, self.idx + 1, self.within_phi)
            else:
                # At end of phi nodes; start the gimple statements
                return Location(self.bb, 0, False)
        else:
            if self.bb.gimple:
                if len(self.bb.gimple) > self.idx + 1:
                    # Next gimple statement:
                    return Location(self.bb, self.idx + 1, self.within_phi)
                else:
                    assert len(self.bb.succs) == 1
                    return Location.get_block_start(self.bb.succs[0].dest)

    @classmethod
    def get_block_start(cls, bb):
        # Don't bother iterating through phi_nodes if there aren't any:
        if bb.phi_nodes:
            return Location(bb, 0, True)
        else:
            return Location(bb, 0, False)

    def get_stmt(self):
        if self.within_phi:
            if self.bb.phi_nodes:
                return self.bb.phi_nodes[self.idx]
            else:
                return None
        else:
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

    def make_assignment(self, key, value):
        new = self.copy()
        new.loc = self.loc.next_loc()
        new.data[str(key)] = value
        return new

    def update_loc(self, newloc):
        new = self.copy()
        new.loc = newloc
        return new

    def use_next_loc(self):
        newloc = self.loc.next_loc()
        return self.update_loc(newloc)

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


class MyState(State):
    def __init__(self, loc, data, owned_refs, resources):
        State.__init__(self, loc, data)
        self.owned_refs = owned_refs
        self.resources = resources

    def copy(self):
        return self.__class__(self.loc, self.data.copy(), self.owned_refs[:],
                              self.resources.copy())

    def _extra(self):
        return ' %s' % self.owned_refs

    def acquire(self, resource):
        self.resources.acquire(resource)

    def release(self, resource):
        self.resources.release(resource)

    def make_assignment(self, key, value, additional_ptr=None):
        newstate = State.make_assignment(self, key, value)
        if additional_ptr:
            newstate.owned_refs.append(additional_ptr)
        return newstate

    def next_states(self, oldstate):
        # Return a list of State instances, based on input State
        stmt = self.loc.get_stmt()
        if stmt:
            return self._next_states_for_stmt(stmt, oldstate)
        else:
            result = []
            for loc in self.loc.next_locs():
                newstate = self.copy()
                newstate.loc = loc
                result.append(newstate)
            log('result: %s' % result)
            return result

    def _next_states_for_stmt(self, stmt, oldstate):
        log('_next_states_for_stmt: %r %s' % (stmt, stmt), 2)
        log('dir(stmt): %s' % dir(stmt), 3)
        if isinstance(stmt, gcc.GimpleCall):
            return self._next_states_for_GimpleCall(stmt)
        elif isinstance(stmt, (gcc.GimpleDebug, gcc.GimpleLabel)):
            return [self.use_next_loc()]
        elif isinstance(stmt, gcc.GimpleCond):
            return self._next_states_for_GimpleCond(stmt)
        elif isinstance(stmt, gcc.GimplePhi):
            return self._next_states_for_GimplePhi(stmt, oldstate)
        elif isinstance(stmt, gcc.GimpleReturn):
            return []
        elif isinstance(stmt, gcc.GimpleAssign):
            return self._next_states_for_GimpleAssign(stmt)
        else:
            raise "foo"

    def eval_expr(self, expr):
        if isinstance(expr, gcc.IntegerCst):
            return expr.constant
        if isinstance(expr, gcc.SsaName):
            if str(expr) in self.data:
                return self.data[str(expr)]
            else:
                return UnknownValue()
        if isinstance(expr, gcc.AddrExpr):
            #log(dir(expr))
            #log(expr.operand)
            # Handle Py_None, which is a #define of (&_Py_NoneStruct)
            if isinstance(expr.operand, gcc.VarDecl):
                if expr.operand.name == '_Py_NoneStruct':
                    # FIXME: do we need a stmt?
                    return PtrToGlobal(1, None, expr.operand.name)
        return UnknownValue()

    def _next_states_for_GimpleCall(self, stmt):
        log('stmt.lhs: %s %r' % (stmt.lhs, stmt.lhs), 3)
        log('stmt.fn: %s %r' % (stmt.fn, stmt.fn), 3)
        log('dir(stmt.fn): %s' % dir(stmt.fn), 4)
        log('stmt.fn.operand: %s' % stmt.fn.operand, 4)
        if isinstance(stmt.fn.operand, gcc.FunctionDecl):
            log('dir(stmt.fn.operand): %s' % dir(stmt.fn.operand), 4)
            log('stmt.fn.operand.name: %r' % stmt.fn.operand.name, 4)
            fnname = stmt.fn.operand.name
            # Function returning new references:
            if fnname in ('PyList_New', 'PyLong_FromLong'):
                nonnull = NonNullPtrValue(1, stmt)
                return [self.make_assignment(stmt.lhs, nonnull, nonnull),
                        self.make_assignment(stmt.lhs, NullPtrValue())]
            # Function returning borrowed references:
            elif fnname in ('Py_InitModule4_64',):
                return [self.make_assignment(stmt.lhs, NonNullPtrValue(1, stmt)),
                        self.make_assignment(stmt.lhs, NullPtrValue())]
            #elif fnname in ('PyList_SetItem'):
            #    pass
            else:
                from libcpychecker.c_stdio import c_stdio_functions, handle_c_stdio_function

                if fnname in c_stdio_functions:
                    return handle_c_stdio_function(self, fnname, stmt)

                raise "don't know how to handle that function"
        log('stmt.args: %s %r' % (stmt.args, stmt.args), 3)
        for i, arg in enumerate(stmt.args):
            log('args[%i]: %s %r' % (i, arg, arg), 4)

    def _next_states_for_GimpleCond(self, stmt):
        def make_nextstate_for_true(stmt):
            e = true_edge(self.loc.bb)
            assert e
            nextstate = self.update_loc(Location.get_block_start(e.dest))
            nextstate.prior_bool = True
            return nextstate

        def make_nextstate_for_false(stmt):
            e = false_edge(self.loc.bb)
            assert e
            nextstate = self.update_loc(Location.get_block_start(e.dest))
            nextstate.prior_bool = False
            return nextstate

        log('stmt.exprcode: %s' % stmt.exprcode, 4)
        log('stmt.exprtype: %s' % stmt.exprtype, 4)
        log('stmt.lhs: %r %s' % (stmt.lhs, stmt.lhs), 4)
        log('stmt.rhs: %r %s' % (stmt.rhs, stmt.rhs), 4)
        log('dir(stmt.lhs): %s' % dir(stmt.lhs), 5)
        log('dir(stmt.rhs): %s' % dir(stmt.rhs), 5)
        boolval = self.eval_condition(stmt)
        if boolval is True:
            log('taking True edge', 2)
            nextstate = make_nextstate_for_true(stmt)
            return [nextstate]
        elif boolval is False:
            log('taking False edge', 2)
            nextstate = make_nextstate_for_false(stmt)
            return [nextstate]
        else:
            assert isinstance(boolval, UnknownValue)
            # We don't have enough information; both branches are possible:
            return [make_nextstate_for_true(stmt),
                    make_nextstate_for_false(stmt)]

    def _next_states_for_GimplePhi(self, stmt, oldstate):
        log('stmt: %s' % stmt)
        log('stmt.lhs: %s' % stmt.lhs)
        log('stmt.args: %s' % stmt.args)
        # Choose the correct new value, based on the edge we came in on
        for expr, edge in stmt.args:
            if edge.src == oldstate.loc.bb:
                # Update the LHS appropriately:
                next = self.use_next_loc()
                next.data[str(stmt.lhs)] = self.eval_expr(expr)
                return [next]
        raise AnalysisError('incoming edge not found')

    def eval_condition(self, stmt):
        lhs = self.eval_expr(stmt.lhs)
        rhs = self.eval_expr(stmt.rhs)
        log('eval of lhs: %r' % lhs)
        log('eval of rhs: %r' % rhs)
        if stmt.exprcode == gcc.EqExpr:
            if isinstance(lhs, NonNullPtrValue) and rhs == 0:
                return False
            if isinstance(lhs, NullPtrValue) and rhs == 0:
                return True
        return UnknownValue()

    def _next_states_for_GimpleAssign(self, stmt):
        log('stmt.lhs: %r %s' % (stmt.lhs, stmt.lhs))
        log('stmt.rhs: %r %s' % (stmt.rhs, stmt.rhs))

        nextstate = self.use_next_loc()
        if isinstance(stmt.lhs, gcc.MemRef):
            value = self.eval_expr(stmt.rhs[0])
            log('value: %s %r' % (value, value))
            # We're writing a value to memory; if it's a PyObject*
            # then we're surrending a reference on it:
            if value in nextstate.owned_refs:
                log('removing ownership of %s' % value)
                nextstate.owned_refs.remove(value)
        return [nextstate] # for now

def iter_traces(fun, prefix=None):
    # Traverse the tree of traces of program state
    # FIXME: this code can't cope with loops yet
    log('iter_traces(%r, %r)' % (fun, prefix))
    if prefix is None:
        prefix = Trace()
        curstate = MyState(Location.get_block_start(fun.cfg.entry),
                           {},
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
        nextstates = curstate.next_states(prevstate)
        assert isinstance(nextstates, list)
    except PredictedError, err:
        # We're at a terminating state:
        err.loc = prefix.get_last_stmt().loc
        trace_with_err = prefix.copy()
        trace_with_err.add_error(err)
        trace_with_err.log(log, 'FINISHED TRACE WITH ERROR: %s' % err, 1)
        return [trace_with_err]

    log('states: %s' % nextstates, 2)

    if len(nextstates) > 0:
        result = []
        for nextstate in nextstates:
            # Recurse:
            for trace in iter_traces(fun, prefix.copy().add(nextstate)):
                result.append(trace)
        return result
    else:
        # We're at a terminating state:
        prefix.log(log, 'FINISHED TRACE', 1)
        return [prefix]

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

def check_refcounts(fun, show_traces):
    # Abstract interpretation:
    # Walk the CFG, gathering the information we're interested in

    traces = iter_traces(fun)
    if show_traces:
        traces = list(traces)
        for i, trace in enumerate(traces):
            def my_logger(item, indent=0):
                sys.stdout.write('%s%s\n' % ('  ' * indent, item))
            trace.log(my_logger, 'TRACE %i' % i, 0)

    for i, trace in enumerate(traces):
        trace.log(log, 'TRACE %i' % i, 0)
        if trace.err:
            # This trace bails early with a fatal error; it probably doesn't
            # have a return value
            log('trace.err: %s %r' % (trace.err, trace.err))
            gcc.permerror(trace.err.loc,
                          str(trace.err))
            describe_trace(trace)
            # FIXME: in our example this ought to mention where the values came from
            continue
        # Otherwise, the trace proceeds normally
        return_value = trace.return_value()
        log('trace.return_value(): %s' % trace.return_value())
        # Ideally, we should "own" exactly one reference, and it should be
        # the return value.  Anything else is an error (and there are other
        # kinds of error...)
        final_refs = trace.final_references()
        if return_value in final_refs:
            final_refs.remove(return_value)
        else:
            if isinstance(return_value, NonNullPtrValue):
                gcc.permerror(trace.get_last_stmt().loc,
                              ('return of PyObject* (%s)'
                               ' without Py_INCREF()'
                               % return_value))
                if str(return_value) == '&_Py_NoneStruct':
                    extra_text('%s: suggest use of "Py_RETURN_NONE;"'
                               % trace.get_last_stmt().loc, 1)

        # Anything remaining is a leak:
        if len(final_refs) > 0:
            for ref in final_refs:
                gcc.permerror(ref.stmt.loc,
                              'leak of PyObject* reference acquired at %s'
                              % describe_stmt(ref.stmt))
                log('ref: %s' % ref, 1)
                # Print more details about the path through the function that
                # leads to the error:
                for j in range(len(trace.states)):
                    state = trace.states[j]
                    stmt = state.loc.get_stmt()
                    if isinstance(stmt, gcc.GimpleCond):
                        nextstate = trace.states[j+1]
                        next_stmt = nextstate.loc.get_stmt()
                        extra_text('%s: taking %s path at %s'
                                   % (stmt.loc,
                                      nextstate.prior_bool,
                                      get_src_for_loc(stmt.loc)), 1)
                        #log(next_stmt, 3)
                        # FIXME: phi nodes don't have locations:
                        if hasattr(next_stmt, 'loc'):
                            if next_stmt.loc:
                                extra_text('%s: reaching here %s'
                                           % (next_stmt.loc,
                                              get_src_for_loc(next_stmt.loc)),
                                           2)
                extra_text('%s: returning %s'
                           % (ref.stmt.loc, return_value),
                           1) # FIXME: loc is wrong

    if 0:
        dot = cfg_to_dot(fun.cfg)
        invoke_dot(dot)


