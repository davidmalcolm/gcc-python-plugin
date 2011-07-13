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

class RefcountValue(AbstractValue):
    def __init__(self, relvalue):
        self.relvalue = relvalue

    def __str__(self):
        return 'refs: %i' % self.relvalue

    def __repr__(self):
        return 'RefcountValue(%i)' % self.relvalue

class MyState(State):
    def __init__(self, loc, region_for_var, value_for_region, return_rvalue, owned_refs, resources):
        State.__init__(self, loc, region_for_var, value_for_region, return_rvalue)
        self.owned_refs = owned_refs
        self.resources = resources

    def copy(self):
        return self.__class__(self.loc,
                              self.region_for_var.copy(),
                              self.value_for_region.copy(),
                              self.return_rvalue,
                              self.owned_refs[:],
                              self.resources.copy())

    def _extra(self):
        return ' %s' % self.owned_refs

    def acquire(self, resource):
        self.resources.acquire(resource)

    def release(self, resource):
        self.resources.release(resource)

    def make_assignment(self, key, value, desc, additional_ptr=None):
        if desc:
            assert isinstance(desc, str)
        transition = State.make_assignment(self, key, value, desc)
        if additional_ptr:
            transition.dest.owned_refs.append(additional_ptr)
        return transition

    def get_transitions(self):
        # Return a list of Transition instances, based on input State
        stmt = self.loc.get_stmt()
        if stmt:
            return self._get_transitions_for_stmt(stmt)
        else:
            result = []
            for loc in self.loc.next_locs():
                newstate = self.copy()
                newstate.loc = loc
                result.append(Transition(self, newstate, ''))
            log('result: %s' % result)
            return result

    def _get_transitions_for_stmt(self, stmt):
        log('_get_transitions_for_stmt: %r %s' % (stmt, stmt), 2)
        log('dir(stmt): %s' % dir(stmt), 3)
        if isinstance(stmt, gcc.GimpleCall):
            return self._get_transitions_for_GimpleCall(stmt)
        elif isinstance(stmt, (gcc.GimpleDebug, gcc.GimpleLabel)):
            return [self.use_next_loc()]
        elif isinstance(stmt, gcc.GimpleCond):
            return self._get_transitions_for_GimpleCond(stmt)
        elif isinstance(stmt, gcc.GimpleReturn):
            return self._get_transitions_for_GimpleReturn(stmt)
        elif isinstance(stmt, gcc.GimpleAssign):
            return self._get_transitions_for_GimpleAssign(stmt)
        else:
            raise "foo"

    def impl_object_ctor(self, stmt, typename):
        """
        Given a gcc.GimpleCall to a Python API function that returns a
        PyObject*, generate a
           (newobj, success, failure)
        triple, where newobj is a region, and success/failure are Transitions
        """
        assert isinstance(stmt, gcc.GimpleCall)
        assert isinstance(stmt.fn.operand, gcc.FunctionDecl)
        assert isinstance(typename, str)
        # the C identifier of the global PyTypeObject for the type
        # FIXME: not yet used

        fnname = stmt.fn.operand.name

        # Allocation and assignment:
        success = self.copy()
        success.loc = self.loc.next_loc()
        nonnull = success.make_heap_region()
        ob_refcnt = success.make_field_region(nonnull, 'ob_refcnt') # FIXME: this should be a memref and fieldref
        success.value_for_region[ob_refcnt] = RefcountValue(1)
        success.assign(stmt.lhs, nonnull)
        success = Transition(self,
                             success,
                             '%s() succeeds' % fnname)
        failure = self.make_assignment(stmt.lhs,
                                       ConcreteValue(stmt.lhs.type, stmt.loc, 0),
                                       '%s() fails' % fnname)
        return (nonnull, success, failure)

    def make_concrete_return_of(self, stmt, value):
        """
        Clone this state (at a function call), updating the location, and
        setting the result of the call to the given concrete value
        """
        newstate = self.copy()
        newstate.loc = self.loc.next_loc()
        if stmt.lhs:
            newstate.assign(stmt.lhs,
                            ConcreteValue(stmt.lhs.type, stmt.loc, value))
        return newstate

    # Specific Python API function implementations:
    def impl_PyList_New(self, stmt):
        # Decl:
        #   PyObject* PyList_New(Py_ssize_t len)
        # Returns a new reference, or raises MemoryError
        lenarg = self.eval_expr(stmt.args[0])
        newobj, success, failure = self.impl_object_ctor(stmt, 'PyList_Type')
        # Set ob_size:
        ob_size = success.dest.make_field_region(newobj, 'ob_size')
        success.dest.value_for_region[ob_size] = lenarg
        return [success, failure]

    def impl_PyLong_FromLong(self, stmt):
        newobj, success, failure = self.impl_object_ctor(stmt, 'PyLong_Type')
        return [success, failure]

    def impl_PyList_SetItem(self, stmt):
        # int PyList_SetItem(PyObject *list, Py_ssize_t index, PyObject *item)
        fnname = stmt.fn.operand.name

        # Is it really a list?
        not_a_list = self.make_concrete_return_of(stmt, -1)
        # FIXME: can we check that it's a list?

        # Index out of range?
        out_of_range = self.make_concrete_return_of(stmt, -1)

        success  = self.make_concrete_return_of(stmt, 0)
        # FIXME: update refcounts
        # Note This function "steals" a reference to item and discards a
        # reference to an item already in the list at the affected position.
        return [Transition(self,
                           not_a_list,
                           '%s() fails (not a list)' % fnname),
                Transition(self,
                           out_of_range,
                           '%s() fails (index out of range)' % fnname),
                Transition(self,
                           success,
                           '%s() succeeds' % fnname)]

    def _get_transitions_for_GimpleCall(self, stmt):
        log('stmt.lhs: %s %r' % (stmt.lhs, stmt.lhs), 3)
        log('stmt.fn: %s %r' % (stmt.fn, stmt.fn), 3)
        log('dir(stmt.fn): %s' % dir(stmt.fn), 4)
        log('stmt.fn.operand: %s' % stmt.fn.operand, 4)
        returntype = stmt.fn.type.dereference.type
        log('returntype: %s' % returntype)
        if isinstance(stmt.fn.operand, gcc.FunctionDecl):
            log('dir(stmt.fn.operand): %s' % dir(stmt.fn.operand), 4)
            log('stmt.fn.operand.name: %r' % stmt.fn.operand.name, 4)
            fnname = stmt.fn.operand.name

            if fnname in ('PyList_New', 'PyLong_FromLong', 'PyList_SetItem'):
                meth = getattr(self, 'impl_%s' % fnname)
                return meth(stmt)
            # Function returning borrowed references:
            elif fnname in ('Py_InitModule4_64',):
                return [self.make_assignment(stmt.lhs, NonNullPtrValue(1, stmt)),
                        self.make_assignment(stmt.lhs, NullPtrValue())]
            else:
                #from libcpychecker.c_stdio import c_stdio_functions, handle_c_stdio_function

                #if fnname in c_stdio_functions:
                #    return handle_c_stdio_function(self, fnname, stmt)

                # Unknown function:
                log('Invocation of unknown function: %r' % fnname)
                return [self.make_assignment(stmt.lhs,
                                             UnknownValue(returntype, stmt.loc),
                                             None)]

        log('stmt.args: %s %r' % (stmt.args, stmt.args), 3)
        for i, arg in enumerate(stmt.args):
            log('args[%i]: %s %r' % (i, arg, arg), 4)

    def _get_transitions_for_GimpleCond(self, stmt):
        def make_transition_for_true(stmt):
            e = true_edge(self.loc.bb)
            assert e
            nextstate = self.update_loc(Location.get_block_start(e.dest))
            nextstate.prior_bool = True
            return Transition(self, nextstate, 'taking True path')

        def make_transition_for_false(stmt):
            e = false_edge(self.loc.bb)
            assert e
            nextstate = self.update_loc(Location.get_block_start(e.dest))
            nextstate.prior_bool = False
            return Transition(self, nextstate, 'taking False path')

        log('stmt.exprcode: %s' % stmt.exprcode, 4)
        log('stmt.exprtype: %s' % stmt.exprtype, 4)
        log('stmt.lhs: %r %s' % (stmt.lhs, stmt.lhs), 4)
        log('stmt.rhs: %r %s' % (stmt.rhs, stmt.rhs), 4)
        log('dir(stmt.lhs): %s' % dir(stmt.lhs), 5)
        log('dir(stmt.rhs): %s' % dir(stmt.rhs), 5)
        boolval = self.eval_condition(stmt)
        if boolval is True:
            log('taking True edge', 2)
            nextstate = make_transition_for_true(stmt)
            return [nextstate]
        elif boolval is False:
            log('taking False edge', 2)
            nextstate = make_transition_for_false(stmt)
            return [nextstate]
        else:
            assert isinstance(boolval, UnknownValue)
            # We don't have enough information; both branches are possible:
            return [make_transition_for_true(stmt),
                    make_transition_for_false(stmt)]

    def eval_condition(self, stmt):
        log('eval_condition: %s' % stmt)
        lhs = self.eval_expr(stmt.lhs)
        rhs = self.eval_expr(stmt.rhs)
        log('eval of lhs: %r' % lhs)
        log('eval of rhs: %r' % rhs)
        log('stmt.exprcode: %r' % stmt.exprcode)
        if stmt.exprcode == gcc.EqExpr:
            if isinstance(rhs, ConcreteValue):
                if isinstance(lhs, Region) and rhs.value == 0:
                    return False
                if isinstance(lhs, ConcreteValue):
                    return lhs.value == rhs.value
        log('got here')
        return UnknownValue(stmt.lhs.type, stmt.loc)

    def eval_rhs(self, stmt):
        rhs = stmt.rhs
        if stmt.exprcode == gcc.PlusExpr:
            a = self.eval_expr(rhs[0])
            b = self.eval_expr(rhs[1])
            log('a: %r' % a)
            log('b: %r' % b)
            if isinstance(a, RefcountValue) and isinstance(b, ConcreteValue):
                return RefcountValue(a.relvalue + b.value)
            raise 'bar'
        elif stmt.exprcode == gcc.ComponentRef:
            return self.eval_expr(rhs[0])
        elif stmt.exprcode == gcc.VarDecl:
            return self.eval_expr(rhs[0])
        elif stmt.exprcode == gcc.IntegerCst:
            return self.eval_expr(rhs[0])
        elif stmt.exprcode == gcc.AddrExpr:
            return self.eval_expr(rhs[0])
        else:
            raise 'foo'

    def _get_transitions_for_GimpleAssign(self, stmt):
        log('stmt.lhs: %r %s' % (stmt.lhs, stmt.lhs))
        log('stmt.rhs: %r %s' % (stmt.rhs, stmt.rhs))
        log('stmt: %r %s' % (stmt, stmt))
        log('stmt.exprcode: %r' % stmt.exprcode)

        value = self.eval_rhs(stmt)
        log('value from eval_rhs: %r' % value)

        nextstate = self.use_next_loc()
        """
        if isinstance(stmt.lhs, gcc.MemRef):
            log('value: %s %r' % (value, value))
            # We're writing a value to memory; if it's a PyObject*
            # then we're surrending a reference on it:
            if value in nextstate.owned_refs:
                log('removing ownership of %s' % value)
                nextstate.owned_refs.remove(value)
        """
        return [self.make_assignment(stmt.lhs,
                                     value,
                                     None)]

    def _get_transitions_for_GimpleReturn(self, stmt):
        #log('stmt.lhs: %r %s' % (stmt.lhs, stmt.lhs))
        #log('stmt.rhs: %r %s' % (stmt.rhs, stmt.rhs))
        log('stmt: %r %s' % (stmt, stmt))
        log('stmt.retval: %r' % stmt.retval)

        rvalue = self.eval_expr(stmt.retval)
        log('rvalue from eval_expr: %r' % rvalue)

        nextstate = self.copy()
        nextstate.return_rvalue = rvalue
        assert nextstate.return_rvalue is not None # ensure termination
        return [Transition(self, nextstate, 'returning')]

def get_traces(fun):
    return list(iter_traces(fun, MyState))

def check_refcounts(fun, show_traces):
    # Abstract interpretation:
    # Walk the CFG, gathering the information we're interested in

    log('check_refcounts(%r, %r)' % (fun, show_traces))

    if show_traces:
        from libcpychecker.visualizations import StateGraphPrettyPrinter
        sg = StateGraph(fun, log, MyState)
        sgpp = StateGraphPrettyPrinter(sg)
        dot = sgpp.to_dot()
        #dot = sgpp.extra_items()
        # print(dot)
        invoke_dot(dot)

    traces = iter_traces(fun, MyState)
    if show_traces:
        traces = list(traces)
        for i, trace in enumerate(traces):
            def my_logger(item, indent=0):
                sys.stdout.write('%s%s\n' % ('  ' * indent, item))
            trace.log(my_logger, 'TRACE %i' % i, 0)

            # Show trace #0:
            if 0: # i == 0:
                from libcpychecker.visualizations import TracePrettyPrinter
                tpp = TracePrettyPrinter(fun.cfg, trace)
                dot = tpp.to_dot()
                print dot
                f = open('test.dot', 'w')
                f.write(dot)
                f.close()
                invoke_dot(dot)

    for i, trace in enumerate(traces):
        trace.log(log, 'TRACE %i' % i, 0)
        if trace.err:
            # This trace bails early with a fatal error; it probably doesn't
            # have a return value
            log('trace.err: %s %r' % (trace.err, trace.err))
            gcc.error(trace.err.loc,
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

        # Locate all PyObject that we touched
        endstate = trace.states[-1]
        endstate.log(log, 0)
        log('return_value: %r' % return_value, 0)
        log('endstate.region_for_var: %r' % endstate.region_for_var, 0)
        log('endstate.value_for_region: %r' % endstate.value_for_region, 0)

        # Consider all regions of memory we know about:
        for k in endstate.region_for_var:
            if not isinstance(endstate.region_for_var[k], Region):
                continue
            region = endstate.region_for_var[k]

            log('considering ob_refcnt of %r' % region)

            # Consider those for which we know something about an "ob_refcnt"
            # field:
            if 'ob_refcnt' not in region.fields:
                continue

            ob_refcnt = endstate.get_value_of_field_by_region(region,
                                                              'ob_refcnt')
            log('ob_refcnt: %r' % ob_refcnt, 0)

            # If it's the return value, it should have a net refcnt delta of
            # 1; all other PyObject should have a net delta of 0:
            if region == return_value:
                desc = 'return value'
                exp_refcnt = 1
            else:
                desc = 'PyObject'
                exp_refcnt = 0
            log('exp_refcnt: %r' % exp_refcnt, 0)
            if isinstance(ob_refcnt, RefcountValue):
                if ob_refcnt.relvalue > exp_refcnt:
                    # too high
                    gcc.error(endstate.get_gcc_loc(),
                              'ob_refcnt of %s is %i too high' % (desc, ob_refcnt.relvalue - exp_refcnt))
                    describe_trace(trace)
                elif ob_refcnt.relvalue < exp_refcnt:
                    # too low
                    gcc.error(endstate.get_gcc_loc(),
                              'ob_refcnt of %s is %i too low' % (desc, exp_refcnt - ob_refcnt.relvalue))
                    describe_trace(trace)
                    if isinstance(return_value, RegionForGlobal):
                        if return_value.vardecl.name == '_Py_NoneStruct':
                            gcc.inform(endstate.get_gcc_loc(),
                                       'consider using "Py_RETURN_NONE;"')

    if 0:
        dot = cfg_to_dot(fun.cfg)
        invoke_dot(dot)


