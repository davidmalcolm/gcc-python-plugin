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

from libcpychecker.absinterp import *
from libcpychecker.diagnostics import Reporter
from libcpychecker.PyArg_ParseTuple import log

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
    """
    Value for an ob_refcnt field.

    'relvalue' is all of the references owned within this function.

    The actual value of ob_refcnt >= relvalue
    """
    def __init__(self, relvalue):
        self.relvalue = relvalue

    def __str__(self):
        return 'refs: %i' % self.relvalue

    def __repr__(self):
        return 'RefcountValue(%i)' % self.relvalue

class GenericTpDealloc(AbstractValue):
    """
    A function pointer that points to a "typical" tp_dealloc callback
    i.e. one that frees up the underlying memory
    """
    def get_transitions_for_function_call(self, state, stmt):
        assert isinstance(state, State)
        assert isinstance(stmt, gcc.GimpleCall)
        returntype = stmt.fn.type.dereference.type

        # Mark the arg as being deallocated:
        value = state.eval_rvalue(stmt.args[0])
        assert isinstance(value, PointerToRegion)
        region = value.region
        assert isinstance(region, Region)
        log('generic tp_dealloc called for %s' % region)

        # Get the description of the region before trashing it:
        desc = 'calling tp_dealloc on %s' % region
        result = state.make_assignment(stmt.lhs,
                                       UnknownValue(returntype, stmt.loc),
                                       'calling tp_dealloc on %s' % region)
        new = state.copy()
        new.loc = state.loc.next_loc()

        # Mark the region as deallocated
        # Since regions are shared with other states, we have to set this up
        # for this state by assigning it with a special "DeallocatedMemory"
        # value
        # Clear the value for any fields within the region:
        for k, v in region.fields.items():
            if v in new.value_for_region:
                del new.value_for_region[v]
        # Set the default value for the whole region to be "DeallocatedMemory"
        new.region_for_var[region] = region
        new.value_for_region[region] = DeallocatedMemory(None, stmt.loc)

        return [Transition(state, new, desc)]

class MyState(State):
    def __init__(self, loc, region_for_var, value_for_region, return_rvalue, owned_refs, resources, exception_rvalue):
        State.__init__(self, loc, region_for_var, value_for_region, return_rvalue)
        self.owned_refs = owned_refs
        self.resources = resources
        self.exception_rvalue = exception_rvalue

    def copy(self):
        return self.__class__(self.loc,
                              self.region_for_var.copy(),
                              self.value_for_region.copy(),
                              self.return_rvalue,
                              self.owned_refs[:],
                              self.resources.copy(),
                              self.exception_rvalue)

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
            raise NotImplementedError("Don't know how to cope with %r (%s) at %s"
                                      % (stmt, stmt, stmt.loc))

    def set_exception(self, exc_name):
        """
        Given the name of a (PyObject*) global for an exception class, such as
        the string "PyExc_MemoryError", set the exception state to the
        (PyObject*) for said exception class.

        The list of standard exception classes can be seen at:
          http://docs.python.org/c-api/exceptions.html#standard-exceptions
        """
        assert isinstance(exc_name, str)
        exc_decl = gccutils.get_global_vardecl_by_name(exc_name)
        assert isinstance(exc_decl, gcc.VarDecl)
        exc_region = self.var_region(exc_decl)
        self.exception_rvalue = exc_region

    def impl_object_ctor(self, stmt, typename, typeobjname):
        """
        Given a gcc.GimpleCall to a Python API function that returns a
        PyObject*, generate a
           (newobj, success, failure)
        triple, where newobj is a region, and success/failure are Transitions
        """
        assert isinstance(stmt, gcc.GimpleCall)
        assert isinstance(stmt.fn.operand, gcc.FunctionDecl)
        assert isinstance(typename, str)
        # the C struct for the type

        assert isinstance(typeobjname, str)
        # the C identifier of the global PyTypeObject for the type

        # Get the gcc.VarDecl for the global PyTypeObject
        typeobjdecl = gccutils.get_global_vardecl_by_name(typeobjname)
        assert isinstance(typeobjdecl, gcc.VarDecl)

        fnname = stmt.fn.operand.name

        # Allocation and assignment:
        success = self.copy()
        success.loc = self.loc.next_loc()

        # Set up type object:
        typeobjregion = success.var_region(typeobjdecl)
        tp_dealloc = success.make_field_region(typeobjregion, 'tp_dealloc')
        type_of_tp_dealloc = gccutils.get_field_by_name(get_PyTypeObject().type,
                                                        'tp_dealloc').type
        success.value_for_region[tp_dealloc] = GenericTpDealloc(type_of_tp_dealloc,
                                                                stmt.loc)

        nonnull = success.make_heap_region(typename, stmt)
        ob_refcnt = success.make_field_region(nonnull, 'ob_refcnt') # FIXME: this should be a memref and fieldref
        success.value_for_region[ob_refcnt] = RefcountValue(1)
        ob_type = success.make_field_region(nonnull, 'ob_type')
        success.value_for_region[ob_type] = PointerToRegion(get_PyTypeObject().pointer,
                                                            stmt.loc,
                                                            typeobjregion)
        success.assign(stmt.lhs,
                       PointerToRegion(stmt.lhs.type,
                                       stmt.loc,
                                       nonnull))
        success = Transition(self,
                             success,
                             '%s() succeeds' % fnname)
        failure = self.make_assignment(stmt.lhs,
                                       ConcreteValue(stmt.lhs.type, stmt.loc, 0),
                                       '%s() fails' % fnname)
        failure.dest.set_exception('PyExc_MemoryError')
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

    def steal_reference(self, region):
        log('steal_reference(%r)' % region)
        assert isinstance(region, Region)
        ob_refcnt = self.make_field_region(region, 'ob_refcnt')
        value = self.value_for_region[ob_refcnt]
        if isinstance(value, RefcountValue):
            # We have a value known relative to all of the refs owned by the
            # rest of the program.  Given that the rest of the program is
            # stealing a ref, that is increasing by one, hence our value must
            # go down by one:
            self.value_for_region[ob_refcnt] = RefcountValue(value.relvalue - 1)

    def make_transitions_for_fncall(self, stmt, success, failure):
        assert isinstance(stmt, gcc.GimpleCall)
        assert isinstance(success, State)
        assert isinstance(failure, State)

        fnname = stmt.fn.operand.name

        return [Transition(self, success, '%s() succeeds' % fnname),
                Transition(self, failure, '%s() fails' % fnname)]

    # Specific Python API function implementations:
    def impl_PyList_New(self, stmt):
        # Decl:
        #   PyObject* PyList_New(Py_ssize_t len)
        # Returns a new reference, or raises MemoryError
        lenarg = self.eval_rvalue(stmt.args[0])
        assert isinstance(lenarg, AbstractValue)
        newobj, success, failure = self.impl_object_ctor(stmt,
                                                         'PyListObject', 'PyList_Type')
        # Set ob_size:
        ob_size = success.dest.make_field_region(newobj, 'ob_size')
        success.dest.value_for_region[ob_size] = lenarg
        return [success, failure]

    def impl_PyLong_FromLong(self, stmt):
        newobj, success, failure = self.impl_object_ctor(stmt,
                                                         'PyLongObject', 'PyLong_Type')
        return [success, failure]

    def impl_PyList_SetItem(self, stmt):
        # Decl:
        #   int PyList_SetItem(PyObject *list, Py_ssize_t index, PyObject *item)
        fnname = stmt.fn.operand.name

        result = []

        arg_list, arg_index, arg_item = [self.eval_rvalue(arg) for arg in stmt.args]

        # Is it really a list?
        if 0: # FIXME: check
            not_a_list = self.make_concrete_return_of(stmt, -1)
            result.append(Transition(self,
                           not_a_list,
                           '%s() fails (not a list)' % fnname))

        # Index out of range?
        if 0: # FIXME: check
            out_of_range = self.make_concrete_return_of(stmt, -1)
            result.append(Transition(self,
                           out_of_range,
                           '%s() fails (index out of range)' % fnname))

        if 1:
            success  = self.make_concrete_return_of(stmt, 0)
            # FIXME: update refcounts
            # "Steal" a reference to item:
            if isinstance(arg_item, PointerToRegion):
                assert isinstance(arg_item.region, Region)
                success.steal_reference(arg_item.region)

            # and discards a
            # reference to an item already in the list at the affected position.
            result.append(Transition(self,
                                     success,
                                     '%s() succeeds' % fnname))

        return result

    def impl_PyArg_ParseTuple(self, stmt):
        # Decl:
        #   PyAPI_FUNC(int) PyArg_ParseTuple(PyObject *, const char *, ...) Py_FORMAT_PARSETUPLE(PyArg_ParseTuple, 2, 3);
        # Also:
        #   #define PyArg_ParseTuple		_PyArg_ParseTuple_SizeT

        success = self.make_concrete_return_of(stmt, 1)

        failure = self.make_concrete_return_of(stmt, 0)
        # Various errors are possible, but a TypeError is always possible
        # e.g. for the case of the wrong number of arguments:
        failure.set_exception('PyExc_TypeError')

        return self.make_transitions_for_fncall(stmt, success, failure)

    def _get_transitions_for_GimpleCall(self, stmt):
        log('stmt.lhs: %s %r' % (stmt.lhs, stmt.lhs), 3)
        log('stmt.fn: %s %r' % (stmt.fn, stmt.fn), 3)
        log('dir(stmt.fn): %s' % dir(stmt.fn), 4)
        if hasattr(stmt.fn, 'operand'):
            log('stmt.fn.operand: %s' % stmt.fn.operand, 4)
        returntype = stmt.fn.type.dereference.type
        log('returntype: %s' % returntype)

        if isinstance(stmt.fn, gcc.VarDecl):
            # Calling through a function pointer:
            val = self.eval_rvalue(stmt.fn)
            log('val: %s' %  val)
            assert isinstance(val, AbstractValue)
            return val.get_transitions_for_function_call(self, stmt)

        if isinstance(stmt.fn.operand, gcc.FunctionDecl):
            log('dir(stmt.fn.operand): %s' % dir(stmt.fn.operand), 4)
            log('stmt.fn.operand.name: %r' % stmt.fn.operand.name, 4)
            fnname = stmt.fn.operand.name

            # Hand off to impl_* methods, where these exist:
            methname = 'impl_%s' % fnname
            if hasattr(self, methname):
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
        def is_equal(lhs, rhs):
            assert isinstance(lhs, AbstractValue)
            assert isinstance(rhs, AbstractValue)
            if isinstance(rhs, ConcreteValue):
                if isinstance(lhs, PointerToRegion) and rhs.value == 0:
                    log('ptr to region vs 0: %s is definitely not equal to %s' % (lhs, rhs))
                    return False
                if isinstance(lhs, ConcreteValue):
                    log('comparing concrete values: %s %s' % (lhs, rhs))
                    return lhs.value == rhs.value
                if isinstance(lhs, RefcountValue):
                    log('comparing refcount value %s with concrete value: %s' % (lhs, rhs))
                    # The actual value of ob_refcnt >= lhs.relvalue
                    if lhs.relvalue > rhs.value:
                        # (Equality is thus not possible for this case)
                        return False
            if isinstance(rhs, PointerToRegion):
                if isinstance(lhs, PointerToRegion):
                    log('comparing regions: %s %s' % (lhs, rhs))
                    return lhs.region == rhs.region
            # We don't know:
            return None

        log('eval_condition: %s' % stmt)
        lhs = self.eval_rvalue(stmt.lhs)
        rhs = self.eval_rvalue(stmt.rhs)
        log('eval of lhs: %r' % lhs)
        log('eval of rhs: %r' % rhs)
        log('stmt.exprcode: %r' % stmt.exprcode)
        if stmt.exprcode == gcc.EqExpr:
            result = is_equal(lhs, rhs)
            if result is not None:
                return result
        elif stmt.exprcode == gcc.NeExpr:
            result = is_equal(lhs, rhs)
            if result is not None:
                return not result

        log('unable to compare %r with %r' % (lhs, rhs))
        return UnknownValue(stmt.lhs.type, stmt.loc)

    def eval_rhs(self, stmt):
        log('eval_rhs(%s): %s' % (stmt, stmt.rhs))
        rhs = stmt.rhs
        if stmt.exprcode == gcc.PlusExpr:
            a = self.eval_rvalue(rhs[0])
            b = self.eval_rvalue(rhs[1])
            log('a: %r' % a)
            log('b: %r' % b)
            if isinstance(a, ConcreteValue) and isinstance(b, ConcreteValue):
                return ConcreteValue(stmt.lhs.type, stmt.loc, a.value + b.value)
            if isinstance(a, RefcountValue) and isinstance(b, ConcreteValue):
                return RefcountValue(a.relvalue + b.value)

            raise NotImplementedError("Don't know how to cope with addition of\n  %r\nand\n  %r\nat %s"
                                      % (a, b, stmt.loc))
        elif stmt.exprcode == gcc.MinusExpr:
            a = self.eval_rvalue(rhs[0])
            b = self.eval_rvalue(rhs[1])
            log('a: %r' % a)
            log('b: %r' % b)
            if isinstance(a, RefcountValue) and isinstance(b, ConcreteValue):
                return RefcountValue(a.relvalue - b.value)
            raise NotImplementedError("Don't know how to cope with subtraction of\n  %r\nand\n  %rat %s"
                                      % (a, b, stmt.loc))
        elif stmt.exprcode == gcc.ComponentRef:
            return self.eval_rvalue(rhs[0])
        elif stmt.exprcode == gcc.VarDecl:
            return self.eval_rvalue(rhs[0])
        elif stmt.exprcode == gcc.IntegerCst:
            return self.eval_rvalue(rhs[0])
        elif stmt.exprcode == gcc.AddrExpr:
            return self.eval_rvalue(rhs[0])
        elif stmt.exprcode == gcc.NopExpr:
            return self.eval_rvalue(rhs[0])
        elif stmt.exprcode == gcc.ArrayRef:
            return self.eval_rvalue(rhs[0])
        else:
            raise NotImplementedError("Don't know how to cope with exprcode: %r (%s) at %s"
                                      % (stmt.exprcode, stmt.exprcode, stmt.loc))

    def _get_transitions_for_GimpleAssign(self, stmt):
        log('stmt.lhs: %r %s' % (stmt.lhs, stmt.lhs))
        log('stmt.rhs: %r %s' % (stmt.rhs, stmt.rhs))
        log('stmt: %r %s' % (stmt, stmt))
        log('stmt.exprcode: %r' % stmt.exprcode)

        value = self.eval_rhs(stmt)
        log('value from eval_rhs: %r' % value)
        assert isinstance(value, AbstractValue)

        if isinstance(value, DeallocatedMemory):
            raise ReadFromDeallocatedMemory(stmt, value)

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

        rvalue = self.eval_rvalue(stmt.retval)
        log('rvalue from eval_rvalue: %r' % rvalue)

        nextstate = self.copy()
        nextstate.return_rvalue = rvalue
        assert nextstate.return_rvalue is not None # ensure termination
        return [Transition(self, nextstate, 'returning')]

def get_traces(fun):
    return list(iter_traces(fun, MyState))

def dump_traces_to_stdout(traces):
    """
    For use in selftests: dump the traces to stdout, in a form that (hopefully)
    will allow usable comparisons against "gold" output ( not embedding
    anything that changes e.g. names of temporaries, address of wrapper
    objects, etc)
    """
    def dump_object(rvalue, title):
        assert isinstance(rvalue, AbstractValue)
        print('  %s:' % title)
        print('    repr(): %r' % rvalue)
        print('    str(): %s' % rvalue)
        if isinstance(rvalue, PointerToRegion):
            print('    r->ob_refcnt: %r'
                  % endstate.get_value_of_field_by_region(rvalue.region, 'ob_refcnt'))
            print('    r->ob_type: %r'
                  % endstate.get_value_of_field_by_region(rvalue.region, 'ob_type'))

    def dump_region(region, title):
        assert isinstance(region, Region)
        print('  %s:' % title)
        print('    repr(): %r' % region)
        print('    str(): %s' % region)
        print('    r->ob_refcnt: %r'
              % endstate.get_value_of_field_by_region(region, 'ob_refcnt'))
        print('    r->ob_type: %r'
              % endstate.get_value_of_field_by_region(region, 'ob_type'))

    for i, trace in enumerate(traces):
        print('Trace %i:' % i)

        # Emit the "interesting transitions" i.e. those with descriptions:
        print('  Transitions:')
        for trans in trace.transitions:
            if trans.desc:
                print('    %r' % trans.desc)

        # Emit information about the end state:
        endstate = trace.states[-1]

        if trace.err:
            print('  error: %r' % trace.err)
            print('  error: %s' % trace.err)

        if endstate.return_rvalue:
            dump_object(endstate.return_rvalue, 'Return value')

        # Other affected PyObject instances:
        for k in endstate.region_for_var:
            if not isinstance(endstate.region_for_var[k], Region):
                continue
            region = endstate.region_for_var[k]

            # Consider those for which we know something about an "ob_refcnt"
            # field:
            if 'ob_refcnt' not in region.fields:
                continue

            if (isinstance(endstate.return_rvalue, PointerToRegion)
                and region == endstate.return_rvalue.region):
                # (We did the return value above)
                continue

            dump_region(region, str(region))

        # Exception state:
        print('  Exception:')
        print('    %s' % endstate.exception_rvalue)

        if i + 1 < len(traces):
            sys.stdout.write('\n')

def check_refcounts(fun, dump_traces=False, show_traces=False):
    """
    The top-level function of the refcount checker, checking the refcounting
    behavior of a function

    fun: the gcc.Function to be checked

    dump_traces: bool: if True, dump information about the traces through
    the function to stdout (for self tests)

    show_traces: bool: if True, display a diagram of the state transition graph
    """
    # Abstract interpretation:
    # Walk the CFG, gathering the information we're interested in

    log('check_refcounts(%r, %r, %r)' % (fun, dump_traces, show_traces))

    assert isinstance(fun, gcc.Function)

    if show_traces:
        from libcpychecker.visualizations import StateGraphPrettyPrinter
        sg = StateGraph(fun, log, MyState)
        sgpp = StateGraphPrettyPrinter(sg)
        dot = sgpp.to_dot()
        #dot = sgpp.extra_items()
        # print(dot)
        invoke_dot(dot)

    traces = iter_traces(fun, MyState)
    if dump_traces:
        traces = list(traces)
        dump_traces_to_stdout(traces)

    rep = Reporter()

    for i, trace in enumerate(traces):
        trace.log(log, 'TRACE %i' % i, 0)
        if trace.err:
            # This trace bails early with a fatal error; it probably doesn't
            # have a return value
            log('trace.err: %s %r' % (trace.err, trace.err))
            err = rep.make_error(fun, trace.err.loc, str(trace.err))
            err.add_trace(trace)
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
            assert isinstance(region, Region)

            # Consider those for which we know something about an "ob_refcnt"
            # field:
            if 'ob_refcnt' not in region.fields:
                continue

            ob_refcnt = endstate.get_value_of_field_by_region(region,
                                                              'ob_refcnt')
            log('ob_refcnt: %r' % ob_refcnt, 0)

            # If it's the return value, it should have a net refcnt delta of
            # 1; all other PyObject should have a net delta of 0:
            if isinstance(return_value, PointerToRegion) and region == return_value.region:
                desc = 'return value'
                exp_refcnt = 1
            else:
                desc = 'PyObject'
                # We may have a more descriptive name within the region:
                if isinstance(region, RegionOnHeap):
                    desc = region.name
                exp_refcnt = 0
            log('exp_refcnt: %r' % exp_refcnt, 0)

            # Helper function for when ob_refcnt is wrong:
            def emit_refcount_error(msg):
                err = rep.make_error(fun, endstate.get_gcc_loc(fun), msg)

                # For dynamically-allocated objects, indicate where they
                # were allocated:
                if isinstance(region, RegionOnHeap):
                    alloc_loc = region.alloc_stmt.loc
                    if alloc_loc:
                        err.add_note(region.alloc_stmt.loc,
                                     ('%s allocated at: %s'
                                      % (region.name,
                                         get_src_for_loc(alloc_loc))))

                # Summarize the control flow we followed through the function:
                err.add_trace(trace)

                return err

            # Here's where we verify the refcount:
            if isinstance(ob_refcnt, RefcountValue):
                if ob_refcnt.relvalue > exp_refcnt:
                    # Refcount is too high:
                    err = emit_refcount_error('ob_refcnt of %s is %i too high'
                                              % (desc, ob_refcnt.relvalue - exp_refcnt))
                elif ob_refcnt.relvalue < exp_refcnt:
                    # Refcount is too low:
                    err = emit_refcount_error('ob_refcnt of %s is %i too low'
                                              % (desc, exp_refcnt - ob_refcnt.relvalue))
                    # Special-case hint for when None has too low a refcount:
                    if isinstance(return_value.region, RegionForGlobal):
                        if return_value.region.vardecl.name == '_Py_NoneStruct':
                            err.add_note(endstate.get_gcc_loc(fun),
                                         'consider using "Py_RETURN_NONE;"')

        # Detect returning a deallocated object:
        if return_value:
            if isinstance(return_value, PointerToRegion):
                rvalue = endstate.value_for_region.get(return_value.region, None)
                if isinstance(rvalue, DeallocatedMemory):
                    err = rep.make_error(fun,
                                         endstate.get_gcc_loc(fun),
                                         'returning pointer to deallocated memory')
                    err.add_trace(trace)
                    err.add_note(rvalue.loc,
                                 'memory deallocated here')

        # Detect failure to set exceptions when returning NULL:
        if not trace.err:
            if (isinstance(return_value, ConcreteValue)
                and return_value.value == 0
                and str(return_value.gcctype)=='struct PyObject *'):

                if (isinstance(endstate.exception_rvalue,
                              ConcreteValue)
                    and endstate.exception_rvalue.value == 0):
                    err = rep.make_error(fun,
                                         endstate.get_gcc_loc(fun),
                                         'returning (PyObject*)NULL without setting an exception')
                    err.add_trace(trace)

    # (all traces analysed)

    if rep.got_errors():
        rep.dump_html(fun, '%s-refcount-errors.html' % fun.decl.name)

    if 0:
        dot = cfg_to_dot(fun.cfg)
        invoke_dot(dot)


