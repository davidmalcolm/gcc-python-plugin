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

from gccutils import cfg_to_dot, invoke_dot, get_src_for_loc, check_isinstance

from libcpychecker.absinterp import *
from libcpychecker.attributes import fnnames_returning_borrowed_refs
from libcpychecker.diagnostics import Reporter, Annotator, Note
from libcpychecker.PyArg_ParseTuple import PyArgParseFmt, FormatStringError, \
    TypeCheckCheckerType, TypeCheckResultType
from libcpychecker.Py_BuildValue import PyBuildValueFmt, ObjectFormatUnit, \
    CodeSO, CodeN
from libcpychecker.types import is_py3k, is_debug_build, get_PyObjectPtr
from libcpychecker.utils import log

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

def type_is_pyobjptr_subclass(t):
    assert t is None or isinstance(t, gcc.Type)
    # It must be a pointer:
    if not isinstance(t, gcc.PointerType):
        return False

    # ...to a struct:
    if not isinstance(t.dereference, gcc.RecordType):
        return False

    fieldnames = [f.name for f in t.dereference.fields]
    if is_py3k():
        # For Python 3, the first field must be "ob_base", or it must be "PyObject":
        if str(t) == 'struct PyObject *':
            return True
        if fieldnames[0] != 'ob_base':
            return False
    else:
        # For Python 2, the first two fields must be "ob_refcnt" and "ob_type".
        # (In a debug build, these are preceded by _ob_next and _ob_prev)
        # FIXME: debug builds!
        if is_debug_build():
            if fieldnames[:4] != ['_ob_next', '_ob_prev',
                                  'ob_refcnt', 'ob_type']:
                return False
        else:
            if fieldnames[:2] != ['ob_refcnt', 'ob_type']:
                return False

    # Passed all tests:
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

def make_null_pyobject_ptr(stmt):
    return ConcreteValue(get_PyObjectPtr(), stmt.loc, 0)

class RefcountValue(AbstractValue):
    """
    Value for an ob_refcnt field.

    'relvalue' is all of the references owned within this function.

    'min_external' is a lower bound on all references owned outside the
    scope of this function.

    The actual value of ob_refcnt >= (relvalue + min_external)

    Examples:

      - an argument passed in a a borrowed ref starts with (0, 1), in that
      the function doesn't own any refs on it, but it has a refcount of at
      least 1, due to refs we know nothing about.

      - a newly constructed object gets (1, 0): we own a reference on it,
      and we don't know if there are any external refs on it.
    """
    __slots__ = ('relvalue', 'min_external')

    def __init__(self, relvalue, min_external):
        self.relvalue = relvalue
        self.min_external = min_external

    @classmethod
    def new_ref(cls):
        return RefcountValue(relvalue=1,
                             min_external=0)

    @classmethod
    def borrowed_ref(cls):
        return RefcountValue(relvalue=0,
                             min_external=1)

    def get_min_value(self):
        return self.relvalue + self.min_external

    def __str__(self):
        return 'refs: %i + N where N >= %i' % (self.relvalue, self.min_external)

    def __repr__(self):
        return 'RefcountValue(%i, %i)' % (self.relvalue, self.min_external)

    def eval_binop(self, exprcode, rhs, gcctype, loc):
        if isinstance(rhs, ConcreteValue):
            if exprcode == gcc.PlusExpr:
                return RefcountValue(self.relvalue + rhs.value, self.min_external)
            elif exprcode == gcc.MinusExpr:
                return RefcountValue(self.relvalue - rhs.value, self.min_external)
        return UnknownValue.make(gcctype, loc)

    def is_equal(self, rhs):
        if isinstance(rhs, ConcreteValue):
            log('comparing refcount value %s with concrete value: %s', self, rhs)
            # The actual value of ob_refcnt >= lhs.relvalue
            if self.relvalue > rhs.value:
                # (Equality is thus not possible for this case)
                return False

    def impl_is_lt(self, rhs):
        if isinstance(rhs, ConcreteValue):
            log('comparing refcount value %s with concrete value: %s', lhs, rhs)
            if self.get_min_value() >= rhs.value:
                return False

    def impl_is_ge(self, rhs):
        if isinstance(rhs, ConcreteValue):
            log('comparing refcount value %s with concrete value: %s', lhs, rhs)
            if self.get_min_value() >= rhs.value:
                return True


class GenericTpDealloc(AbstractValue):
    """
    A function pointer that points to a "typical" tp_dealloc callback
    i.e. one that frees up the underlying memory
    """
    def get_transitions_for_function_call(self, state, stmt):
        check_isinstance(state, State)
        check_isinstance(stmt, gcc.GimpleCall)
        returntype = stmt.fn.type.dereference.type

        # Mark the arg as being deallocated:
        value = state.eval_rvalue(stmt.args[0], stmt.loc)
        check_isinstance(value, PointerToRegion)
        region = value.region
        check_isinstance(region, Region)
        log('generic tp_dealloc called for %s', region)

        # Get the description of the region before trashing it:
        desc = 'calling tp_dealloc on %s' % region
        result = state.mktrans_assignment(stmt.lhs,
                                       UnknownValue.make(returntype, stmt.loc),
                                       'calling tp_dealloc on %s' % region)
        s_new = state.copy()
        s_new.loc = state.loc.next_loc()

        # Mark the region as deallocated
        # Since regions are shared with other states, we have to set this up
        # for this state by assigning it with a special "DeallocatedMemory"
        # value
        # Clear the value for any fields within the region:
        for k, v in region.fields.items():
            if v in s_new.value_for_region:
                del s_new.value_for_region[v]
        # Set the default value for the whole region to be "DeallocatedMemory"
        s_new.region_for_var[region] = region
        s_new.value_for_region[region] = DeallocatedMemory(None, stmt.loc)

        return [Transition(state, s_new, desc)]

class CPython(Facet):
    __slots__ = ('exception_rvalue', )

    def __init__(self, state, exception_rvalue=None, fun=None):
        Facet.__init__(self, state)
        if exception_rvalue:
            check_isinstance(exception_rvalue, AbstractValue)
            self.exception_rvalue = exception_rvalue
        else:
            check_isinstance(fun, gcc.Function)
            self.exception_rvalue = ConcreteValue(get_PyObjectPtr(),
                                                  fun.start,
                                                  0)

    def copy(self, newstate):
        f_new = CPython(newstate,
                        self.exception_rvalue)
        return f_new

    def init_for_function(self, fun):
        log('CPython.init_for_function(%r)', fun)

        # Initialize PyObject* arguments to sane values
        # (assume that they're non-NULL)
        nonnull_args = get_nonnull_arguments(fun.decl.type)
        for idx, parm in enumerate(fun.decl.arguments):
            region = self.state.eval_lvalue(parm, None)
            if type_is_pyobjptr_subclass(parm.type):
                # We have a PyObject* (or a derived class)
                log('got python obj arg: %r', region)
                # Assume it's a non-NULL ptr:
                objregion = Region('region-for-arg-%s' % parm, None)
                self.state.region_for_var[objregion] = objregion
                self.state.value_for_region[region] = PointerToRegion(parm.type,
                                                                parm.location,
                                                                objregion)
                # Assume we have a borrowed reference:
                ob_refcnt = self.state.make_field_region(objregion, 'ob_refcnt') # FIXME: this should be a memref and fieldref
                self.state.value_for_region[ob_refcnt] = RefcountValue.borrowed_ref()

                # Assume it has a non-NULL ob_type:
                ob_type = self.state.make_field_region(objregion, 'ob_type')
                typeobjregion = Region('region-for-type-of-arg-%s' % parm, None)
                self.state.value_for_region[ob_type] = PointerToRegion(get_PyTypeObject().pointer,
                                                                 parm.location,
                                                                 typeobjregion)
        self.state.verify()

    def change_refcount(self, pyobjectptr, loc, fn):
        """
        Manipulate pyobjectptr's ob_refcnt.

        fn is a function taking a RefcountValue instance, returning another one
        """
        check_isinstance(pyobjectptr, PointerToRegion)
        ob_refcnt = self.state.make_field_region(pyobjectptr.region,
                                                 'ob_refcnt')
        check_isinstance(ob_refcnt, Region)
        oldvalue = self.state.get_store(ob_refcnt, None, loc) # FIXME: gcctype
        check_isinstance(oldvalue, AbstractValue)
        log('oldvalue: %r', oldvalue)
        #if isinstance(oldvalue, UnknownValue):
        #    self.raise_split_value(oldvalue, loc)
        check_isinstance(oldvalue, RefcountValue)
        newvalue = fn(oldvalue)
        log('newvalue: %r', newvalue)
        self.state.value_for_region[ob_refcnt] = newvalue
        return newvalue

    def add_ref(self, pyobjectptr, loc):
        """
        Add a "visible" reference to pyobjectptr's ob_refcnt i.e. a reference
        being held by a PyObject* that we are directly tracking.
        """
        def _incref_internal(oldvalue):
            return RefcountValue(oldvalue.relvalue + 1,
                                 oldvalue.min_external)
        self.change_refcount(pyobjectptr,
                             loc,
                             _incref_internal)

    def add_external_ref(self, pyobjectptr, loc):
        """
        Add an "external" reference to pyobjectptr's ob_refcnt i.e. a reference
        being held by a PyObject* that we're not directly tracking.
        """
        def _incref_external(oldvalue):
            return RefcountValue(oldvalue.relvalue,
                                 oldvalue.min_external + 1)
        self.change_refcount(pyobjectptr,
                             loc,
                             _incref_external)

    def dec_ref(self, pyobjectptr, loc):
        """
        Remove a "visible" reference to pyobjectptr's ob_refcnt i.e. a
        reference being held by a PyObject* that we are directly tracking.
        """
        def _decref_internal(oldvalue):
            return RefcountValue(oldvalue.relvalue - 1,
                                 oldvalue.min_external)
        check_isinstance(pyobjectptr, PointerToRegion)
        v_ob_refcnt = self.change_refcount(pyobjectptr,
                                           loc,
                                           _decref_internal)
        # FIXME: potentially this destroys the object

    def set_exception(self, exc_name, loc):
        """
        Given the name of a (PyObject*) global for an exception class, such as
        the string "PyExc_MemoryError", set the exception state to the
        (PyObject*) for said exception class.

        The list of standard exception classes can be seen at:
          http://docs.python.org/c-api/exceptions.html#standard-exceptions
        """
        check_isinstance(exc_name, str)
        exc_decl = gccutils.get_global_vardecl_by_name(exc_name)
        check_isinstance(exc_decl, gcc.VarDecl)
        r_exception = self.state.var_region(exc_decl)
        v_exception = PointerToRegion(get_PyObjectPtr(), loc, r_exception)
        self.exception_rvalue = v_exception

    def bad_internal_call(self, loc):
        """
        Analogous to PyErr_BadInternalCall(), which is a macro to
        _PyErr_BadInternalCall() at the source file/line location
        """
        self.set_exception('PyExc_SystemError', loc)

    def object_ctor(self, stmt, typename, typeobjname):
        """
        Given a gcc.GimpleCall to a Python API function that returns a
        PyObject*, generate a
           (r_newobj, t_success, t_failure)
        triple, where r_newobj is a region, and success/failure are Transitions
        """
        check_isinstance(stmt, gcc.GimpleCall)
        check_isinstance(stmt.fn.operand, gcc.FunctionDecl)
        check_isinstance(typename, str)
        # the C struct for the type

        check_isinstance(typeobjname, str)
        # the C identifier of the global PyTypeObject for the type

        # Get the gcc.VarDecl for the global PyTypeObject
        typeobjdecl = gccutils.get_global_vardecl_by_name(typeobjname)
        check_isinstance(typeobjdecl, gcc.VarDecl)

        fnname = stmt.fn.operand.name
        returntype = stmt.fn.type.dereference.type

        # (the region hierarchy is shared by all states, so we can get the
        # var region from "self", rather than "success")
        typeobjregion = self.state.var_region(typeobjdecl)

        # The "success" case:
        s_success, nonnull = self.mkstate_new_ref(stmt, typename, typeobjregion)
        t_success = Transition(self.state,
                               s_success,
                               'when %s() succeeds' % fnname)
        # The "failure" case:
        t_failure = self.state.mktrans_assignment(stmt.lhs,
                                       ConcreteValue(returntype, stmt.loc, 0),
                                       'when %s() fails' % fnname)
        t_failure.dest.cpython.set_exception('PyExc_MemoryError', stmt.loc)
        return (nonnull, t_success, t_failure)

    def steal_reference(self, region):
        log('steal_reference(%r)', region)
        check_isinstance(region, Region)
        ob_refcnt = self.state.make_field_region(region, 'ob_refcnt')
        value = self.state.value_for_region[ob_refcnt]
        if isinstance(value, RefcountValue):
            # We have a value known relative to all of the refs owned by the
            # rest of the program.  Given that the rest of the program is
            # stealing a ref, that is increasing by one, hence our value must
            # go down by one:
            self.state.value_for_region[ob_refcnt] = RefcountValue(value.relvalue - 1,
                                                                   value.min_external + 1)

    def make_sane_object(self, stmt, name, v_refcount, r_typeobj=None):
        """
        Modify this State, adding a new object.

        The ob_refcnt is set to the given value.

        The object has ob_type set to either the given typeobj,
        or a sane new one.

        Returns r_nonnull, a Region
        """
        check_isinstance(stmt, gcc.Gimple)
        check_isinstance(name, str)
        check_isinstance(v_refcount, RefcountValue)

        # Claim a Region for the object:
        r_nonnull = self.state.make_heap_region(name, stmt)

        # Set up ob_refcnt to the given value:
        r_ob_refcnt = self.state.make_field_region(r_nonnull,
                                             'ob_refcnt') # FIXME: this should be a memref and fieldref
        self.state.value_for_region[r_ob_refcnt] = v_refcount

        # Ensure that the new object has a sane ob_type:
        if r_typeobj is None:
            # If no specific type object provided by caller, supply one:
            r_typeobj = Region('PyTypeObject for %s' % name, None)
            # it is its own region:
            self.state.region_for_var[r_typeobj] = r_typeobj

        # Set up obj->ob_type:
        ob_type = self.state.make_field_region(r_nonnull, 'ob_type')
        self.state.value_for_region[ob_type] = PointerToRegion(get_PyTypeObject().pointer,
                                                         stmt.loc,
                                                         r_typeobj)
        # Set up obj->ob_type->tp_dealloc:
        tp_dealloc = self.state.make_field_region(r_typeobj, 'tp_dealloc')
        type_of_tp_dealloc = gccutils.get_field_by_name(get_PyTypeObject().type,
                                                        'tp_dealloc').type
        self.state.value_for_region[tp_dealloc] = GenericTpDealloc(type_of_tp_dealloc,
                                                             stmt.loc)
        return r_nonnull

    def mkstate_new_ref(self, stmt, name, typeobjregion=None):
        """
        Make a new State, in which a new ref to some object has been
        assigned to the statement's LHS.

        Returns a pair: (newstate, RegionOnHeap for the new object)
        """
        newstate = self.state.copy()
        newstate.loc = self.state.loc.next_loc()

        r_nonnull = newstate.cpython.make_sane_object(stmt, name,
                                              RefcountValue.new_ref(),
                                              typeobjregion)
        if stmt.lhs:
            newstate.assign(stmt.lhs,
                            PointerToRegion(stmt.lhs.type,
                                            stmt.loc,
                                            r_nonnull),
                            stmt.loc)
        # FIXME
        return newstate, r_nonnull

    def mkstate_borrowed_ref(self, stmt, name, r_typeobj=None):
        """Make a new State, giving a borrowed ref to some object"""
        newstate = self.state.copy()
        newstate.loc = self.state.loc.next_loc()

        r_nonnull = newstate.cpython.make_sane_object(stmt, name,
                                              RefcountValue.borrowed_ref(),
                                              r_typeobj)
        if stmt.lhs:
            newstate.assign(stmt.lhs,
                            PointerToRegion(stmt.lhs.type,
                                            stmt.loc,
                                            r_nonnull),
                            stmt.loc)
        return newstate

    def mkstate_exception(self, stmt):
        """Make a new State, giving NULL and some exception"""
        if stmt.lhs:
            value = ConcreteValue(stmt.lhs.type, stmt.loc, 0)
        else:
            value = None
        t_failure = self.state.mktrans_assignment(stmt.lhs,
                                                  value,
                                                  None)
        t_failure.dest.cpython.set_exception('PyExc_MemoryError', stmt.loc)
        return t_failure.dest

    def make_transitions_for_new_ref_or_fail(self, stmt, objname=None):
        """
        Generate the appropriate list of 2 transitions for a call to a
        function that either:
          - returns either a new ref, or
          - fails with NULL and sets an exception
        Optionally, a name for the new object can be supplied; otherwise
        a sane default will be used.
        """
        if objname is None:
            fnname = stmt.fn.operand.name
            objname = 'new ref from call to %s' % fnname
        s_success, nonnull = self.mkstate_new_ref(stmt, objname)
        s_failure = self.mkstate_exception(stmt)
        return self.state.make_transitions_for_fncall(stmt, s_success, s_failure)

    def make_transitions_for_borrowed_ref_or_fail(self, stmt, objname=None):
        """
        Generate the appropriate list of 2 transitions for a call to a
        function that either:
          - returns either a borrowed ref, or
          - fails with NULL and sets an exception
        Optionally, a name for the new object can be supplied; otherwise
        a sane default will be used.
        """
        if objname is None:
            fnname = stmt.fn.operand.name
            objname = 'borrowed ref from call to %s' % fnname
        s_success = self.mkstate_borrowed_ref(stmt, objname)
        s_failure = self.mkstate_exception(stmt)
        return self.state.make_transitions_for_fncall(stmt, s_success, s_failure)

    def object_ptr_has_global_ob_type(self, v_object_ptr, vardecl_name):
        """
        Boolean: do we know that the given PyObject* has an ob_type matching
        the given global PyTypeObject (e.g. "PyString_Type")
        """
        check_isinstance(v_object_ptr, AbstractValue)
        check_isinstance(vardecl_name, str)
        if isinstance(v_object_ptr, PointerToRegion):
            v_ob_type = self.state.get_value_of_field_by_region(v_object_ptr.region,
                                                          'ob_type')
            if isinstance(v_ob_type, PointerToRegion):
                if isinstance(v_ob_type.region, RegionForGlobal):
                    if v_ob_type.region.vardecl.name == vardecl_name:
                        return True

    # Treat calls to various function prefixed with __cpychecker as special,
    # to help with debugging, and when writing selftests:

    def impl___cpychecker_log(self, stmt, *args):
        """
        Assuming a C function with this declaration:
            extern void __cpychecker_log(const char *);
        and that it is called with a string constant, log the message
        within the trace.
        """
        returntype = stmt.fn.type.dereference.type
        desc =  args[0].as_string_constant()
        return [self.state.mktrans_assignment(stmt.lhs,
                                     UnknownValue.make(returntype, stmt.loc),
                                     desc)]

    def impl___cpychecker_dump(self, stmt, *args):
        returntype = stmt.fn.type.dereference.type
        # Give the transition a description that embeds the argument values
        # This will show up in selftests (and in error reports that embed
        # traces)
        desc = '__dump(%s)' % (','.join([str(arg) for arg in args]))
        return [self.state.mktrans_assignment(stmt.lhs,
                                     UnknownValue.make(returntype, stmt.loc),
                                     desc)]

    def impl___cpychecker_dump_all(self, stmt, *args):
        """
        Dump all of our state to stdout, to help with debugging
        """
        print(str(stmt.loc))
        print(self.state.as_str_table())
        returntype = stmt.fn.type.dereference.type
        return [self.state.mktrans_assignment(stmt.lhs,
                                     UnknownValue.make(returntype, stmt.loc),
                                              None)]

    def impl___cpychecker_assert_equal(self, stmt, *args):
        """
        Assuming a C function with this declaration:
            extern void __cpychecker_assert_equal(T, T);
        for some type T, raise an exception within the checker if the two
        arguments are non-equal (for use in writing selftests).
        """
        returntype = stmt.fn.type.dereference.type
        # Give the transition a description that embeds the argument values
        # This will show up in selftests (and in error reports that embed
        # traces)
        if args[0] != args[1]:
            raise AssertionError('%s != %s' % (args[0], args[1]))
        desc = '__cpychecker_assert_equal(%s)' % (','.join([str(arg) for arg in args]))
        return [self.state.mktrans_assignment(stmt.lhs,
                                     UnknownValue.make(returntype, stmt.loc),
                                     desc)]

    # Specific Python API function implementations
    # (keep this list alphabetized, discounting case and underscores)

    ########################################################################
    # PyArg_*
    ########################################################################
    def _handle_PyArg_function(self, stmt, v_fmt, v_varargs, with_size_t):
        """
        Handle one of the various PyArg_Parse* functions
        """
        check_isinstance(v_fmt, AbstractValue)
        check_isinstance(v_varargs, tuple) # of AbstractValue
        check_isinstance(with_size_t, bool)

        s_success = self.state.mkstate_concrete_return_of(stmt, 1)

        s_failure = self.state.mkstate_concrete_return_of(stmt, 0)
        # Various errors are possible, but a TypeError is always possible
        # e.g. for the case of the wrong number of arguments:
        s_failure.cpython.set_exception('PyExc_TypeError', stmt.loc)

        # Parse the format string, and figure out what the effects of a
        # successful parsing are:

        def _get_new_value_for_vararg(unit, exptype):
            if unit.code == 'O':
                # non-NULL sane PyObject*:
                return PointerToRegion(exptype.dereference,
                                       stmt.loc,
                                       self.make_sane_object(stmt, 'object from arg "O"',
                                                             RefcountValue.borrowed_ref()))

            if unit.code == 'O!':
                if isinstance(exptype, TypeCheckCheckerType):
                    # This is read from, not written to:
                    return None
                if isinstance(exptype, TypeCheckResultType):
                    # non-NULL sane PyObject*
                    # FIXME: we could perhaps set ob_type to the given type.
                    # However "O!" only enforces the weaker condition:
                    #    if (PyType_IsSubtype(arg->ob_type, type))
                    return PointerToRegion(get_PyObjectPtr(),
                                           stmt.loc,
                                           self.make_sane_object(stmt, 'object from arg "O!"',
                                                                 RefcountValue.borrowed_ref()))

            # Unknown value:
            check_isinstance(exptype, gcc.PointerType)
            return UnknownValue.make(exptype.dereference, stmt.loc)

        def _handle_successful_parse(fmt):
            exptypes = fmt.iter_exp_types()
            for v_vararg, (unit, exptype) in zip(v_varargs, exptypes):
                if 0:
                    print('v_vararg: %r' % v_vararg)
                    print('  unit: %r' % unit)
                    print('  exptype: %r %s' % (exptype, exptype))
                if isinstance(v_vararg, PointerToRegion):
                    v_new = _get_new_value_for_vararg(unit, exptype)
                    if v_new:
                        check_isinstance(v_new, AbstractValue)
                        s_success.value_for_region[v_vararg.region] = v_new

        fmt_string = v_fmt.as_string_constant()
        if fmt_string:
            try:
                fmt = PyArgParseFmt.from_string(fmt_string, with_size_t)
                _handle_successful_parse(fmt)
            except FormatStringError:
                pass

        return self.state.make_transitions_for_fncall(stmt, s_success, s_failure)

    def impl_PyArg_ParseTuple(self, stmt, v_args, v_fmt, *v_varargs):
        # Declared in modsupport.h:
        #   PyAPI_FUNC(int) PyArg_ParseTuple(PyObject *, const char *, ...) Py_FORMAT_PARSETUPLE(PyArg_ParseTuple, 2, 3);
        # Also, with #ifdef PY_SSIZE_T_CLEAN
        #   #define PyArg_ParseTuple		_PyArg_ParseTuple_SizeT

        return self._handle_PyArg_function(stmt, v_fmt, v_varargs, with_size_t=False)

    def impl__PyArg_ParseTuple_SizeT(self, stmt, v_args, v_fmt, *v_varargs):
        # Declared in modsupport.h:
        #   PyAPI_FUNC(int) PyArg_ParseTuple(PyObject *, const char *, ...) Py_FORMAT_PARSETUPLE(PyArg_ParseTuple, 2, 3);
        # Also, with #ifdef PY_SSIZE_T_CLEAN
        #   #define PyArg_ParseTuple		_PyArg_ParseTuple_SizeT

        return self._handle_PyArg_function(stmt, v_fmt, v_varargs, with_size_t=True)

    def impl_PyArg_ParseTupleAndKeywords(self, stmt, v_args, v_kwargs,
                                         v_fmt, v_keywords, *v_varargs):
        # Declared in modsupport.h:
        #   PyAPI_FUNC(int) PyArg_ParseTupleAndKeywords(PyObject *, PyObject *,
        #                                               const char *, char **, ...);
        #
        # Also, with #ifdef PY_SSIZE_T_CLEAN
        #   #define PyArg_ParseTupleAndKeywords	_PyArg_ParseTupleAndKeywords_SizeT

        return self._handle_PyArg_function(stmt, v_fmt, v_varargs, with_size_t=False)

    def impl__PyArg_ParseTupleAndKeywords_SizeT(self, stmt, v_args, v_kwargs,
                                                v_fmt, v_keywords, *v_varargs):
        # Declared in modsupport.h:
        #   PyAPI_FUNC(int) PyArg_ParseTupleAndKeywords(PyObject *, PyObject *,
        #                                               const char *, char **, ...);
        #
        # Also, with #ifdef PY_SSIZE_T_CLEAN
        #   #define PyArg_ParseTupleAndKeywords	_PyArg_ParseTupleAndKeywords_SizeT

        return self._handle_PyArg_function(stmt, v_fmt, v_varargs, with_size_t=True)

    def impl_PyArg_UnpackTuple(self, stmt, v_args, v_name, v_min, v_max,
                               *v_varargs):
        # http://docs.python.org/c-api/arg.html#PyArg_UnpackTuple
        # Declared in modsupport.h:
        #   PyAPI_FUNC(int) PyArg_UnpackTuple(PyObject *, const char *,
        #                                     Py_ssize_t, Py_ssize_t, ...);
        # Defined in Python/getargs.c:
        #   int
        #   PyArg_UnpackTuple(PyObject *args, const char *name,
        #                     Py_ssize_t min, Py_ssize_t max, ...)
        #
        # Will only write betweeen v_min..v_max values back

        # For now, assume that we can figure out min and max during the
        # analysis:
        check_isinstance(v_min, ConcreteValue)
        check_isinstance(v_max, ConcreteValue)

        # for arg in v_varargs:
        #     print arg

        # Detect wrong number of arguments:
        if len(v_varargs) != v_max.value:
            class WrongNumberOfVarargs(PredictedError):
                def __init__(self, v_max, v_varargs):
                    self.v_max = v_max
                    self.v_varargs = v_varargs
                def __str__(self):
                    return ('expected %i vararg pointer(s); got %i' %
                            (v_max.value, len(v_varargs)))
            raise WrongNumberOfVarargs(v_max, v_varargs)

        s_failure = self.state.mkstate_concrete_return_of(stmt, 0)
        # Various errors are possible, but a TypeError is always possible
        # e.g. for the case of the wrong number of arguments:
        s_failure.cpython.set_exception('PyExc_TypeError', stmt.loc)
        result = [self.state.mktrans_from_fncall_state(stmt,
                        s_failure, 'fails', has_siblings=True)]

        # Enumerate all possible successes, to detect the case where an
        # optional argument doesn't get initialized
        for numargs in range(v_min.value, v_max.value + 1):
            s_success = self.state.mkstate_concrete_return_of(stmt, 1)
            result.append(self.state.mktrans_from_fncall_state(
                    stmt, s_success, 'successfully unpacks %i argument(s)' % numargs,
                    has_siblings=True))
            # Write sane objects to each location that gets written to,
            # given this number of arguments:
            for i in range(numargs):
                vararg = v_varargs[i]
                if isinstance(vararg, PointerToRegion):
                    # Write back a sane object:
                    v_obj = PointerToRegion(get_PyObjectPtr(),
                                            stmt.loc,
                                            s_success.cpython.make_sane_object(stmt,
                                                                               'argument %i' % (i + 1),
                                                                               RefcountValue.borrowed_ref()))
                    s_success.value_for_region[vararg.region] = v_obj

        return result

    ########################################################################
    # PyBool_*
    ########################################################################
    def impl_PyBool_FromLong(self, stmt, v_long):
        # Declared in boolobject.h:
        #   PyAPI_FUNC(PyObject *) PyBool_FromLong(long);
        # Defined in Objects/boolobject.c
        #
        # Always succeeds, returning a new ref to one of the two singleton
        # booleans
        # v_ok = self.state.eval_stmt_args(stmt)[0]
        s_success, r_nonnull = self.mkstate_new_ref(stmt, 'PyBool_FromLong')
        return [self.state.mktrans_from_fncall_state(stmt, s_success,
                                                     'returns', False)]

    ########################################################################
    # Py_BuildValue*
    ########################################################################
    def _handle_Py_BuildValue(self, stmt, v_fmt, v_varargs, with_size_t):
        """
        Handle one of the various Py_BuildValue functions

        http://docs.python.org/c-api/arg.html#Py_BuildValue

        We don't try to model the resulting object, just the success/failure
        and the impact on the refcounts of any inputs
        """
        check_isinstance(v_fmt, AbstractValue)
        check_isinstance(v_varargs, tuple) # of AbstractValue
        check_isinstance(with_size_t, bool)

        # The function can succeed or fail
        # If any of the PyObject* inputs are NULL, it is doomed to failure
        def _handle_successful_parse(fmt):
            """
            Returns a boolean: is success of the function possible?
            """
            exptypes = fmt.iter_exp_types()
            for v_vararg, (unit, exptype) in zip(v_varargs, exptypes):
                if 0:
                    print('v_vararg: %r' % v_vararg)
                    print('  unit: %r' % unit)
                    print('  exptype: %r %s' % (exptype, exptype))
                if isinstance(unit, ObjectFormatUnit):
                    # NULL inputs ptrs guarantee failure:
                    if isinstance(v_vararg, ConcreteValue):
                        if v_vararg.is_null_ptr():
                            # The call will fail:
                            return False

                    # non-NULL input ptrs receive "external" references on
                    # success for codes "S" and "O":
                    if isinstance(v_vararg, PointerToRegion):
                        if isinstance(unit, CodeSO):
                            t_success.dest.cpython.add_external_ref(v_vararg, stmt.loc)
                        else:
                            t_success.dest.cpython.steal_reference(v_vararg.region)
            return True

        t_success, t_failure = self.make_transitions_for_new_ref_or_fail(stmt)

        fmt_string = v_fmt.as_string_constant()
        if fmt_string:
            try:
                fmt = PyBuildValueFmt.from_string(fmt_string, with_size_t)
                if not _handle_successful_parse(fmt):
                    return [t_failure]
            except FormatStringError:
                pass

        return [t_success, t_failure]

    def impl_Py_BuildValue(self, stmt, v_fmt, *args):
        # http://docs.python.org/c-api/arg.html#Py_BuildValue
        #
        # Declared in modsupport.h:
        #   PyAPI_FUNC(PyObject *) Py_BuildValue(const char *, ...);
        #
        # Defined in Python/modsupport.c:
        #   PyObject *
        #   Py_BuildValue(const char *format, ...)
        #
        return self._handle_Py_BuildValue(stmt, v_fmt, args, with_size_t=False)

    def impl__Py_BuildValue_SizeT(self, stmt, v_fmt, *args):
        # http://docs.python.org/c-api/arg.html#Py_BuildValue
        #
        # Declared in modsupport.h:
        #   #ifdef PY_SSIZE_T_CLEAN
        #   #define Py_BuildValue   _Py_BuildValue_SizeT
        #   #endif
        #
        #   PyAPI_FUNC(PyObject *) _Py_BuildValue_SizeT(const char *, ...);
        #
        # Defined in Python/modsupport.c:
        #   PyObject *
        #   _Py_BuildValue_SizeT(const char *format, ...)
        #
        return self._handle_Py_BuildValue(stmt, v_fmt, args, with_size_t=True)

    ########################################################################
    # PyDict_*
    ########################################################################
    def impl_PyDict_GetItem(self, stmt, v_mp, v_key):
        # Declared in dictobject.h:
        #   PyAPI_FUNC(PyObject *) PyDict_GetItem(PyObject *mp, PyObject *key);
        # Defined in dictobject.c
        #
        # Returns a borrowed ref, or NULL if not found.  It does _not_ set
        # an exception (for historical reasons)
        s_success = self.mkstate_borrowed_ref(stmt, 'result from PyDict_GetItem')
        t_notfound = self.state.mktrans_assignment(stmt.lhs,
                                             make_null_pyobject_ptr(stmt),
                                             'when PyDict_GetItem does not find item')
        return [self.state.mktrans_from_fncall_state(stmt, s_success,
                                                     'succeeds', True),
                t_notfound]

    def impl_PyDict_GetItemString(self, stmt, v_dp, v_key):
        # Declared in dictobject.h:
        #   PyAPI_FUNC(PyObject *) PyDict_GetItemString(PyObject *dp, const char *key);
        # Defined in dictobject.c
        #
        # Returns a borrowed ref, or NULL if not found (can also return NULL
        # and set MemoryError)
        s_success = self.mkstate_borrowed_ref(stmt, 'PyDict_GetItemString')
        t_notfound = self.state.mktrans_assignment(stmt.lhs,
                                             make_null_pyobject_ptr(stmt),
                                             'PyDict_GetItemString does not find string')
        if 0:
            t_memoryexc = self.state.mktrans_assignment(stmt.lhs,
                                                  make_null_pyobject_ptr(stmt),
                                                  'OOM allocating string') # FIXME: set exception
        return [self.state.mktrans_from_fncall_state(stmt, s_success,
                                                     'succeeds', True),
                t_notfound]
                #t_memoryexc]

    def impl_PyDict_New(self, stmt):
        r_newobj, t_success, t_failure = self.object_ctor(stmt,
                                                          'PyDictObject',
                                                          'PyDict_Type')
        return [t_success, t_failure]

    def impl_PyDict_SetItem(self, stmt, v_dp, v_key, v_item):
        # Declared in dictobject.h:
        #   PyAPI_FUNC(int) PyDict_SetItem(PyObject *mp, PyObject *key, PyObject *item);
        # Defined in dictobject.c
        #
        # API docs:
        #   http://docs.python.org/c-api/dict.html#PyDict_SetItem
        # Can return -1, setting MemoryError
        # Otherwise returns 0, and adds a ref on the value
        self.state.raise_any_null_ptr_func_arg(stmt, 1, v_key)
        self.state.raise_any_null_ptr_func_arg(stmt, 2, v_item)

        s_success = self.state.mkstate_concrete_return_of(stmt, 0)
        # the dictionary now owns a new ref on "item".  We won't model the
        # insides of the dictionary type.  Instead, treat it as a new
        # external reference:
        s_success.cpython.add_external_ref(v_item, stmt.loc)

        s_failure = self.state.mkstate_concrete_return_of(stmt, -1)
        s_failure.cpython.set_exception('PyExc_MemoryError', stmt.loc)

        return self.state.make_transitions_for_fncall(stmt, s_success, s_failure)

    def impl_PyDict_SetItemString(self, stmt, v_dp, v_key, v_item):
        # Declared in dictobject.h:
        #   PyAPI_FUNC(int) PyDict_SetItemString(PyObject *dp, const char *key, PyObject *item);
        # Defined in dictobject.c
        #
        # API docs:
        #   http://docs.python.org/c-api/dict.html#PyDict_SetItemString
        # Can return -1, setting MemoryError
        # Otherwise returns 0, and adds a ref on the value

        # This is implemented in terms of PyDict_SetItem and shows the same
        # success and failures:
        self.state.raise_any_null_ptr_func_arg(stmt, 1, v_key)
        self.state.raise_any_null_ptr_func_arg(stmt, 2, v_item)
        # (strictly speaking, v_key goes from being a char* to a PyObject*)
        return self.impl_PyDict_SetItem(stmt, v_dp, v_key, v_item)

    ########################################################################
    # PyErr_*
    ########################################################################
    def impl_PyErr_Format(self, stmt, v_exc, v_fmt, *v_args):
        # Declared in pyerrors.h:
        #   PyAPI_FUNC(void) PyErr_SetString(PyObject *, const char *);
        # Defined in Python/errors.c
        #

        # It always returns NULL:
        t_next = self.state.mktrans_assignment(stmt.lhs,
                                         make_null_pyobject_ptr(stmt),
                                         'PyErr_Format()')
        t_next.dest.cpython.exception_rvalue = v_exc
        return [t_next]

    def impl_PyErr_NoMemory(self, stmt):
        # Declared in pyerrors.h:
        #   PyAPI_FUNC(PyObject *) PyErr_NoMemory(void);
        #
        # Defined in Python/errors.c
        #
        # It always returns NULL:
        t_next = self.state.mktrans_assignment(stmt.lhs,
                                         make_null_pyobject_ptr(stmt),
                                         'PyErr_NoMemory()')
        t_next.dest.cpython.set_exception('PyExc_MemoryError', stmt.loc)
        return [t_next]

    def impl_PyErr_Occurred(self, stmt):
        # Declared in pyerrors.h:
        #   PyAPI_FUNC(PyObject *) PyErr_Occurred(void);
        #
        # Defined in Python/errors.c
        #
        # http://docs.python.org/c-api/exceptions.html#PyErr_Occurred
        # Returns a borrowed reference; can't fail:
        t_next = self.state.mktrans_assignment(stmt.lhs,
                                         self.exception_rvalue,
                                         'PyErr_Occurred()')
        return [t_next]

    def impl_PyErr_Print(self, stmt):
        # Declared in pythonrun.h:
        #   PyAPI_FUNC(void) PyErr_Print(void);
        # Defined in pythonrun.c

        t_next = self.state.mktrans_nop(stmt, 'PyErr_Print')
        # Clear the error indicator:
        t_next.dest.cpython.exception_rvalue = make_null_pyobject_ptr(stmt)
        return [t_next]

    def impl_PyErr_PrintEx(self, stmt, v_int):
        # Declared in pythonrun.h:
        #   PyAPI_FUNC(void) PyErr_PrintEx(int);
        # Defined in pythonrun.c

        t_next = self.state.mktrans_nop(stmt, 'PyErr_PrintEx')
        # Clear the error indicator:
        t_next.dest.cpython.exception_rvalue = make_null_pyobject_ptr(stmt)
        return [t_next]

    def impl_PyErr_SetFromErrno(self, stmt, v_exc):
        # API docs:
        #   http://docs.python.org/c-api/exceptions.html#PyErr_SetFromErrno
        #
        # It always returns NULL:
        t_next = self.state.mktrans_assignment(stmt.lhs,
                                         make_null_pyobject_ptr(stmt),
                                         'PyErr_SetFromErrno()')
        t_next.dest.cpython.exception_rvalue = v_exc
        return [t_next]

    def impl_PyErr_SetFromErrnoWithFilename(self, stmt, v_exc):
        # It always returns NULL:
        t_next = self.state.mktrans_assignment(stmt.lhs,
                                         make_null_pyobject_ptr(stmt),
                                         'PyErr_SetFromErrnoWithFilename()')
        t_next.dest.cpython.exception_rvalue = v_exc
        return [t_next]

    def impl_PyErr_SetObject(self, stmt, v_exc, v_value):
        # http://docs.python.org/c-api/exceptions.html#PyErr_SetObject
        #
        # Declared in pyerrors.h:
        #   PyAPI_FUNC(void) PyErr_SetObject(PyObject *, PyObject *);
        #
        # Defined in Python/errors.c
        #   void
        #   PyErr_SetObject(PyObject *exception, PyObject *value)
        #
        # It's acceptable for each of v_exc and v_value to be NULL
        t_next = self.state.mktrans_nop(stmt, 'PyErr_SetObject')
        t_next.dest.cpython.exception_rvalue = v_exc
        if isinstance(v_exc, PointerToRegion):
            t_next.dest.cpython.add_external_ref(v_exc, stmt.loc)
        if isinstance(v_value, PointerToRegion):
            t_next.dest.cpython.add_external_ref(v_value, stmt.loc)
        return [t_next]

    def impl_PyErr_SetString(self, stmt, v_exc, v_string):
        # Declared in pyerrors.h:
        #   PyAPI_FUNC(void) PyErr_SetString(PyObject *, const char *);
        # Defined in Python/errors.c
        #
        t_next = self.state.mktrans_nop(stmt, 'PyErr_SetString')
        t_next.dest.cpython.exception_rvalue = v_exc
        return [t_next]

    ########################################################################
    # PyEval_InitThreads()
    ########################################################################
    def impl_PyEval_InitThreads(self, stmt):
        # http://docs.python.org/c-api/init.html#PyEval_InitThreads
        # For now, treat it as a no-op:
        return [self.state.mktrans_nop(stmt, 'PyEval_InitThreads')]

    ########################################################################
    # Py_Finalize()
    ########################################################################
    def impl_Py_Finalize(self, stmt):
        # http://docs.python.org/c-api/init.html#Py_Finalize
        # For now, treat it as a no-op:
        return [self.state.mktrans_nop(stmt, 'Py_Finalize')]

    ########################################################################
    # PyGILState_*
    ########################################################################
    def impl_PyGILState_Ensure(self, stmt):
        # http://docs.python.org/c-api/init.html#PyGILState_Ensure
        # Return some opaque handle:
        returntype = stmt.fn.type.dereference.type
        return [self.state.mktrans_assignment(stmt.lhs,
                                              UnknownValue.make(returntype, stmt.loc),
                                              'PyGILState_Ensure')]

    def impl_PyGILState_Release(self, stmt, v_state):
        # http://docs.python.org/c-api/init.html#PyGILState_Release
        # For now, treat it as a no-op:
        return [self.state.mktrans_nop(stmt, 'PyGILState_Release')]

    ########################################################################
    # PyImport_*
    ########################################################################
    def impl_PyImport_AppendInittab(self, stmt, v_name, v_initfunc):
        # http://docs.python.org/c-api/import.html#PyImport_AppendInittab
        s_success = self.state.mkstate_concrete_return_of(stmt, 0)
        s_failure = self.state.mkstate_concrete_return_of(stmt, -1)
        # (doesn't set an exception on failure, and Py_Initialize shouldn't
        # have been called yet, in any case)
        return self.state.make_transitions_for_fncall(stmt, s_success, s_failure)

    def impl_PyImport_ImportModule(self, stmt, v_name):
        # http://docs.python.org/c-api/import.html#PyImport_ImportModule
        r_newobj, t_success, t_failure = self.object_ctor(stmt,
                                                          'PyModuleObject',
                                                          'PyModule_Type')
        return [t_success, t_failure]

    ########################################################################
    # Py_Initialize*
    ########################################################################
    def impl_Py_Initialize(self, stmt):
        # http://docs.python.org/c-api/init.html#Py_Initialize
        # For now, treat it as a no-op:
        return [self.state.mktrans_nop(stmt, 'Py_Initialize')]

    ########################################################################
    # Py_InitModule*
    ########################################################################
    def impl_Py_InitModule4_64(self, stmt, v_name, v_methods,
                               v_doc, v_self, v_apiver):
        # Decl:
        #   PyAPI_FUNC(PyObject *) Py_InitModule4(const char *name, PyMethodDef *methods,
        #                                         const char *doc, PyObject *self,
        #                                         int apiver);
        #  Returns a borrowed reference
        #
        # FIXME:
        #  On 64-bit:
        #    #define Py_InitModule4 Py_InitModule4_64
        #  with tracerefs:
        #    #define Py_InitModule4 Py_InitModule4TraceRefs_64
        #    #define Py_InitModule4 Py_InitModule4TraceRefs
        s_success = self.mkstate_borrowed_ref(stmt, 'output from Py_InitModule4')
        s_failure = self.mkstate_exception(stmt)
        return self.state.make_transitions_for_fncall(stmt, s_success, s_failure)

    ########################################################################
    # Py_Int*
    ########################################################################
    def impl_PyInt_AsLong(self, stmt, v_op):
        # Declared in intobject.h as:
        #   PyAPI_FUNC(long) PyInt_AsLong(PyObject *);
        # Defined in Objects/intobject.c
        #
        # http://docs.python.org/c-api/int.html#PyInt_AsLong

        # Can fail (gracefully) with NULL, and with non-int objects

        returntype = stmt.fn.type.dereference.type

        if self.object_ptr_has_global_ob_type(v_op, 'PyInt_Type'):
            # We know it's a PyIntObject; the call will succeed:
            # FIXME: cast:
            v_ob_ival = self.state.get_value_of_field_by_region(v_op.region,
                                                          'ob_ival')
            t_success = self.state.mktrans_assignment(stmt.lhs,
                                                v_ob_ival,
                                                'PyInt_AsLong() returns ob_ival')
            return [t_success]

        # We don't know if it's a PyIntObject (or subclass); the call could
        # fail:
        t_success = self.state.mktrans_assignment(stmt.lhs,
                                            UnknownValue.make(returntype, stmt.loc),
                                            'PyInt_AsLong() succeeds')
        t_failure = self.state.mktrans_assignment(stmt.lhs,
                                            ConcreteValue(returntype, stmt.loc, -1),
                                            'PyInt_AsLong() fails')
        t_failure.dest.cpython.set_exception('PyExc_MemoryError', stmt.loc)
        return [t_success, t_failure]

    def impl_PyInt_FromLong(self, stmt, v_ival):
        # Declared in intobject.h as:
        #   PyAPI_FUNC(PyObject *) PyInt_FromLong(long);
        # Defined in Objects/intobject.c
        #
        # CPython2 shares objects for integers in the range:
        #   -5 <= ival < 257
        # within intobject.c's "small_ints" array and these are preallocated
        # by _PyInt_Init().  Thus, for these values, we know that the call
        # cannot fail

        r_newobj, t_success, t_failure = self.object_ctor(stmt,
                                                          'PyIntObject',
                                                          'PyInt_Type')
        # Set ob_size:
        r_ob_size = t_success.dest.make_field_region(r_newobj, 'ob_ival')
        t_success.dest.value_for_region[r_ob_size] = v_ival

        if isinstance(v_ival, ConcreteValue):
            if v_ival.value >= -5 and v_ival.value < 257:
                # We know that failure isn't possible:
                return [t_success]

        return [t_success, t_failure]

    ########################################################################
    # PyList_*
    ########################################################################
    def impl_PyList_Append(self, stmt, v_op, v_newitem):
        # Declared in listobject.h as:
        #   PyAPI_FUNC(int) PyList_Append(PyObject *, PyObject *);
        #
        # Defined in listobject.c
        #
        # http://docs.python.org/c-api/list.html#PyList_Append
        #
        # If it succeeds, it adds a reference on the item
        #

        # On success, adds a ref on input:
        s_success = self.state.mkstate_concrete_return_of(stmt, 0)
        s_success.cpython.add_ref(v_newitem, stmt.loc)
        #...and set the pointer value within ob_item array, so that we can
        # discount that refcount:
        ob_item_region = self.state.make_field_region(v_op.region, 'ob_item')
        ob_size_region = self.state.make_field_region(v_op.region, 'ob_size')
        check_isinstance(s_success.value_for_region[ob_size_region], ConcreteValue) # for now
        index = s_success.value_for_region[ob_size_region].value
        array_region = s_success._array_region(ob_item_region, index)
        s_success.value_for_region[array_region] = v_newitem

        # Can fail with memory error, overflow error:
        s_failure = self.state.mkstate_concrete_return_of(stmt, -1)
        s_failure.cpython.set_exception('PyExc_MemoryError', stmt.loc)

        return self.state.make_transitions_for_fncall(stmt, s_success, s_failure)

    def impl_PyList_New(self, stmt, v_len):
        # Decl:
        #   PyObject* PyList_New(Py_ssize_t len)
        # Returns a new reference, or raises MemoryError

        check_isinstance(v_len, AbstractValue)
        r_newobj, t_success, t_failure = self.object_ctor(stmt,
                                                          'PyListObject',
                                                          'PyList_Type')
        # Set ob_size:
        ob_size = t_success.dest.make_field_region(r_newobj, 'ob_size')
        t_success.dest.value_for_region[ob_size] = v_len

        # "Allocate" ob_item, and set it up so that all of the array is
        # treated as NULL:
        ob_item_region = t_success.dest.make_heap_region(
            'ob_item array for PyListObject',
            stmt)
        t_success.dest.value_for_region[ob_item_region] = \
            ConcreteValue(get_PyObjectPtr(),
                          stmt.loc, 0)

        ob_item = t_success.dest.make_field_region(r_newobj, 'ob_item')
        t_success.dest.value_for_region[ob_item] = PointerToRegion(get_PyObjectPtr().pointer,
                                                                 stmt.loc,
                                                                 ob_item_region)

        return [t_success, t_failure]

    def impl_PyList_SetItem(self, stmt, v_list, v_index, v_item):
        # Decl:
        #   int PyList_SetItem(PyObject *list, Py_ssize_t index, PyObject *item)
        # http://docs.python.org/c-api/list.html#PyList_SetItem
        fnname = stmt.fn.operand.name

        # It uses Py_List_Check, a macro which uses Py_TYPE(op) without
        # checking op; hence it will segfault will a NULL "list" pointer
        self.state.raise_any_null_ptr_func_arg(stmt, 0, v_list)

        # However, it appears to be robust in the face of NULL "item" pointers

        result = []

        # Is it really a list?
        if 0: # FIXME: check
            not_a_list = self.state.mkstate_concrete_return_of(stmt, -1)
            result.append(Transition(self.state,
                           not_a_list,
                           '%s() fails (not a list)' % fnname))

        # Index out of range?
        if 0: # FIXME: check
            out_of_range = self.state.mkstate_concrete_return_of(stmt, -1)
            result.append(Transition(self.state,
                           out_of_range,
                           '%s() fails (index out of range)' % fnname))

        if 1:
            s_success  = self.state.mkstate_concrete_return_of(stmt, 0)
            # FIXME: update refcounts
            # "Steal" a reference to item:
            if isinstance(v_item, PointerToRegion):
                check_isinstance(v_item.region, Region)
                s_success.cpython.steal_reference(v_item.region)

            # and discards a
            # reference to an item already in the list at the affected position.
            result.append(Transition(self.state,
                                     s_success,
                                     '%s() succeeds' % fnname))

        return result

    ########################################################################
    # PyLong_*
    ########################################################################
    def impl_PyLong_FromLong(self, stmt, v_long):
        r_newobj, t_success, t_failure = self.object_ctor(stmt,
                                                          'PyLongObject',
                                                          'PyLong_Type')
        return [t_success, t_failure]

    def impl_PyLong_FromString(self, stmt, v_str, v_pend, v_base):
        # Declared in longobject.h as:
        #   PyAPI_FUNC(PyObject *) PyLong_FromString(char *, char **, int);
        # Defined in longobject.c
        # http://docs.python.org/c-api/long.html#PyLong_FromString
        r_newobj, t_success, t_failure = self.object_ctor(stmt,
                                                          'PyLongObject',
                                                          'PyLong_Type')
        return [t_success, t_failure]

    def impl_PyLong_FromVoidPtr(self, stmt, v_p):
        # http://docs.python.org/c-api/long.html#PyLong_FromVoidPtr
        r_newobj, t_success, t_failure = self.object_ctor(stmt,
                                                          'PyLongObject',
                                                          'PyLong_Type')
        return [t_success, t_failure]

    ########################################################################
    # PyMem_*
    ########################################################################
    def impl_PyMem_Free(self, stmt, v_ptr):
        # http://docs.python.org/c-api/memory.html#PyMem_Free
        fnname = 'PyMem_Free'

        # FIXME: it's unsafe to call repeatedly, or on the wrong memory region

        s_new = self.state.copy()
        s_new.loc = self.state.loc.next_loc()
        desc = None

        # It's safe to call on NULL
        if isinstance(v_ptr, ConcreteValue):
            if v_ptr.is_null_ptr():
                desc = 'calling PyMem_Free on NULL'
        elif isinstance(v_ptr, PointerToRegion):
            # Mark the arg as being deallocated:
            region = v_ptr.region
            check_isinstance(region, Region)

            # Get the description of the region before trashing it:
            desc = 'calling PyMem_Free on %s' % region
            #t_temp = state.mktrans_assignment(stmt.lhs,
            #                                  UnknownValue.make(None, stmt.loc),
            #                                  'calling tp_dealloc on %s' % region)

            # Mark the region as deallocated
            # Since regions are shared with other states, we have to set this up
            # for this state by assigning it with a special "DeallocatedMemory"
            # value
            # Clear the value for any fields within the region:
            for k, v in region.fields.items():
                if v in s_new.value_for_region:
                    del s_new.value_for_region[v]
            # Set the default value for the whole region to be "DeallocatedMemory"
            s_new.region_for_var[region] = region
            s_new.value_for_region[region] = DeallocatedMemory(None, stmt.loc)

        return [Transition(self.state, s_new, desc)]

    def impl_PyMem_Malloc(self, stmt, v_size):
        # http://docs.python.org/c-api/memory.html#PyMem_Malloc
        fnname = 'PyMem_Malloc'
        returntype = stmt.fn.type.dereference.type
        r_nonnull = self.state.make_heap_region('PyMem_Malloc', stmt)
        v_nonnull = PointerToRegion(returntype, stmt.loc, r_nonnull)
        # FIXME: it hasn't been initialized
        t_success = self.state.mktrans_assignment(stmt.lhs,
                                            v_nonnull,
                                            'when %s() succeeds' % fnname)
        t_failure = self.state.mktrans_assignment(stmt.lhs,
                                            ConcreteValue(returntype, stmt.loc, 0),
                                            'when %s() fails' % fnname)
        return [t_success, t_failure]

    ########################################################################
    # PyModule_*
    ########################################################################
    def impl_PyModule_AddIntConstant(self, stmt, v_module, v_name, v_value):
        # http://docs.python.org/c-api/module.html#PyModule_AddIntConstant

        # (No externally-visible refcount changes)
        s_success = self.state.mkstate_concrete_return_of(stmt, 0)

        # Can fail with memory error, overflow error:
        s_failure = self.state.mkstate_concrete_return_of(stmt, -1)
        s_failure.cpython.set_exception('PyExc_MemoryError', stmt.loc)

        return self.state.make_transitions_for_fncall(stmt, s_success, s_failure)

    def impl_PyModule_AddObject(self, stmt, v_module, v_name, v_value):
        # Steals a reference to the object if if succeeds:
        #   http://docs.python.org/c-api/module.html#PyModule_AddObject
        # Implemented in Python/modsupport.c

        # On success, steals a ref from v_value:
        s_success = self.state.mkstate_concrete_return_of(stmt, 0)
        s_success.cpython.steal_reference(v_value.region)

        # Can fail with memory error, overflow error:
        s_failure = self.state.mkstate_concrete_return_of(stmt, -1)
        s_failure.cpython.set_exception('PyExc_MemoryError', stmt.loc)

        return self.state.make_transitions_for_fncall(stmt, s_success, s_failure)

    def impl_PyModule_AddStringConstant(self, stmt, v_module, v_name, v_value):
        # http://docs.python.org/c-api/module.html#PyModule_AddStringConstant

        # (No externally-visible refcount changes)
        s_success = self.state.mkstate_concrete_return_of(stmt, 0)

        # Can fail with memory error, overflow error:
        s_failure = self.state.mkstate_concrete_return_of(stmt, -1)
        s_failure.cpython.set_exception('PyExc_MemoryError', stmt.loc)

        return self.state.make_transitions_for_fncall(stmt, s_success, s_failure)

    ########################################################################
    # PyObject_*
    ########################################################################
    def _handle_PyObject_CallMethod(self, stmt, v_o, v_name, v_fmt, v_varargs, with_size_t):
        check_isinstance(v_o, AbstractValue)
        check_isinstance(v_name, AbstractValue)
        check_isinstance(v_fmt, AbstractValue)
        check_isinstance(v_varargs, tuple) # of AbstractValue
        check_isinstance(with_size_t, bool)

        # The function can succeed or fail
        # If any of the PyObject* inputs are NULL, it is doomed to failure
        def _handle_successful_parse(fmt):
            """
            Returns a boolean: is success of the function possible?
            """
            exptypes = fmt.iter_exp_types()
            for v_vararg, (unit, exptype) in zip(v_varargs, exptypes):
                if 0:
                    print('v_vararg: %r' % v_vararg)
                    print('  unit: %r' % unit)
                    print('  exptype: %r %s' % (exptype, exptype))
                if isinstance(unit, ObjectFormatUnit):
                    # NULL inputs ptrs guarantee failure:
                    if isinstance(v_vararg, ConcreteValue):
                        if v_vararg.is_null_ptr():
                            # The call will fail:
                            return False

                    # non-NULL input ptrs receive "external" references on
                    # success for codes "S" and "O", but code "N" steals a
                    # reference for the args.  The args are then decref-ed
                    # by the call.  Hence args with code "N" lose a ref:
                    if isinstance(v_vararg, PointerToRegion):
                        if isinstance(unit, CodeN):
                            t_success.dest.cpython.dec_ref(v_vararg, stmt.loc)
                            t_failure.dest.cpython.dec_ref(v_vararg, stmt.loc)
            return True

        t_success, t_failure = self.make_transitions_for_new_ref_or_fail(stmt)

        fmt_string = v_fmt.as_string_constant()
        if fmt_string:
            try:
                fmt = PyBuildValueFmt.from_string(fmt_string, with_size_t)
                if not _handle_successful_parse(fmt):
                    return [t_failure]
            except FormatStringError:
                pass

        return [t_success, t_failure]

    def impl_PyObject_CallMethod(self, stmt, v_o, v_name, v_format, *args):
        # http://docs.python.org/c-api/object.html#PyObject_CallMethod
        #
        # Implemented in Objects/abstract.c:
        #   PyObject *
        #   PyObject_CallMethod(PyObject *o, char *name, char *format, ...)
        return self._handle_PyObject_CallMethod(stmt, v_o, v_name, v_format,
                                                args, with_size_t=False)

    def impl__PyObject_CallMethod_SizeT(self, stmt, v_o, v_name, v_format, *args):
        # abstract.h has:
        #   #ifdef PY_SSIZE_T_CLEAN
        #   #define PyObject_CallMethod _PyObject_CallMethod_SizeT
        #   #endif
        #
        # Implemented in Objects/abstract.c:
        #   PyObject *
        #   _PyObject_CallMethod_SizeT(PyObject *o, char *name, char *format, ...)
        return self._handle_PyObject_CallMethod(stmt, v_o, v_name, v_format,
                                                args, with_size_t=True)

    def impl_PyObject_HasAttrString(self, stmt, v_o, v_attr_name):
        # http://docs.python.org/c-api/object.html#PyObject_HasAttrString

        fnname = stmt.fn.operand.name

        # the object must be non-NULL: it is unconditionally
        # dereferenced to get the ob_type:
        self.state.raise_any_null_ptr_func_arg(stmt, 0, v_o)

        # attr_name must be non-NULL, this fn calls:
        #   PyObject_GetAttrString(PyObject *v, const char *name)
        # which can call:
        #   PyString_InternFromString(const char *cp)
        #     PyString_FromString(str) <-- must be non-NULL
        self.state.raise_any_null_ptr_func_arg(stmt, 1, v_attr_name)

        s_true = self.state.mkstate_concrete_return_of(stmt, 1)
        s_false = self.state.mkstate_concrete_return_of(stmt, 0)

        return [Transition(self.state, s_true, 'when %s() returns 1 (true)' % fnname),
                Transition(self.state, s_false, 'when %s() returns 0 (false)' % fnname)]

    def impl_PyObject_IsTrue(self, stmt, v_o):
        #   http://docs.python.org/c-api/object.html#PyObject_IsTrue
        s_true = self.state.mkstate_concrete_return_of(stmt, 1)
        s_false = self.state.mkstate_concrete_return_of(stmt, 0)
        s_failure = self.state.mkstate_concrete_return_of(stmt, -1)
        s_failure.cpython.set_exception('PyExc_MemoryError', stmt.loc) # arbitrarily chosen error

        fnname = stmt.fn.operand.name
        return [Transition(self.state, s_true, 'when %s() returns 1 (true)' % fnname),
                Transition(self.state, s_false, 'when %s() returns 0 (false)' % fnname),
                Transition(self.state, s_failure, 'when %s() returns -1 (failure)' % fnname)]

    def impl__PyObject_New(self, stmt, v_typeptr):
        # Declaration in objimpl.h:
        #   PyAPI_FUNC(PyObject *) _PyObject_New(PyTypeObject *);
        #
        # For use via this macro:
        #   #define PyObject_New(type, typeobj) \
        #      ( (type *) _PyObject_New(typeobj) )
        #
        # Definition is in Objects/object.c
        #
        #   Return value: New reference.
        check_isinstance(stmt, gcc.GimpleCall)
        check_isinstance(stmt.fn.operand, gcc.FunctionDecl)

        # Success case: allocation and assignment:
        s_success, nonnull = self.mkstate_new_ref(stmt, '_PyObject_New')
        # ...and set up ob_type on the result object:
        ob_type = s_success.make_field_region(nonnull, 'ob_type')
        s_success.value_for_region[ob_type] = v_typeptr
        t_success = Transition(self.state,
                             s_success,
                             'when _PyObject_New() succeeds')
        # Failure case:
        t_failure = self.state.mktrans_assignment(stmt.lhs,
                                       ConcreteValue(stmt.lhs.type, stmt.loc, 0),
                                       'when _PyObject_New() fails')
        t_failure.dest.cpython.set_exception('PyExc_MemoryError', stmt.loc)
        return [t_success, t_failure]

    def impl_PyObject_Repr(self, stmt, v_o):
        # Declared in object.h as:
        #  PyAPI_FUNC(PyObject *) PyObject_Repr(PyObject *);
        # Docs:
        #   http://docs.python.org/c-api/object.html#PyObject_Repr
        r_newobj, t_success, t_failure = self.object_ctor(stmt,
                                                          'PyStringObject',
                                                          'PyString_Type')
        return [t_success, t_failure]

    def impl_PyObject_Str(self, stmt, v_o):
        # Declared in object.h as:
        #  PyAPI_FUNC(PyObject *) PyObject_Str(PyObject *);
        # also with:
        #  #define PyObject_Bytes PyObject_Str
        r_newobj, t_success, t_failure = self.object_ctor(stmt,
                                                          'PyStringObject',
                                                          'PyString_Type')
        return [t_success, t_failure]

    ########################################################################
    # PyRun_*
    ########################################################################
    def impl_PyRun_SimpleFileExFlags(self, stmt, v_fp, v_filename,
                                     v_closeit, v_flags):
        # http://docs.python.org/c-api/veryhigh.html#PyRun_SimpleFileExFlags
        s_success = self.state.mkstate_concrete_return_of(stmt, 0)
        s_failure = self.state.mkstate_concrete_return_of(stmt, -1)
        # (no way to get the exception on failure)
        # (FIXME: handle the potential autoclosing of the FILE*)
        return self.state.make_transitions_for_fncall(stmt, s_success, s_failure)

    def impl_PyRun_SimpleStringFlags(self, stmt, v_command, v_flags):
        # http://docs.python.org/c-api/veryhigh.html#PyRun_SimpleStringFlags
        s_success = self.state.mkstate_concrete_return_of(stmt, 0)
        s_failure = self.state.mkstate_concrete_return_of(stmt, -1)
        # (no way to get the exception on failure)
        return self.state.make_transitions_for_fncall(stmt, s_success, s_failure)

    ########################################################################
    # PySequence_*
    ########################################################################
    def impl_PySequence_GetItem(self, stmt, v_o, v_i):
        # http://docs.python.org/c-api/sequence.html#PySequence_GetItem
        # Declared in abstract.h:
        #   PyAPI_FUNC(PyObject *) PySequence_GetItem(PyObject *o, Py_ssize_t i);
        #
        # Defined in Objects/abstract.c:
        #   PyObject *
        #   PySequence_GetItem(PyObject *s, Py_ssize_t i)
        #   {
        #      [... setup and error handling ...]
        #      return m->sq_item(s, i);
        #   }
        #
        # When it succeeds, it returns a new reference; see e.g.
        # Objects/listobject.c: list_item (the sq_item callback for
        # PyList_Type): it Py_INCREFs the returned item.
        fnname = 'PySequence_GetItem'
        return self.make_transitions_for_new_ref_or_fail(stmt,
                                                         'new ref from %s' % fnname)

    ########################################################################
    # PyString_*
    ########################################################################
    def impl_PyString_AsString(self, stmt, v_op):
        # Declared in stringobject.h as:
        #   PyAPI_FUNC(char *) PyString_AsString(PyObject *);
        # Implemented in Objects/stringobject.c
        #
        #  http://docs.python.org/c-api/string.html#PyString_AsString
        #
        # With PyStringObject and their subclasses, it returns
        #    ((PyStringObject *)op) -> ob_sval
        # With other classes, this call can fail

        # It will segfault if called with NULL, since it uses PyString_Check,
        # which reads through the object's ob_type:
        self.state.raise_any_null_ptr_func_arg(stmt, 0, v_op)

        returntype = stmt.fn.type.dereference.type

        if self.object_ptr_has_global_ob_type(v_op, 'PyString_Type'):
            # We know it's a PyStringObject; the call will succeed:
            # FIXME: cast:
            r_ob_sval = self.state.make_field_region(v_op.region, 'ob_sval')
            v_result = PointerToRegion(returntype, stmt.loc, r_ob_sval)
            t_success = self.state.mktrans_assignment(stmt.lhs,
                                                v_result,
                                                'PyString_AsString() returns ob_sval')
            return [t_success]

        # We don't know if it's a PyStringObject (or subclass); the call could
        # fail:
        r_nonnull = self.state.make_heap_region('buffer from PyString_AsString()', stmt)
        v_success = PointerToRegion(returntype, stmt.loc, r_nonnull)
        t_success = self.state.mktrans_assignment(stmt.lhs,
                                            v_success,
                                            'when PyString_AsString() succeeds')
        t_failure = self.state.mktrans_assignment(stmt.lhs,
                                            ConcreteValue(returntype, stmt.loc, 0),
                                            'when PyString_AsString() fails')
        t_failure.dest.cpython.set_exception('PyExc_MemoryError', stmt.loc)
        return [t_success, t_failure]

    def impl_PyString_FromFormat(self, stmt, v_fmt, *v_args):
        # Declared in stringobject.h as:
        #   PyAPI_FUNC(PyObject *) PyString_FromFormat(const char*, ...)
        #                             Py_GCC_ATTRIBUTE((format(printf, 1, 2)));
        # Returns a new reference
        #   http://docs.python.org/c-api/string.html#PyString_FromFormat
        #
        # (We do not yet check that the format string matches the types of the
        # varargs)
        r_newobj, t_success, t_failure = self.object_ctor(stmt,
                                                          'PyStringObject',
                                                          'PyString_Type')
        return [t_success, t_failure]

    def impl_PyString_FromString(self, stmt, v_str):
        # Declared in stringobject.h as:
        #   PyAPI_FUNC(PyObject *) PyString_FromString(const char *);
        #
        #   http://docs.python.org/c-api/string.html#PyString_FromString
        #

        # The input _must_ be non-NULL; it is not checked:
        self.state.raise_any_null_ptr_func_arg(stmt, 0, v_str)

        r_newobj, t_success, t_failure = self.object_ctor(stmt,
                                                          'PyStringObject',
                                                          'PyString_Type')
        return [t_success, t_failure]

    def impl_PyString_FromStringAndSize(self, stmt, v_str, v_size):
        # Declared in stringobject.h as:
        #   PyAPI_FUNC(PyObject *) PyString_FromStringAndSize(const char *, Py_ssize_t);
        #
        # http://docs.python.org/c-api/string.html#PyString_FromStringAndSize
        #
        # Defined in Objects/stringobject.c:
        #   # PyObject *
        #   PyString_FromStringAndSize(const char *str, Py_ssize_t size)

        # v_str, v_size = self.state.eval_stmt_args(stmt)
        # (the input can legitimately be NULL)

        r_newobj, t_success, t_failure = self.object_ctor(stmt,
                                                          'PyStringObject',
                                                          'PyString_Type')
        return [t_success, t_failure]

    ########################################################################
    # PyStructSequence_*
    ########################################################################
    def impl_PyStructSequence_InitType(self, stmt, v_type, v_desc):
        # void PyStructSequence_InitType(PyTypeObject *type, PyStructSequence_Desc *desc)
        #
        # Implemented in Objects/structseq.c
        # For now, treat it as a no-op:
        return [self.state.mktrans_nop(stmt, 'PyStructSequence_InitType')]

    def impl_PyStructSequence_New(self, stmt, v_typeptr):
        # Declared in structseq.h as:
        #   PyAPI_FUNC(PyObject *) PyStructSequence_New(PyTypeObject* type);
        #
        # Implemented in Objects/structseq.c

        # From our perspective, this is very similar to _PyObject_New
        check_isinstance(stmt, gcc.GimpleCall)
        check_isinstance(stmt.fn.operand, gcc.FunctionDecl)

        # Success case: allocation and assignment:
        s_success, nonnull = self.mkstate_new_ref(stmt, 'PyStructSequence_New')
        # ...and set up ob_type on the result object:
        ob_type = s_success.make_field_region(nonnull, 'ob_type')
        s_success.value_for_region[ob_type] = v_typeptr
        t_success = Transition(self.state,
                             s_success,
                             'when PyStructSequence_New() succeeds')
        # Failure case:
        t_failure = self.state.mktrans_assignment(stmt.lhs,
                                       ConcreteValue(stmt.lhs.type, stmt.loc, 0),
                                       'when PyStructSequence_New() fails')
        t_failure.dest.cpython.set_exception('PyExc_MemoryError', stmt.loc)
        return [t_success, t_failure]

    ########################################################################
    # PySys_*
    ########################################################################
    def impl_PySys_SetObject(self, stmt, v_name, v_value):
        # Declated in sysmodule.h
        # Defined in Python/sysmodule.c:
        #   int PySys_SetObject(char *name, PyObject *v)
        # Docs:
        #   http://docs.python.org/c-api/sys.html#PySys_SetObject
        #
        # can be called with NULL or non-NULL, calls PyDict_SetItemString
        # on non-NULL, which adds a ref on it
        fnname = 'PySys_SetObject'
        returntype = stmt.fn.type.dereference.type
        t_success = self.state.mktrans_assignment(stmt.lhs,
                                            ConcreteValue(returntype, stmt.loc, 0),
                                            'when %s() succeeds' % fnname)
        if isinstance(v_value, PointerToRegion):
            t_success.dest.cpython.add_external_ref(v_value, stmt.loc)
        t_failure = self.state.mktrans_assignment(stmt.lhs,
                                            ConcreteValue(returntype, stmt.loc, -1),
                                            'when %s() fails' % fnname)
        t_failure.dest.cpython.set_exception('PyExc_MemoryError', stmt.loc)
        return [t_success, t_failure]

    ########################################################################
    # PyTuple_*
    ########################################################################
    def impl_PyTuple_New(self, stmt, v_len):
        # http://docs.python.org/c-api/tuple.html#PyTuple_New

        r_newobj, t_success, t_failure = self.object_ctor(stmt,
                                                          'PyTupleObject',
                                                          'PyTuple_Type')
        # Set ob_size:
        r_ob_size = t_success.dest.make_field_region(r_newobj, 'ob_size')
        t_success.dest.value_for_region[r_ob_size] = v_len
        return [t_success, t_failure]

    def impl_PyTuple_SetItem(self, stmt, v_op, v_i, v_newitem):
        # http://docs.python.org/c-api/tuple.html#PyTuple_SetItem
        # Implemented in Objects/tupleobject.c
        fnname = 'PyTuple_SetItem'
        returntype = stmt.fn.type.dereference.type

        # The CPython implementation uses PyTuple_Check, which uses
        # Py_TYPE(op), an unchecked read through the ptr:
        self.state.raise_any_null_ptr_func_arg(stmt, 0, v_op)

        # i is range checked
        # newitem can safely be NULL

        result = []

        # Check that it's a tuple:
        if not self.object_ptr_has_global_ob_type(v_op, 'PyTuple_Type'):
            # FIXME: Py_XDECREF on newitem
            s_failure = self.state.mkstate_concrete_return_of(stmt, -1)
            s_failure.cpython.bad_internal_call(stmt.loc)
            result.append(Transition(self.state,
                                     s_failure,
                                     'when PyTuple_SetItem fails (not a tuple)'))

        # Check that refcount is 1 (mutation during initial creation):
        v_ob_refcnt = self.state.get_value_of_field_by_region(v_op.region,
                                                              'ob_refcnt')
        # Because of the way we store RefcountValue instances, we can't
        # easily prove that the refcount == 1, so only follow this path
        # if we can prove that refcount != 1
        eq_one = v_ob_refcnt.is_equal(ConcreteValue.from_int(1))
        if eq_one is False: # tri-state
            # FIXME: Py_XDECREF on newitem
            s_failure = self.state.mkstate_concrete_return_of(stmt, -1)
            s_failure.cpython.bad_internal_call(stmt.loc)
            result.append(Transition(self.state,
                                     s_failure,
                                     'when PyTuple_SetItem fails (refcount is not 1)'))
            # It's known that no further outcomes are possible:
            return result

        # Range check:
        v_ob_size = self.state.get_value_of_field_by_region(v_op.region,
                                                            'ob_size')

        lt_zero = v_i.is_lt(ConcreteValue.from_int(0))
        lt_size = v_i.is_lt(v_ob_size)
        # The above could be None: signifying that we don't know, and that
        # False is possible.  Out-of-range is possible if either aren't known
        # to be non-False:
        if lt_zero is not False or lt_size is not True:
            s_failure = self.state.mkstate_concrete_return_of(stmt, -1)
            s_failure.cpython.set_exception('PyExc_IndexError', stmt.loc)
            result.append(Transition(self.state,
                                     s_failure,
                                     'when PyTuple_SetItem fails (index out of range)'))

        # Within range is only possible if both boundaries are known to not
        # definitely be wrong:
        if lt_zero is not True and lt_size is not False:
            s_success = self.state.mkstate_concrete_return_of(stmt, 0)
            r_ob_item = s_success.make_field_region(v_op.region, 'ob_item')
            r_indexed = s_success._array_region(r_ob_item, v_i)
            # v_olditem = s_success.value_for_region[r_indexed]
            # FIXME: it does an XDECREF on the olditem
            s_success.value_for_region[r_indexed] = v_newitem

            result.append(Transition(self.state,
                                     s_success,
                                     'when PyTuple_SetItem succeeds'))

        return result


    def impl_PyTuple_Size(self, stmt, v_op):
        # http://docs.python.org/c-api/tuple.html#PyTuple_Size
        # Implemented in Objects/tupleobject.c
        fnname = 'PyTuple_Size'
        returntype = stmt.fn.type.dereference.type

        # The CPython implementation uses PyTuple_Check, which uses
        # Py_TYPE(op), an unchecked read through the ptr:
        self.state.raise_any_null_ptr_func_arg(stmt, 0, v_op)

        # FIXME: cast:
        v_ob_size = self.state.get_value_of_field_by_region(v_op.region,
                                                      'ob_size')
        t_success = self.state.mktrans_assignment(stmt.lhs,
                                            v_ob_size,
                                            'when PyTuple_Size() returns ob_size')

        if self.object_ptr_has_global_ob_type(v_op, 'PyTuple_Type'):
            # We know it's a PyTupleObject; the call will succeed:
            return [t_success]

        # Can fail if not a tuple:
        # (For now, ignore the fact that it could be a tuple subclass)

        s_failure = self.state.mkstate_concrete_return_of(stmt, -1)
        s_failure.cpython.set_exception('PyExc_SystemError', stmt.loc)
        t_failure = Transition(self.state,
                               s_failure,
                               'when %s() fails (not a tuple)' % fnname)
        return [t_success, t_failure]

    ########################################################################
    # PyType_*
    ########################################################################
    def impl_PyType_IsSubtype(self, stmt, v_a, v_b):
        # http://docs.python.org/dev/c-api/type.html#PyType_IsSubtype
        returntype = stmt.fn.type.dereference.type
        return [self.state.mktrans_assignment(stmt.lhs,
                                        UnknownValue.make(returntype, stmt.loc),
                                        None)]

    def impl_PyType_Ready(self, stmt, v_type):
        #  http://docs.python.org/dev/c-api/type.html#PyType_Ready
        s_success = self.state.mkstate_concrete_return_of(stmt, 0)

        s_failure = self.state.mkstate_concrete_return_of(stmt, -1)
        s_failure.cpython.set_exception('PyExc_MemoryError', stmt.loc) # various possible errors

        return self.state.make_transitions_for_fncall(stmt, s_success, s_failure)


    ########################################################################
    # (end of Python API implementations)
    ########################################################################

def get_traces(fun):
    return list(iter_traces(fun,
                            {'cpython':CPython},
                            limits=Limits(maxtrans=1024)))


def dump_traces_to_stdout(traces):
    """
    For use in selftests: dump the traces to stdout, in a form that (hopefully)
    will allow usable comparisons against "gold" output ( not embedding
    anything that changes e.g. names of temporaries, address of wrapper
    objects, etc)
    """
    def dump_object(rvalue, title):
        check_isinstance(rvalue, AbstractValue)
        print('  %s:' % title)
        print('    repr(): %r' % rvalue)
        print('    str(): %s' % rvalue)
        if isinstance(rvalue, PointerToRegion):
            print('    r->ob_refcnt: %s'
                  % endstate.get_value_of_field_by_region(rvalue.region, 'ob_refcnt'))
            print('    r->ob_type: %r'
                  % endstate.get_value_of_field_by_region(rvalue.region, 'ob_type'))

    def dump_region(region, title):
        check_isinstance(region, Region)
        print('  %s:' % title)
        print('    repr(): %r' % region)
        print('    str(): %s' % region)
        print('    r->ob_refcnt: %s'
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
        if hasattr(endstate, 'cpython'):
            print('  Exception:')
            print('    %s' % endstate.cpython.exception_rvalue)

        if i + 1 < len(traces):
            sys.stdout.write('\n')

class DebugAnnotator(Annotator):
    """
    Annotate a trace with copious debug information
    """
    def get_notes(self, transition):
        loc = transition.src.get_gcc_loc_or_none()
        if loc is None:
            # (we can't add a note without a valid location)
            return []

        result = []

        # Add refcount information on all PyObject*
        for k in transition.dest.region_for_var:
            region = transition.dest.region_for_var[k]
            check_isinstance(region, Region)
            if 'ob_refcnt' not in region.fields:
                continue
            ra = RefcountAnnotator(region,
                                   region.name)
            result += ra.get_notes(transition)

        # Show all new/changing regions:
        for region in transition.dest.value_for_region:
            dest_value = transition.dest.value_for_region[region]
            if region in transition.src.value_for_region:
                src_value = transition.src.value_for_region[region]
                if dest_value != src_value:
                    result.append(Note(loc,
                                       ('%s now has value: %s'
                                        % (region, dest_value))))
            else:
                result.append(Note(loc,
                                   ('%s has initial value: %s'
                                    % (region, dest_value))))

        # Show exception information:
        esa = ExceptionStateAnnotator()
        result += esa.get_notes(transition)

        return result


class RefcountAnnotator(Annotator):
    """
    Annotate a trace with information on the reference count of a particular
    object
    """
    def __init__(self, region, desc):
        check_isinstance(region, Region)
        check_isinstance(desc, str)
        self.region = region
        self.desc = desc

    def get_notes(self, transition):
        """
        Add a note to every transition that affects reference-counting for
        our target object
        """
        loc = transition.src.get_gcc_loc_or_none()
        if loc is None:
            # (we can't add a note without a valid location)
            return []

        result = []

        # Add a note when the ob_refcnt of the object changes:
        src_refcnt = transition.src.get_value_of_field_by_region(self.region,
                                                                 'ob_refcnt')
        dest_refcnt = transition.dest.get_value_of_field_by_region(self.region,
                                                                   'ob_refcnt')
        if src_refcnt != dest_refcnt:
            log('src_refcnt: %r', src_refcnt)
            log('dest_refcnt: %r', dest_refcnt)
            result.append(Note(loc,
                               ('ob_refcnt is now %s' % dest_refcnt)))

        # Add a note when there's a change to the set of persistent storage
        # locations referencing this object:
        src_refs = transition.src.get_persistent_refs_for_region(self.region)
        dest_refs = transition.dest.get_persistent_refs_for_region(self.region)
        if src_refs != dest_refs:
            result.append(Note(loc,
                               ('%s is now referenced by %i non-stack value(s): %s'
                                % (self.desc,
                                   len(dest_refs),
                                   ', '.join([ref.name for ref in dest_refs])))))

        if 0:
            # For debugging: show the history of all references to the given
            # object:
            src_refs = transition.src.get_all_refs_for_region(self.region)
            dest_refs = transition.dest.get_all_refs_for_region(self.region)
            if src_refs != dest_refs:
                result.append(Note(loc,
                                   ('all refs: %s' % dest_refs)))
        return result

class ExceptionStateAnnotator(Annotator):
    """
    Annotate a trace with information on changes to the thread-local exception
    state
    """
    def get_notes(self, transition):
        """
        Add a note to every transition that affects thread-local exception
        state
        """
        loc = transition.src.get_gcc_loc_or_none()
        if loc is None:
            # (we can't add a note without a valid location)
            return []

        result = []

        if hasattr(transition.dest, 'cpython'):
            if transition.dest.cpython.exception_rvalue != transition.src.cpython.exception_rvalue:
                result.append(Note(loc,
                                   ('thread-local exception state now has value: %s'
                                    % transition.dest.cpython.exception_rvalue)))

        return result

def check_refcounts(fun, dump_traces=False, show_traces=False,
                    show_possible_null_derefs=False,
                    show_timings=False):
    """
    The top-level function of the refcount checker, checking the refcounting
    behavior of a function

    fun: the gcc.Function to be checked

    dump_traces: bool: if True, dump information about the traces through
    the function to stdout (for self tests)

    show_traces: bool: if True, display a diagram of the state transition graph

    show_timings: bool: if True, add timing information to stderr
    """
    # Abstract interpretation:
    # Walk the CFG, gathering the information we're interested in

    log('check_refcounts(%r, %r, %r)', fun, dump_traces, show_traces)

    # show_timings = 1

    if show_timings:
        import time
        start_cpusecs = time.clock()
        gcc.inform(fun.start, 'Analyzing reference-counting within %s' % fun.decl.name)

    check_isinstance(fun, gcc.Function)

    # Generate a mapping from facet names to facet classes, so that we know
    # what additional attributes each State instance will have.
    #
    # For now, we just have an optional CPython instance per state, but only
    # for code that's included Python's headers:
    facets = {}
    if get_PyObject():
        facets['cpython'] = CPython

    if show_traces:
        from libcpychecker.visualizations import StateGraphPrettyPrinter
        sg = StateGraph(fun, log, MyState)
        sgpp = StateGraphPrettyPrinter(sg)
        dot = sgpp.to_dot()
        #dot = sgpp.extra_items()
        # print(dot)
        invoke_dot(dot)

    limits=Limits(maxtrans=1024)

    try:
        traces = iter_traces(fun,
                             facets,
                             limits=limits)
    except TooComplicated:
        gcc.inform(fun.start,
                   'this function is too complicated for the reference-count checker to analyze')
        return

    if dump_traces:
        traces = list(traces)
        dump_traces_to_stdout(traces)

    # Debug dump of all traces in HTML form:
    if 0:
        filename = ('%s.%s-refcount-traces.html'
                    % (gcc.get_dump_base_name(), fun.decl.name))
        rep = Reporter()
        for i, trace in enumerate(traces):
            endstate = trace.states[-1]
            r = rep.make_debug_dump(fun,
                                    endstate.get_gcc_loc(fun),
                                    'Debug dump of trace %i' % i)
            r.add_trace(trace, DebugAnnotator())
        rep.dump_html(fun, filename)
        gcc.inform(fun.start,
                   ('graphical debug report for function %r written out to %r'
                    % (fun.decl.name, filename)))

    rep = Reporter()

    for i, trace in enumerate(traces):
        trace.log(log, 'TRACE %i' % i)
        if trace.err:
            # This trace bails early with a fatal error; it probably doesn't
            # have a return value
            log('trace.err: %s %r', trace.err, trace.err)

            # Unless explicitly enabled, don't report on NULL pointer
            # dereferences that are only possible, not definite: it may be
            # that there are invariants that we know nothing about that mean
            # that they can't happen:
            if isinstance(trace.err, NullPtrDereference):
                if not trace.err.isdefinite:
                    if not show_possible_null_derefs:
                        continue

            err = rep.make_error(fun, trace.err.loc, str(trace.err))
            err.add_trace(trace)
            # FIXME: in our example this ought to mention where the values came from
            continue
        # Otherwise, the trace proceeds normally
        return_value = trace.return_value()
        log('trace.return_value(): %s', trace.return_value())

        # Ideally, we should "own" exactly one reference, and it should be
        # the return value.  Anything else is an error (and there are other
        # kinds of error...)

        # Locate all PyObject that we touched
        endstate = trace.states[-1]
        endstate.log(log)
        log('return_value: %r', return_value)
        log('endstate.region_for_var: %r', endstate.region_for_var)
        log('endstate.value_for_region: %r', endstate.value_for_region)

        # Consider all regions of memory we know about:
        for k in endstate.region_for_var:
            if not isinstance(endstate.region_for_var[k], Region):
                continue
            region = endstate.region_for_var[k]

            log('considering ob_refcnt of %r', region)
            check_isinstance(region, Region)

            # Consider those for which we know something about an "ob_refcnt"
            # field:
            if 'ob_refcnt' not in region.fields:
                continue

            ob_refcnt = endstate.get_value_of_field_by_region(region,
                                                              'ob_refcnt')
            log('ob_refcnt: %r', ob_refcnt)

            # If it's the return value, it should have a net refcnt delta of
            # 1; all other PyObject should have a net delta of 0:
            if isinstance(return_value, PointerToRegion) and region == return_value.region:
                desc = 'return value'
                if fun.decl.name in fnnames_returning_borrowed_refs:
                    # ...then this function has been marked as returning a
                    # borrowed reference, rather than a new one:
                    exp_refs = []
                else:
                    exp_refs = ['return value']
            else:
                # Try to get a descriptive name for the region:
                desc = trace.get_description_for_region(region)
                # print('desc: %r' % desc)
                exp_refs = []

            # The reference count should also reflect any non-stack pointers
            # that point at this object:
            exp_refs += [ref.name
                         for ref in endstate.get_persistent_refs_for_region(region)]
            exp_refcnt = len(exp_refs)
            log('exp_refs: %r', exp_refs)

            # Helper function for when ob_refcnt is wrong:
            def emit_refcount_error(msg):
                err = rep.make_error(fun, endstate.get_gcc_loc(fun), msg)
                err.add_note(endstate.get_gcc_loc(fun),
                             ('was expecting final ob_refcnt to be N + %i (for some unknown N)'
                              % exp_refcnt))
                if exp_refcnt > 0:
                    err.add_note(endstate.get_gcc_loc(fun),
                                 ('due to object being referenced by: %s'
                                  % ', '.join(exp_refs)))
                err.add_note(endstate.get_gcc_loc(fun),
                             ('but final ob_refcnt is N + %i'
                              % ob_refcnt.relvalue))
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
                if 1:
                    annotator = RefcountAnnotator(region, desc)
                else:
                    # Debug help:
                    from libcpychecker.diagnostics import TestAnnotator
                    annotator = TestAnnotator()
                err.add_trace(trace, annotator)

                if 0:
                    # Handy for debugging:
                    err.add_note(endstate.get_gcc_loc(fun),
                                 'this was trace %i' % i)
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
                    if return_value:
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

                if (isinstance(endstate.cpython.exception_rvalue,
                              ConcreteValue)
                    and endstate.cpython.exception_rvalue.value == 0):
                    err = rep.make_error(fun,
                                         endstate.get_gcc_loc(fun),
                                         'returning (PyObject*)NULL without setting an exception')
                    err.add_trace(trace, ExceptionStateAnnotator())

    # (all traces analysed)

    if rep.got_errors():
        filename = ('%s.%s-refcount-errors.html'
                    % (gcc.get_dump_base_name(), fun.decl.name))
        rep.dump_html(fun, filename)
        gcc.inform(fun.start,
                   ('graphical error report for function %r written out to %r'
                    % (fun.decl.name, filename)))

    if show_timings:
        end_cpusecs = time.clock()
        gcc.inform(fun.start, 'Finished analyzing reference-counting within %s' % fun.decl.name)
        gcc.inform(fun.start,
                   ('%i transitions, %fs CPU'
                    % (limits.trans_seen, end_cpusecs - start_cpusecs)))

    if 0:
        dot = cfg_to_dot(fun.cfg, fun.decl.name)
        invoke_dot(dot)


