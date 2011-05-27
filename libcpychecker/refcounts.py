# Attempt to check that C code is implementing CPython's reference-counting
# rules.  See:
#   http://docs.python.org/c-api/intro.html#reference-counts
# for a description of how such code is meant to be written

import gcc

from gccutils import cfg_to_dot, invoke_dot

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

class Operations:
    def __init__(self, fun):
        self.fun = fun

        self.assigns_to_count = []
        self.assigns_to_objptr = []
        self.returns_of_objptr = []

        for bb in fun.cfg.basic_blocks:
            if isinstance(bb.gimple, list):
                for stmt in bb.gimple:
                    # log(stmt)
                    # log(repr(stmt))
                    if stmt_is_assignment_to_count(stmt):
                        log('%s: assignment to count: %s' % (stmt.loc, stmt))
                        self.assigns_to_count.append(stmt)
                    if stmt_is_assignment_to_objptr(stmt):
                        log('%s: assignment to objptr: %s' % (stmt.loc, stmt))
                        self.assigns_to_objptr.append(stmt)
                    if stmt_is_return_of_objptr(stmt):
                        log('%s: return of objptr: %s' % (stmt.loc, stmt))
                        log('stmt.retval: %s %r' % (stmt.retval, stmt.retval))
                        if isinstance(stmt.retval, gcc.SsaName):
                            log('dir(stmt.retval): %s' % dir(stmt.retval))
                            log('stmt.retval.def_stmt: %s %r' % (stmt.retval.def_stmt, stmt.retval.def_stmt))
                            log('dir(stmt.retval.def_stmt): %s' % dir(stmt.retval.def_stmt))
                            if isinstance(stmt.retval.def_stmt, gcc.GimpleCall):
                                log('stmt.retval.def_stmt.fn: %s %r' % (stmt.retval.def_stmt.fn, stmt.retval.def_stmt.fn))
                                log('stmt.retval.def_stmt.args: %s %r' % (stmt.retval.def_stmt.args, stmt.retval.def_stmt.args))
                                for i, arg in enumerate(stmt.retval.def_stmt.args):
                                    log('  args[%i]: %s %r' % (i, arg, arg))
                            log('stmt.retval.def_stmt.rhs: %s' % stmt.retval.def_stmt.rhs)
                            log('stmt.retval.var: %s' % stmt.retval.var)
                            log('dir(stmt.retval.var): %s' % dir(stmt.retval.var))
                        self.returns_of_objptr.append(stmt)

        log(self.returns_of_objptr)
        log(self.assigns_to_count)

        # Highly-simplistic first pass at refcount tracking:
        if len(self.returns_of_objptr) > 0:
            if self.assigns_to_count == []:
                # We're returning a PyObject *, but not modifying a refcount
                # FIXME: if we're calling various APIs, this would affect the count
                # Otherwise, this is a bug:
                for r in self.returns_of_objptr:
                    if r.loc:
                        gcc.permerror(r.loc, 'return of PyObject* without Py_INCREF()')


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

class UnknownValue:
    pass

class PtrValue:
    """An abstract (PyObject*) value"""
    def __init__(self, nonnull):
        self.nonnull = nonnull

class NullPtrValue(PtrValue):
    def __init__(self):
        PtrValue.__init__(self, False)

    def __str__(self):
        return 'NULL'

    def __repr__(self):
        return 'NullPtrValue()'

class NonNullPtrValue(PtrValue):
    def __init__(self, refdelta):
        PtrValue.__init__(self, True)
        self.refdelta = refdelta

    def __str__(self):
        return 'non-NULL(%s refs)' % self.refdelta

    def __repr__(self):
        return 'NonNullPtrValue(%i)' % self.refdelta

class State:
    """A Location with a dict of vars and values"""
    def __init__(self, loc, data):
        self.loc = loc
        self.data = data

    def __str__(self):
        return '%s: %s' % (self.loc, self.data)

    def __repr__(self):
        return '%s: %s' % (self.loc, self.data)

    def make_assignment(self, key, value):
        new = self.__class__(self.loc.next_loc(), self.data.copy())
        new.data[str(key)] = value
        return new

    def update_loc(self, newloc):
        return self.__class__(newloc, self.data.copy())

    def use_next_loc(self):
        newloc = self.loc.next_loc()
        return self.__class__(newloc, self.data.copy())

class Trace:
    """A sequence of State"""
    def __init__(self):
        self.states = []

    def add(self, state):
        assert isinstance(state, State)
        self.states.append(state)
        return self

    def copy(self):
        t = Trace()
        t.states = self.states[:]
        return t

    def log(self, name, indent):
        log('%s:' % name, indent)
        for i, state in enumerate(self.states):
            log('  %i: %s' % (i, state), indent + 1 )

def true_edge(bb):
    for e in bb.succs:
        if e.true_value:
            return e

def false_edge(bb):
    for e in bb.succs:
        if e.false_value:
            return e

class MyState(State):
    def next_states(self):
        # Return a list of State instances, based on input State
        stmt = self.loc.get_stmt()
        if stmt:
            return self._next_states_for_stmt(stmt)
        else:
            return [MyState(loc, self.data.copy())
                    for loc in self.loc.next_locs()]

    def _next_states_for_stmt(self, stmt):
        log('_next_states_for_stmt: %r %s' % (stmt, stmt), 2)
        log('dir(stmt): %s' % dir(stmt), 3)
        if isinstance(stmt, gcc.GimpleCall):
            return self._next_states_for_GimpleCall(stmt)
        elif isinstance(stmt, gcc.GimpleDebug):
            return [self.use_next_loc()]
        elif isinstance(stmt, gcc.GimpleCond):
            return self._next_states_for_GimpleCond(stmt)
        elif isinstance(stmt, gcc.GimplePhi):
            return [self.use_next_loc()]
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
            if fnname in ('PyList_New', 'PyLong_FromLong'):
                return [self.make_assignment(stmt.lhs, NonNullPtrValue(1)),
                        self.make_assignment(stmt.lhs, NullPtrValue())]
            #elif fnname in ('PyList_SetItem'):
            #    pass
            else:
                raise "don't know how to handle that function"
        log('stmt.args: %s %r' % (stmt.args, stmt.args), 3)
        for i, arg in enumerate(stmt.args):
            log('args[%i]: %s %r' % (i, arg, arg), 4)

    def _next_states_for_GimpleCond(self, stmt):
        log('stmt.exprcode: %s' % stmt.exprcode, 4)
        log('stmt.exprtype: %s' % stmt.exprtype, 4)
        log('stmt.lhs: %r %s' % (stmt.lhs, stmt.lhs), 4)
        log('stmt.rhs: %r %s' % (stmt.rhs, stmt.rhs), 4)
        log('dir(stmt.lhs): %s' % dir(stmt.lhs), 5)
        log('dir(stmt.rhs): %s' % dir(stmt.rhs), 5)
        boolval = self.eval_condition(stmt)
        if boolval is True:
            log('taking True edge', 2)
            e = true_edge(self.loc.bb)
            assert e
            return [self.update_loc(Location.get_block_start(e.dest))]
        elif boolval is False:
            log('taking False edge', 2)
            e = false_edge(self.loc.bb)
            assert e
            return [self.update_loc(Location.get_block_start(e.dest))]
        else:
            assert isinstance(boolval, UnknownValue)
            # We don't have enough information; both branches are possible:
            return [self.update_loc(Location.get_block_start(e.dest))
                    for e in self.loc.bb.succs]

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
        return [self.use_next_loc()] # for now

def iter_traces(fun, prefix=None):
    # Traverse the tree of traces of program state
    # FIXME: this code can't cope with loops yet
    log('iter_traces(%r, %r)' % (fun, prefix))
    if prefix is None:
        prefix = Trace()
        state = MyState(Location.get_block_start(fun.cfg.entry),
                        {})
    else:
        state = prefix.states[-1]
    prefix.log('PREFIX', 1)
    log('  %s:%s' % (fun.decl.name, state.loc))
    nextstates = state.next_states()
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
        prefix.log('FINISHED TRACE', 1)
        return [prefix]

def check_refcounts(fun):
    #ops = Operations(fun)

    # Abstract interpretation:
    # Walk the CFG, gathering the information we're interested in

    traces = iter_traces(fun)
    for i, trace in enumerate(traces):
        trace.log('TRACE %i' % i, 0)

    if 1:
        dot = cfg_to_dot(fun.cfg)
        invoke_dot(dot)


        
