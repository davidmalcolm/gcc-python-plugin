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
import gccutils
import sys
from six import StringIO, integer_types
from gccutils import get_src_for_loc, get_nonnull_arguments, check_isinstance
from collections import OrderedDict
from libcpychecker.utils import log, logging_enabled
from libcpychecker.types import *

numeric_types = integer_types + (float, )

# I found myself regularly getting State and Transition instances confused.  To
# ameliorate that, here are some naming conventions and abbreviations:
#
# Within method names:
#   "mktrans_" means "make a Transition"
#   "mkstate_" means "make a State"
#
# Within variable names
#   the prefix "t_" means a Transition
#   the prefix "s_" means a State
#   the prefix "v_" means an AbstractValue
#   the prefix "r_" means a Region
#   the prefix "f_" means a Facet

############################################################################
# Various kinds of r-value:
############################################################################

class AbstractValue(object):
    """
    Base class, representing some subset of possible values out of the full
    set of values that this r-value could hold.
    """
    __slots__ = ('gcctype', 'loc', 'fromsplit')

    def __init__(self, gcctype, loc):
        if gcctype:
            check_isinstance(gcctype, gcc.Type)
        if loc:
            check_isinstance(loc, gcc.Location)
        self.gcctype = gcctype
        self.loc = loc

    def __str__(self):
        if self.gcctype:
            result = '%s' % self.gcctype
        else:
            result = 'unknown type'
        if self.loc:
            result += ' from %s' % self.loc
        return result

    def __repr__(self):
        return ('%s(gcctype=%r, loc=%r)'
                % (self.__class__.__name__, str(self.gcctype), self.loc))

    def get_transitions_for_function_call(self, state, stmt):
        """
        For use for handling function pointers.  Return a list of Transition
        instances giving the outcome of calling this function ptr value
        """
        check_isinstance(state, State)
        check_isinstance(stmt, gcc.GimpleCall)
        returntype = stmt.fn.type.dereference.type

        if str(returntype) == 'struct PyObject *':
            log('Invocation of function pointer returning PyObject *')
            # Assume that all such functions either:
            #   - return a new reference, or
            #   - return NULL and set an exception (e.g. MemoryError)
            return state.cpython.make_transitions_for_new_ref_or_fail(stmt,
                                                                      'new ref from call through function pointer')
        return state.apply_fncall_side_effects(
            [state.mktrans_assignment(stmt.lhs,
                                      UnknownValue.make(returntype, stmt.loc),
                                      'calling %s' % self)],
            stmt)

    def eval_unary_op(self, exprcode, gcctype, loc):
        if exprcode == gcc.ConvertExpr:
            raise NotImplementedError("Don't know how to cope with type conversion of: %r (%s) at %s to type %s"
                                      % (self, self, loc, gcctype))
        else:
            raise NotImplementedError("Don't know how to cope with exprcode: %r (%s) on %s at %s"
                                      % (exprcode, exprcode, self, loc))

    def eval_binop(self, exprcode, rhs, gcctype, loc):
        raise NotImplementedError

    def is_equal(self, rhs):
        """
        Return a boolean, or None (meaning we don't know)
        """
        raise NotImplementedError("is_equal for %s" % self)

    def is_lt(self, rhs):
        """
        "lt" = "less-than"
        Return a boolean, or None (meaning we don't know)
        """
        # First try "less-than":
        lt_result = self.impl_is_lt(rhs)
        if lt_result is not None:
            return lt_result
        # We don't know; try the other way around:
        ge_result = rhs.impl_is_ge(self)
        if ge_result is not None:
            return not ge_result
        # We don't know:
        return None

    def is_le(lhs, rhs):
        # "less-than-or-equal"
        # This is the default implementation, using is_equal() and is_lt(),
        # but subclasses can override this if needed

        # First try "less-than":
        lt_result = lhs.is_lt(rhs)
        if lt_result is not None:
            if lt_result:
                return True
        # Either not less than, or we don't know
        # Try equality:
        eq_result = lhs.is_equal(rhs)
        if eq_result is not None:
            if eq_result:
                # Definitely equal:
                return eq_result
            else:
                # Definitely not equal
                # If we have a definite result for less-than, use it:
                if lt_result is not None:
                    return lt_result
        # We don't know:
        return None

    def impl_is_lt(self, rhs):
        """
        "lt" = "less-than"
        Return a boolean, or None (meaning we don't know)
        """
        raise NotImplementedError("impl_is_lt for %s (with %s)" % (self, rhs))

    def impl_is_ge(self, rhs):
        """
        "ge" = "greater-than-or-equal"
        Return a boolean, or None (meaning we don't know)
        """
        raise NotImplementedError("impl_is_ge for %s (with %s" % (self, rhs))

    def extract_from_parent(self, region, gcctype, loc):
        """
        Called on a parent when inheriting a value from it for a child region,
        for example, when a whole struct has "UnknownValue", we can extract
        a particular field, giving an UnknownValue of the appropriate type
        """
        raise NotImplementedError('%s.extract_from_parent(%s, %s, %s)'
                                  % (self.__class__.__name__, region, gcctype, loc))

    def as_string_constant(self):
        """
        If this is a pointer to a string constant, return the underlying
        string, otherwise return None
        """
        if isinstance(self, PointerToRegion):
            if isinstance(self.region, RegionForStringConstant):
                return self.region.text
            # We could be dealing with e.g. char *ptr = "hello world";
            # where "hello world" is a 'char[12]', and thus ptr has been
            # assigned a char* pointing to '"hello world"[0]'
            if isinstance(self.region, ArrayElementRegion):
                if isinstance(self.region.parent, RegionForStringConstant):
                    return self.region.parent.text[self.region.index:]
        # Otherwise, not a string constant, return None

    def union(self, v_other):
        check_isinstance(v_other, AbstractValue)
        raise NotImplementedError('%s.union(%s, %s)'
                                  % (self.__class__.__name__, v_other))

class EmptySet(AbstractValue):
    """
    The empty set: there are no possible values for this variable (yet).
    """
    def union(self, v_other):
        check_isinstance(v_other, AbstractValue)
        return v_other

class UnknownValue(AbstractValue):
    """
    A value that we know nothing about: it could be any of the possible values
    """
    @classmethod
    def make(cls, gcctype, loc):
        """
        For some types, we may be able to supply more information
        """
        if gcctype:
            check_isinstance(gcctype, gcc.Type)
        if loc:
            check_isinstance(loc, gcc.Location)
        if gcctype:
            if isinstance(gcctype, gcc.IntegerType):
                # Supply range limits for integer types, from the type itself:
                return WithinRange(gcctype, loc,
                                   gcctype.min_value.constant,
                                   gcctype.max_value.constant)
        return UnknownValue(gcctype, loc)

    def __str__(self):
        if self.gcctype:
            return 'unknown %s from %s' % (self.gcctype, self.loc)
        else:
            if self.loc:
                return 'unknown value from %s' % self.loc
            else:
                return 'unknown value'

    def __repr__(self):
        return 'UnknownValue(gcctype=%r, loc=%r)' % (self.gcctype, self.loc)

    def eval_unary_op(self, exprcode, gcctype, loc):
        return UnknownValue.make(gcctype, loc)

    def eval_binop(self, exprcode, rhs, gcctype, loc):
        return UnknownValue.make(gcctype, loc)

    def is_equal(self, rhs):
        return None

    def impl_is_lt(self, rhs):
        return None

    def impl_is_ge(self, rhs):
        return None

    def extract_from_parent(self, region, gcctype, loc):
        return UnknownValue.make(gcctype, loc)

    def union(self, v_other):
        check_isinstance(v_other, AbstractValue)
        return self

def eval_binop(exprcode, a, b):
    """
    Evaluate a gcc exprcode on a pair of Python values (as opposed to
    AbstractValue instances)
    """
    log('eval_binop(%s, %s, %s)', exprcode, a, b)
    assert isinstance(a, numeric_types)
    assert isinstance(b, numeric_types)

    def inner():
        if exprcode == gcc.PlusExpr:
            return a + b
        elif exprcode == gcc.MinusExpr:
            return a - b
        elif exprcode == gcc.MultExpr:
            return a * b
        elif exprcode == gcc.TruncDivExpr:
            return a // b
        elif exprcode == gcc.TruncModExpr:
            return a % b
        elif exprcode == gcc.MaxExpr:
            return max(a, b)
        elif exprcode == gcc.MinExpr:
            return min(a, b)
        elif exprcode == gcc.BitIorExpr:
            return a | b
        elif exprcode == gcc.BitAndExpr:
            return a & b
        elif exprcode == gcc.BitXorExpr:
            return a ^ b
        elif exprcode == gcc.LshiftExpr:
            return a << b
        elif exprcode == gcc.RshiftExpr:
            return a >> b
        elif exprcode == gcc.TruthAndExpr:
            return a and b
        elif exprcode == gcc.TruthOrExpr:
            return a or b

        # (an implicit return of None means "did not know how to handle this
        # expression")

    result = inner()
    log('result: %s', result)
    assert isinstance(result, numeric_types)
    return result


class ConcreteValue(AbstractValue):
    """
    A known, specific value (e.g. 0)
    """
    __slots__ = ('value', )

    def __init__(self, gcctype, loc, value):
        check_isinstance(gcctype, gcc.Type)
        if loc:
            check_isinstance(loc, gcc.Location)
        check_isinstance(value, numeric_types)
        self.gcctype = gcctype
        self.loc = loc
        self.value = value

    @classmethod
    def from_int(self, value):
        return ConcreteValue(gcc.Type.int(), None, value)

    def __ne__(self, other):
        if isinstance(other, ConcreteValue):
            return self.value != other.value
        return NotImplemented

    def __str__(self):
        if self.loc:
            return '(%s)%r from %s' % (self.gcctype, self.value, self.loc)
        else:
            return '(%s)%r' % (self.gcctype, self.value)

    def __repr__(self):
        return 'ConcreteValue(gcctype=%r, loc=%r, value=%r)' % (str(self.gcctype), self.loc, self.value)

    def is_null_ptr(self):
        if isinstance(self.gcctype, gcc.PointerType):
            return self.value == 0

    def get_transitions_for_function_call(self, state, stmt):
        check_isinstance(state, State)
        check_isinstance(stmt, gcc.GimpleCall)

        class CallOfNullFunctionPtr(PredictedError):
            def __init__(self, stmt, value):
                check_isinstance(stmt, gcc.Gimple)
                check_isinstance(value, AbstractValue)
                self.stmt = stmt
                self.value = value

            def __str__(self):
                return ('call of NULL function pointer at %s: %s'
                        % (self.stmt.loc, self.value))

        if self.is_null_ptr():
            raise CallOfNullFunctionPtr(stmt, self)

        return AbstractValue.get_transitions_for_function_call(self, state, stmt)

    def eval_unary_op(self, exprcode, gcctype, loc):
        if exprcode == gcc.AbsExpr:
            return ConcreteValue(gcctype, loc, abs(self.value))
        elif exprcode == gcc.BitNotExpr:
            # FIXME: bitwise-complement, with the correct width
            #   self.gcctype.precision
            return ConcreteValue(gcctype, loc, ~self.value)
        elif exprcode == gcc.NegateExpr:
            return ConcreteValue(gcctype, loc, -self.value)
        elif exprcode == gcc.ConvertExpr:
            # Is this value expressible within the new type?
            # If not, we might lose information
            if isinstance(self.gcctype, gcc.IntegerType):
                if (self.value >= gcctype.min_value.constant
                    and self.value <= gcctype.max_value.constant):
                    # The old range will convert OK to the new type:
                    return ConcreteValue(gcctype, loc, self.value)
            # We might lose information e.g. truncation; be pessimistic for now:
            return UnknownValue.make(gcctype, loc)
        else:
            raise NotImplementedError("Don't know how to cope with exprcode: %r (%s) on %s at %s"
                                      % (exprcode, exprcode, self, loc))

    def eval_binop(self, exprcode, rhs, gcctype, loc):
        if isinstance(rhs, ConcreteValue):
            newvalue = eval_binop(exprcode, self.value, rhs.value)
            if newvalue is not None:
                return ConcreteValue(gcctype, loc, newvalue)
        return UnknownValue.make(gcctype, loc)

    def is_equal(self, rhs):
        if isinstance(rhs, ConcreteValue):
            log('comparing concrete values: %s %s', self, rhs)
            return self.value == rhs.value
        return None

    def impl_is_lt(self, rhs):
        if isinstance(rhs, ConcreteValue):
            log('comparing concrete values: %s %s', self, rhs)
            return self.value < rhs.value
        return None

    def impl_is_ge(self, rhs):
        if isinstance(rhs, ConcreteValue):
            log('comparing concrete values: %s %s', self, rhs)
            return self.value >= rhs.value
        return None

    def extract_from_parent(self, region, gcctype, loc):
        return ConcreteValue(gcctype, loc, self.value)

    def union(self, v_other):
        check_isinstance(v_other, AbstractValue)
        if isinstance(v_other, ConcreteValue):
            if self.value == v_other.value:
                return self
            return WithinRange(self.gcctype, self.loc,
                               self.value, v_other.value)
        if isinstance(v_other, WithinRange):
            return WithinRange(self.gcctype, self.loc,
                               *(self.value, v_other.minvalue, v_other.maxvalue))
        raise NotImplementedError('%s.union(%s)'
                                  % (self.__class__.__name__, v_other))

def value_to_str(value):
    """
    Display large integers/longs in hexadecimal, since it's easier
    to decipher
       -0x8000000000000000
    than
       -9223372036854775808
    """
    check_isinstance(value, numeric_types)

    if isinstance(value, integer_types):
        if abs(value) > 0x100000:
            return hex(value)
    return str(value)

class WithinRange(AbstractValue):
    """
    A value known to be within a given range e.g. -3 <= val <= +4
    """
    __slots__ = ('minvalue', 'maxvalue', )

    def __init__(self, gcctype, loc, *values):
        """
        The constructor can take one or more values; the resulting set
        is the minimal range covering all of the input values,
        For example,
           WithinRange(gcctype, loc, 7, 4, -4, -2)
        will give the range -2 <= val < 7
        """
        check_isinstance(gcctype, gcc.Type)
        if loc:
            check_isinstance(loc, gcc.Location)
        assert len(values) >= 1
        for value in values:
            check_isinstance(value, numeric_types)
        self.gcctype = gcctype
        self.loc = loc
        self.minvalue = min(values)
        self.maxvalue = max(values)

    def __str__(self):
        if self.loc:
            return ('(%s)val [%s <= val <= %s] from %s'
                    % (self.gcctype, value_to_str(self.minvalue),
                       value_to_str(self.maxvalue), self.loc))
        else:
            return ('(%s)val [%s <= val <= %s]'
                    % (self.gcctype, value_to_str(self.minvalue),
                       value_to_str(self.maxvalue)))

    def __repr__(self):
        return ('WithinRange(gcctype=%r, loc=%r, minvalue=%s, maxvalue=%s)'
                % (str(self.gcctype), self.loc, value_to_str(self.minvalue),
                   value_to_str(self.maxvalue)))

    def eval_unary_op(self, exprcode, gcctype, loc):
        if exprcode == gcc.AbsExpr:
            values = [abs(val)
                      for val in (self.minvalue, self.maxvalue)]
            return WithinRange(gcctype, loc, min(values), max(values))
        elif exprcode == gcc.BitNotExpr:
            return UnknownValue.make(gcctype, loc)
        elif exprcode == gcc.NegateExpr:
            return WithinRange(gcctype, loc, -self.maxvalue, -self.minvalue)
        elif exprcode == gcc.ConvertExpr:
            # Is the whole of this range fully expressible within the new type?
            # If not, we might lose information
            if isinstance(self.gcctype, gcc.IntegerType):
                if (self.minvalue >= gcctype.min_value.constant
                    and self.maxvalue <= gcctype.max_value.constant):
                    # The old range will convert OK to the new type:
                    return WithinRange(gcctype, loc,
                                       self.minvalue, self.maxvalue)
            # We might lose information e.g. truncation; be pessimistic for now:
            return UnknownValue.make(gcctype, loc)
        else:
            raise NotImplementedError("Don't know how to cope with exprcode: %r (%s) on %s at %s"
                                      % (exprcode, exprcode, self, loc))

    def eval_binop(self, exprcode, rhs, gcctype, loc):
        if isinstance(rhs, ConcreteValue):
            values = [eval_binop(exprcode, val, rhs.value)
                      for val in (self.minvalue, self.maxvalue)]
            return WithinRange(gcctype, loc, min(values), max(values))
        elif isinstance(rhs, WithinRange):
            # Assume that the operations are "concave" in that the resulting
            # range is within that found by trying all four corners:
            values = (eval_binop(exprcode, self.minvalue, rhs.minvalue),
                      eval_binop(exprcode, self.minvalue, rhs.maxvalue),
                      eval_binop(exprcode, self.maxvalue, rhs.minvalue),
                      eval_binop(exprcode, self.maxvalue, rhs.maxvalue))
            return WithinRange(gcctype, loc,
                               min(values),
                               max(values))
        return UnknownValue.make(gcctype, loc)

    def contains(self, rawvalue):
        return self.minvalue <= rawvalue and rawvalue <= self.maxvalue

    def is_equal(self, rhs):
        log('is_equal(%s, %s)', self, rhs)
        if isinstance(rhs, WithinRange):
            # They can only be equal if there's an overlap:
            if self.contains(rhs.minvalue) or self.contains(rhs.maxvalue):
                # Maybe equal:
                return None
            else:
                # No overlap: definitely non-equal:
                return False
        elif isinstance(rhs, ConcreteValue):
            if self.contains(rhs.value):
                # Maybe equal:
                return None
            else:
                # Definitely non-equal:
                return False
        return None

    def is_le(self, rhs):
        # Overridden implementation of AbstractValue.is_le, to better capture
        # the end conditions:
        # A <= B?
        if isinstance(rhs, WithinRange):
            if self.maxvalue <= rhs.minvalue:
                # A is definitely <= that B:
                return True
            if self.minvalue > rhs.maxvalue:
                # A is definitely > B, hence A <= B is a definite falsehood:
                return False
            return None
        elif isinstance(rhs, ConcreteValue):
            if self.maxvalue <= rhs.value:
                # A is definitely <= that B:
                return True
            if self.minvalue > rhs.value:
                # A is definitely > B, hence A <= B is a definite falsehood:
                return False
            if isinstance(self.gcctype, gcc.IntegerType):
                # Split the range against the concrete value, into the True and
                # False cases:
                true_range = WithinRange(self.gcctype, self.loc,
                                         self.minvalue,
                                         rhs.value)
                false_range = WithinRange(self.gcctype, self.loc,
                                          rhs.value + 1,
                                          self.maxvalue)
                ranges = [true_range, false_range]
                descriptions = ['when considering range: %s <= value <= %s' %
                                (value_to_str(r.minvalue),
                                 value_to_str(r.maxvalue))
                                for r in ranges]
                raise SplitValue(self, ranges, descriptions)
            return None
        return None

    def impl_is_lt(self, rhs):
        # Is A < B ?
        if isinstance(rhs, WithinRange):
            if self.maxvalue < rhs.minvalue:
                # A is definitely less that B:
                return True
            if self.minvalue >= rhs.maxvalue:
                # A is definitely >= B, hence A < B is a definite falsehood:
                return False
            return None
        elif isinstance(rhs, ConcreteValue):
            if self.maxvalue < rhs.value:
                # A is definitely less that B:
                return True
            if self.minvalue >= rhs.value:
                # A is definitely >= B, hence A < B is a definite falsehood:
                return False
            if isinstance(self.gcctype, gcc.IntegerType):
                # Split the range against the concrete value, into the True and
                # False cases:
                true_range = WithinRange(self.gcctype, self.loc,
                                         self.minvalue,
                                         rhs.value - 1)
                false_range = WithinRange(self.gcctype, self.loc,
                                          rhs.value,
                                          self.maxvalue)
                ranges = [true_range, false_range]
                descriptions = ['when considering range: %s <= value <= %s' %
                                (value_to_str(r.minvalue),
                                 value_to_str(r.maxvalue))
                                for r in ranges]
                raise SplitValue(self, ranges, descriptions)
            return None
        return None

    def impl_is_ge(self, rhs):
        # Is A >= B ?
        if isinstance(rhs, WithinRange):
            if self.minvalue >= rhs.maxvalue:
                # A is definitely >= B:
                return True
            if self.maxvalue <= rhs.minvalue:
                # A is definitely not >= B:
                return False
            return None
        elif isinstance(rhs, ConcreteValue):
            if self.minvalue >= rhs.value:
                # A is definitely >= B:
                return True
            if self.maxvalue <= rhs.value:
                # A is definitely not >= B:
                return False
            return None
        return None

    def extract_from_parent(self, region, gcctype, loc):
        return WithinRange(gcctype, self.loc, self.minvalue, self.maxvalue)

    def union(self, v_other):
        check_isinstance(v_other, AbstractValue)
        if isinstance(v_other, ConcreteValue):
            return WithinRange(self.gcctype, self.loc,
                               *(self.minvalue, self.maxvalue, v_other.value))
        if isinstance(v_other, WithinRange):
            return WithinRange(self.gcctype, self.loc,
                               *(self.minvalue, self.maxvalue,
                                 v_other.minvalue, v_other.maxvalue))
        raise NotImplementedError('%s.union(%s)'
                                  % (self.__class__.__name__, v_other))

class PointerToRegion(AbstractValue):
    """A non-NULL pointer value, pointing at a specific Region"""
    __slots__ = ('region', )

    def __init__(self, gcctype, loc, region):
        AbstractValue.__init__(self, gcctype, loc)
        check_isinstance(region, Region)
        self.region = region

    def __str__(self):
        if self.loc:
            return '(%s)&%r from %s' % (self.gcctype, self.region, self.loc)
        else:
            return '(%s)&%r' % (self.gcctype, self.region)

    def __repr__(self):
        return 'PointerToRegion(gcctype=%r, loc=%r, region=%r)' % (str(self.gcctype), self.loc, self.region)

    def is_equal(self, rhs):
        if isinstance(rhs, ConcreteValue) and rhs.value == 0:
            log('ptr to region vs 0: %s is definitely not equal to %s', self, rhs)
            return False

        if isinstance(rhs, PointerToRegion):
            log('comparing regions: %s %s', self, rhs)
            return self.region == rhs.region

        # We don't know:
        return None

    def impl_is_lt(self, rhs):
        return None

    def impl_is_ge(self, rhs):
        return None

class DeallocatedMemory(AbstractValue):
    """
    A 'poisoned' r-value: this memory has been deallocated, so the r-value
    is meaningless.
    """
    def __str__(self):
        if self.loc:
            return 'memory deallocated at %s' % self.loc
        else:
            return 'deallocated memory'

    def extract_from_parent(self, region, gcctype, loc):
        return DeallocatedMemory(gcctype, self.loc)

class UninitializedData(AbstractValue):
    """
    A 'poisoned' r-value: this memory has not yet been written to, so the
    r-value is meaningless.
    """
    def __str__(self):
        if self.loc:
            return 'uninitialized data at %s' % self.loc
        else:
            return 'uninitialized data'

    def is_equal(self, rhs):
        # We don't know:
        return None

    def impl_is_lt(self, rhs):
        return None

    def impl_is_ge(self, rhs):
        return None

    def get_transitions_for_function_call(self, state, stmt):
        check_isinstance(state, State)
        check_isinstance(stmt, gcc.GimpleCall)

        class CallOfUninitializedFunctionPtr(PredictedError):
            def __init__(self, stmt, value):
                check_isinstance(stmt, gcc.Gimple)
                check_isinstance(value, AbstractValue)
                self.stmt = stmt
                self.value = value

            def __str__(self):
                return ('call of uninitialized function pointer at %s: %s'
                        % (self.stmt.loc, self.value))

        raise CallOfUninitializedFunctionPtr(stmt, self)

    def extract_from_parent(self, region, gcctype, loc):
        return UninitializedData(gcctype, self.loc)

############################################################################
# Various kinds of predicted error:
############################################################################

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


class PredictedValueError(PredictedError):
    def __init__(self, state, expr, value, isdefinite):
        check_isinstance(state, State)
        check_isinstance(expr, gcc.Tree)
        check_isinstance(value, AbstractValue)
        self.state = state
        self.expr = expr
        self.value = value
        self.isdefinite = isdefinite

class UsageOfUninitializedData(PredictedValueError):
    def __init__(self, state, expr, value, desc):
        check_isinstance(state, State)
        check_isinstance(expr, gcc.Tree)
        check_isinstance(value, AbstractValue)
        PredictedValueError.__init__(self, state, expr, value, True)
        check_isinstance(desc, str)
        self.desc = desc

    def __str__(self):
        return ('%s: %s at %s'
                    % (self.desc, self.expr, self.state.loc.get_stmt().loc))

class NullPtrDereference(PredictedValueError):
    def __init__(self, state, expr, ptr, isdefinite):
        check_isinstance(state, State)
        check_isinstance(expr, gcc.Tree)
        check_isinstance(expr, (gcc.ComponentRef, gcc.MemRef))
        PredictedValueError.__init__(self, state, expr, ptr, isdefinite)

    def __str__(self):
        if self.isdefinite:
            return ('dereferencing NULL (%s) at %s'
                    % (self.expr, self.state.loc.get_stmt().loc))
        else:
            return ('possibly dereferencing NULL (%s) at %s'
                    % (self.expr, self.state.loc.get_stmt().loc))

class NullPtrArgument(PredictedValueError):
    def __init__(self, state, stmt, idx, ptr, isdefinite):
        check_isinstance(state, State)
        check_isinstance(stmt, gcc.Gimple)
        check_isinstance(idx, int)
        check_isinstance(ptr, AbstractValue)
        PredictedValueError.__init__(self, state, stmt.args[idx], ptr, isdefinite)
        self.stmt = stmt
        self.idx = idx
        # this is a 0-based index; it is changed to a 1-based index when
        # printed

    def __str__(self):
        if self.isdefinite:
            return ('calling %s with NULL (%s) as argument %i at %s'
                    % (self.stmt.fn, self.expr,
                       self.idx + 1, self.state.loc.get_stmt().loc))
        else:
            return ('possibly calling %s with NULL (%s) as argument %i at %s'
                    % (self.stmt.fn, self.expr,
                       self.idx + 1, self.state.loc.get_stmt().loc))



class ReadFromDeallocatedMemory(PredictedError):
    def __init__(self, stmt, value):
        check_isinstance(stmt, gcc.Gimple)
        check_isinstance(value, DeallocatedMemory)
        self.stmt = stmt
        self.value = value

    def __str__(self):
        return ('reading from deallocated memory at %s: %s'
                % (self.stmt.loc, self.value))

def describe_stmt(stmt):
    if isinstance(stmt, gcc.GimpleCall):
        if isinstance(stmt.fn.operand, gcc.FunctionDecl):
            fnname = stmt.fn.operand.name
            return 'call to %s at line %i' % (fnname, stmt.loc.line)
    else:
        return str(stmt.loc)

class Location(object):
    """A location within a CFG: a gcc.BasicBlock together with an index into
    the gimple list.  (We don't support SSA passes)"""
    __slots__ = ('bb', 'idx', )

    def __init__(self, bb, idx):
        check_isinstance(bb, gcc.BasicBlock)
        check_isinstance(idx, int)
        self.bb = bb
        self.idx = idx

    def __repr__(self):
        return ('Location(bb=%i, idx=%i)'
                % (self.bb.index, self.idx))

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

    def __eq__(self, other):
        return self.bb == other.bb and self.idx == other.idx

    @classmethod
    def get_block_start(cls, bb):
        # Don't bother iterating through phi_nodes if there aren't any:
        return Location(bb, 0)

    def get_stmt(self):
        if self.bb.gimple:
            return self.bb.gimple[self.idx]
        else:
            return None

    def get_gcc_loc(self):
        stmt = self.get_stmt()
        if stmt:
            return stmt.loc
        else:
            return None

class Region(object):
    __slots__ = ('name', 'parent', 'children', 'fields', )

    def __init__(self, name, parent):
        self.name = name
        self.parent = parent
        self.children = []
        self.fields = {}
        if parent:
            parent.children.append(self)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.name)

    def is_on_stack(self):
        if isinstance(self, RegionOnStack):
            return True
        if self.parent:
            return self.parent.is_on_stack()
        return False

class RegionForGlobal(Region):
    """
    Represents the area of memory (e.g. in .data or .bss section)
    used to store a particular globa
    """
    __slots__ = ('vardecl', )

    def __init__(self, vardecl):
        check_isinstance(vardecl, (gcc.VarDecl, gcc.FunctionDecl))
        Region.__init__(self, vardecl.name, None)
        self.vardecl = vardecl

    def __repr__(self):
        return 'RegionForGlobal(%r)' % self.vardecl

class RegionOnStack(Region):
    def __repr__(self):
        return 'RegionOnStack(%r)' % self.name

    def __str__(self):
        return '%s on stack' % self.name

class RegionForLocal(RegionOnStack):
    __slots__ = ('vardecl', )

    def __init__(self, vardecl, stack):
        RegionOnStack.__init__(self, 'region for %r' % vardecl, stack)
        self.vardecl = vardecl

class RegionOnHeap(Region):
    """
    Represents an area of memory allocated on the heap
    """
    __slots__ = ('alloc_stmt', )

    def __init__(self, name, alloc_stmt):
        check_isinstance(alloc_stmt, gcc.Gimple)
        Region.__init__(self, name, None)
        self.alloc_stmt = alloc_stmt

    def __repr__(self):
        return 'RegionOnHeap(%r, %r)' % (self.name, self.alloc_stmt.loc)

    def __str__(self):
        return '%s allocated at %s' % (self.name, self.alloc_stmt.loc)


class RegionForStringConstant(Region):
    """
    Represents an area of memory used for string constants
    typically allocated in the .data segment
    """
    __slots__ = ('text', )

    def __init__(self, text):
        Region.__init__(self, text, None)
        self.text = text

class ArrayElementRegion(Region):
    __slots__ = ('index', )

    def __init__(self, name, parent, index):
        Region.__init__(self, name, parent)
        self.index = index

class MissingValue(Exception):
    """
    The value tracking system couldn't figure out any information about the
    given region
    """
    def __init__(self, region):
        self.region = region

    def __str__(self):
        return 'Missing value for %s' % self.region

class SplitValue(Exception):
    """
    We encountered an value (e.g. UnknownValue), but we'd like to know more
    about it.

    Backtrack the analysis, splitting it into multiple possible worlds
    with alternate abstract values for said value
    """
    def __init__(self, value, altvalues, descriptions):
        self.value = value
        self.altvalues = altvalues
        self.descriptions = descriptions

    def __str__(self):
        return ('Splitting:\n%r\ninto\n%s'
                % (self.value,
                   '\n'.join([repr(alt) for alt in self.altvalues])))

    def split(self, state):
        log('creating states for split of %s into %s', self.value, self.altvalues)
        result = []
        for altvalue, desc in zip(self.altvalues, self.descriptions):
            log(' creating state for split where %s is %s', self.value, altvalue)
            altvalue.fromsplit = True

            newstate = state.copy()
            newstate.fromsplit = True
            for r in newstate.value_for_region:
                # Replace instances of the value itself:
                if newstate.value_for_region[r] is self.value:
                    log('  replacing value for region %s with %s', r, altvalue)
                    newstate.value_for_region[r] = altvalue
            result.append(Transition(state,
                                     newstate,
                                     desc))
        return result


class Facet(object):
    """
    A facet of state, relating to a particular API (e.g. libc, cpython, etc)

    Each facet knows which State instance it relates to, and knows how to
    copy itself to a new State.

    Potentially it can also supply "impl_" methods, which implement named
    functions within the API, describing all possible transitions from the
    current state to new states (e.g. success, failure, etc), creating
    appropriate new States with appropriate new Facet subclass instances.
    """
    __slots__ = ('state', )

    def __init__(self, state):
        check_isinstance(state, State)
        self.state = state

    def copy(self, newstate):
        # Concrete subclasses should implement this.
        raise NotImplementedError

class State(object):
    """
    A Location with memory state, and zero or more additional "facets" of
    state, one per API that we care about.

    'facets' is a dict, mapping attribute names to Facet subclass.

    For example, it might be:
       {'cpython': CPython,
        'libc': Libc,
        'glib': GLib}
    indicating that we expect all State instances to have a s.cpython field,
    with a CPython instance, and a s.libc field (a Libc instance), etc.

    Every State "knows" what all its facets are, and each Facet has a "state"
    attribute recording which State instance it is part of.

    For example, a CPython facet can keep track of the thread-local exception
    status, and a Libc facet can keep track of file-descriptors, malloc
    buffers, etc.

    Hopefully this will allow checking of additional APIs to be slotted into
    the checker, whilst keeping each API's special-case rules isolated.
    """

    # We can't use the __slots__ optimization here, as we're adding additional
    # per-facet attributes

    def __init__(self, fun, loc, facets, region_for_var=None, value_for_region=None,
                 return_rvalue=None, has_returned=False, not_returning=False):
        check_isinstance(fun, gcc.Function)
        check_isinstance(loc, Location)
        check_isinstance(facets, dict)
        self.fun = fun
        self.loc = loc
        self.facets = facets

        # Mapping from VarDecl.name to Region:
        if region_for_var:
            check_isinstance(region_for_var, OrderedDict)
            self.region_for_var = region_for_var
        else:
            self.region_for_var = OrderedDict()

        # Mapping from Region to AbstractValue:
        if value_for_region:
            check_isinstance(value_for_region, OrderedDict)
            self.value_for_region = value_for_region
        else:
            self.value_for_region = OrderedDict()

        self.return_rvalue = return_rvalue
        self.has_returned = has_returned
        self.not_returning = not_returning

    def __str__(self):
        return ('loc: %s region_for_var:%s value_for_region:%s'
                % (self.loc,
                   self.region_for_var,
                   self.value_for_region))

    def __repr__(self):
        return ('loc: %r region_for_var:%r value_for_region:%r'
                % (self.loc,
                   self.region_for_var,
                   self.value_for_region))

    def as_str_table(self):
        # Generate a string, displaying the data in tabular form:
        from gccutils import Table
        t = Table(['Expression', 'Region', 'Value'])
        for k in self.region_for_var:
            region = self.region_for_var[k]
            value = self.value_for_region.get(region, None)
            t.add_row((k, region, value),)
        s = StringIO()
        t.write(s)
        return s.getvalue()

    def log(self, logger):
        if not logging_enabled:
            return
        # Display data in tabular form:
        logger('%s', self.as_str_table())

        #logger('extra: %s' % (self._extra(), ), indent)

        # FIXME: derived class/extra:
        #self.resources.log(logger, indent)

        logger('loc: %s', self.loc)
        if self.loc.get_stmt():
            logger('%s', self.loc.get_stmt().loc)

    def copy(self):
        s_new = State(self.fun,
                      self.loc,
                      self.facets,
                      self.region_for_var.copy(),
                      self.value_for_region.copy(),
                      self.return_rvalue,
                      self.has_returned,
                      self.not_returning)
        # Make a copy of each facet into the new state:
        for key in self.facets:
            facetcls = self.facets[key]
            f_old = getattr(self, key)
            f_new = f_old.copy(s_new)
            setattr(s_new, key, f_new)
        return s_new

    def verify(self):
        """
        Perform self-tests to ensure sanity of this State
        """
        for k in self.value_for_region:
            check_isinstance(k, Region)
            if not isinstance(self.value_for_region[k], AbstractValue):
                raise TypeError('value for region %r is not an AbstractValue: %r'
                                % (k, self.value_for_region[k]))

    def eval_lvalue(self, expr, loc):
        """
        Return the Region for the given expression
        """
        log('eval_lvalue: %r %s', expr, expr)
        if loc:
            check_isinstance(loc, gcc.Location)
        if isinstance(expr, gcc.SsaName):
            region = self.var_region(expr.var)
            check_isinstance(region, Region)
            return region
        if isinstance(expr, (gcc.VarDecl, gcc.ParmDecl, gcc.ResultDecl, gcc.FunctionDecl)):
            region = self.var_region(expr)
            check_isinstance(region, Region)
            return region
        elif isinstance(expr, gcc.ArrayRef):
            region = self.element_region(expr, loc)
            check_isinstance(region, Region)
            return region
        elif isinstance(expr, gcc.ComponentRef):
            check_isinstance(expr.field, gcc.FieldDecl)
            return self.get_field_region(expr, loc)
        elif isinstance(expr, gcc.StringCst):
            region = self.string_constant_region(expr, loc)
            check_isinstance(region, Region)
            return region
        elif isinstance(expr, gcc.MemRef):
            # Write through a pointer:
            dest_ptr = self.eval_rvalue(expr.operand, loc)
            log('dest_ptr: %r', dest_ptr)
            self.raise_any_null_ptr_deref(expr, dest_ptr)
            if isinstance(dest_ptr, UnknownValue):
                # Split into null/non-null pointers:
                self.raise_split_value(dest_ptr)
            check_isinstance(dest_ptr, PointerToRegion)
            dest_region = dest_ptr.region
            log('dest_region: %r', dest_region)
            return dest_region
        raise NotImplementedError('eval_lvalue: %r %s' % (expr, expr))

    def eval_rvalue(self, expr, loc):
        """
        Return the value for the given expression, as an AbstractValue
        FIXME: also as a Region?
        """
        log('eval_rvalue: %r %s', expr, expr)
        if loc:
            check_isinstance(loc, gcc.Location)

        if isinstance(expr, AbstractValue):
            return expr
        if isinstance(expr, Region):
            return expr
        if isinstance(expr, gcc.IntegerCst):
            return ConcreteValue(expr.type, loc, expr.constant)
        if isinstance(expr, gcc.SsaName):
            region = self.var_region(expr.var)
            check_isinstance(region, Region)
            value = self.get_store(region, expr.type, loc)
            check_isinstance(value, AbstractValue)
            return value
        if isinstance(expr, (gcc.VarDecl, gcc.ParmDecl, gcc.ResultDecl)):
            region = self.var_region(expr)
            check_isinstance(region, Region)
            value = self.get_store(region, expr.type, loc)
            check_isinstance(value, AbstractValue)
            return value
            #return UnknownValue.make(expr.type, str(expr))
        if isinstance(expr, gcc.ComponentRef):
            #check_isinstance(expr.field, gcc.FieldDecl)
            region = self.get_field_region(expr, loc)#.target, expr.field.name)
            check_isinstance(region, Region)
            log('got field region for %s: %r', expr, region)
            try:
                value = self.get_store(region, expr.type, loc)
                log('got value: %r', value)
            except MissingValue:
                value = UnknownValue.make(expr.type, loc)
                log('no value; using: %r', value)
            check_isinstance(value, AbstractValue)
            return value
        if isinstance(expr, gcc.AddrExpr):
            log('expr.operand: %r', expr.operand)
            lvalue = self.eval_lvalue(expr.operand, loc)
            check_isinstance(lvalue, Region)
            if isinstance(expr.operand.type, gcc.ArrayType):
                index0_lvalue = self._array_region(lvalue, 0)
                return PointerToRegion(expr.type, loc, index0_lvalue)
            else:
                return PointerToRegion(expr.type, loc, lvalue)
        if isinstance(expr, gcc.ArrayRef):
            log('expr.array: %r', expr.array)
            log('expr.index: %r', expr.index)
            lvalue = self.eval_lvalue(expr, loc)
            check_isinstance(lvalue, Region)
            rvalue = self.get_store(lvalue, expr.type, loc)
            check_isinstance(rvalue, AbstractValue)
            return rvalue
        if isinstance(expr, gcc.MemRef):
            log('expr.operand: %r', expr.operand)
            opvalue = self.eval_rvalue(expr.operand, loc)
            check_isinstance(opvalue, AbstractValue)
            log('opvalue: %r', opvalue)
            self.raise_any_null_ptr_deref(expr, opvalue)
            if isinstance(opvalue, UnknownValue):
                # Split into null/non-null pointers:
                self.raise_split_value(opvalue)
            check_isinstance(opvalue, PointerToRegion) # FIXME
            rvalue = self.get_store(opvalue.region, expr.type, loc)
            check_isinstance(rvalue, AbstractValue)
            return rvalue
        if isinstance(expr, gcc.BitFieldRef):
            # e.g. in 'D.2694 = BIT_FIELD_REF <*foo, 8, 0>;'
            # for now, pessimistically assume nothing:
            return UnknownValue.make(expr.type, loc)

        raise NotImplementedError('eval_rvalue: %r %s' % (expr, expr))
        return UnknownValue.make(expr.type, loc) # FIXME

    def assign(self, lhs, rhs, loc):
        log('assign(%r, %r)', lhs, rhs)
        log('assign(%s, %s)', lhs, rhs)
        if loc:
            check_isinstance(loc, gcc.Location)
        dest_region = self.eval_lvalue(lhs, loc)
        log('dest_region: %s %r', dest_region, dest_region)
        value = self.eval_rvalue(rhs, loc)
        log('value: %s %r', value, value)
        check_isinstance(value, AbstractValue)
        check_isinstance(dest_region, Region)
        self.value_for_region[dest_region] = value

    def var_region(self, var):
        check_isinstance(var, (gcc.VarDecl, gcc.ParmDecl, gcc.ResultDecl, gcc.FunctionDecl))
        if var not in self.region_for_var:
            # Presumably a reference to a global variable:
            log('adding region for global var: %r', var)
            region = RegionForGlobal(var)
            # it is its own region:
            self.region_for_var[var] = region

            # Initialize the refcount of global PyObject instances
            # e.g. _Py_NoneStruct to 0 i.e. we don't own any references to them
            if str(var.type) == 'struct PyObject':
                from libcpychecker.refcounts import RefcountValue
                ob_refcnt = self.make_field_region(region, 'ob_refcnt') # FIXME: this should be a memref and fieldref
                self.value_for_region[ob_refcnt] = RefcountValue.borrowed_ref()
        return self.region_for_var[var]

    def element_region(self, ar, loc):
        log('element_region: %s', ar)
        check_isinstance(ar, gcc.ArrayRef)
        if loc:
            check_isinstance(loc, gcc.Location)

        log('  ar.array: %r', ar.array)
        log('  ar.index: %r', ar.index)
        parent = self.eval_lvalue(ar.array, loc)
        check_isinstance(parent, Region)
        log('  parent: %r', parent)
        index = self.eval_rvalue(ar.index, loc)
        check_isinstance(index, AbstractValue)
        log('  index: %r', index)
        if isinstance(index, ConcreteValue):
            index = index.value
        return self._array_region(parent, index)

    def pointer_plus_region(self, stmt):
        # Cope with treating pointers as arrays.
        # The constant appears to be in bytes, rather than as units of the type
        log('pointer_add_region')
        assert stmt.exprcode == gcc.PointerPlusExpr
        rhs = stmt.rhs
        a = self.eval_rvalue(rhs[0], stmt.loc)
        b = self.eval_rvalue(rhs[1], stmt.loc)
        log('a: %r', a)
        log('b: %r', b)
        if isinstance(a, PointerToRegion) and isinstance(b, ConcreteValue):
            parent = a.region
            log('%s', rhs[0].type)
            log('%s', rhs[0].type.dereference)
            t = rhs[0].type.dereference
            if isinstance(t, gcc.VoidType):
                index = b.value
            else:
                sizeof = t.sizeof
                log('%s', sizeof)
                index = b.value // sizeof
            # Are we offsetting within an array?
            if isinstance(parent, ArrayElementRegion):
                return self._array_region(parent.parent, parent.index + index)
            return self._array_region(parent, index)
        else:
            raise NotImplementedError("Don't know how to cope with pointer addition of\n  %r\nand\n  %rat %s"
                                      % (a, b, stmt.loc))

    def _array_region(self, parent, index):
        # Used by element_region, and pointer_add_region
        log('_array_region(%s, %s)', parent, index)
        check_isinstance(parent, Region)
        check_isinstance(index, (integer_types, UnknownValue, ConcreteValue, WithinRange))
        if isinstance(index, ConcreteValue):
            index = index.value
        if index in parent.fields:
            log('reusing')
            return parent.fields[index]
        log('not reusing')
        region = ArrayElementRegion('%s[%s]' % (parent.name, index), parent, index)
        parent.fields[index] = region
        # it is its own region:
        self.region_for_var[region] = region
        return region

    def get_field_region(self, cr, loc): #target, field):
        check_isinstance(cr, gcc.ComponentRef)
        if loc:
            check_isinstance(loc, gcc.Location)
        #cr.debug()
        log('target: %r %s ', cr.target, cr.target)
        log('field: %r', cr.field)
        if isinstance(cr.target, gcc.MemRef):
            ptr = self.eval_rvalue(cr.target.operand, loc) # FIXME
            log('ptr: %r', ptr)
            self.raise_any_null_ptr_deref(cr, ptr)
            if isinstance(ptr, UnknownValue):
                # It could be NULL; it could be non-NULL
                # Split the analysis
                # Non-NULL pointer:
                log('splitting %s into non-NULL/NULL pointers', cr)
                self.raise_split_value(ptr)
            check_isinstance(ptr, PointerToRegion)
            return self.make_field_region(ptr.region, cr.field.name)

        target_region = self.eval_lvalue(cr.target, loc)
        return self.make_field_region(target_region, cr.field.name)

    def string_constant_region(self, expr, loc):
        log('string_constant_region: %s', expr)
        check_isinstance(expr, gcc.StringCst)
        if loc:
            check_isinstance(loc, gcc.Location)
        region = RegionForStringConstant(expr.constant)
        return region

    def get_store(self, region, gcctype, loc):
        if gcctype:
            check_isinstance(gcctype, gcc.Type)
        if loc:
            check_isinstance(loc, gcc.Location)
        try:
            val = self._get_store_recursive(region, gcctype, loc)
            return val
        except MissingValue:
            # The first time we look up the value of a global, assign it a new
            # "unknown" value:
            if isinstance(region, RegionForGlobal):
                newval = UnknownValue.make(region.vardecl.type, region.vardecl.location)
                log('setting up %s for %s', newval, region.vardecl)
                self.value_for_region[region] = newval
                return newval

            # OK: no value known:
            return UnknownValue.make(gcctype, loc)

    def summarize_array(self, r_array, v_range, gcctype, loc):
        """
        Determine if the region r_array is fully populated with values
        in the range of indices covered by v_range

        If it is, return a representative value
        """
        check_isinstance(r_array, Region)
        check_isinstance(v_range, WithinRange)

        v_result = EmptySet(gcctype, loc)

        # (This loop should rapidly fail when the range is large and/or outside
        # the bounds of the array)
        for index in range(v_range.minvalue,
                           v_range.maxvalue + 1):
            # print 'index: %i' % index
            if index not in r_array.fields:
                # We have an uninitialized element:
                return None
            r_at_index = r_array.fields[index]
            # print 'r_at_index: %s' % r_at_index
            check_isinstance(r_at_index, Region)
            v_at_index = self.value_for_region[r_at_index]
            # print 'v_at_index: %s' % v_at_index
            check_isinstance(v_at_index, AbstractValue)
            v_result = v_result.union(v_at_index)
            # print 'v_result: %s' % v_result

        # Every subregion within the given range is initialized:
        return v_result

    def _get_store_recursive(self, region, gcctype, loc):
        check_isinstance(region, Region)
        log('_get_store_recursive(%s, %s, %s)', region, gcctype, loc)
        if region in self.value_for_region:
            return self.value_for_region[region]

        # Not found; try default value from parent region:
        if region.parent:
            try:
                parent_value = self._get_store_recursive(region.parent, gcctype, loc)

                # If we're looking up within an array on the stack that has
                # been fully initialized, then the default value from the
                # parent is UninitializedData(), but every actual value that
                # could be looked up is some sane value.  If we're indexing
                # to an unknown location, don't falsely say it's unitialized:
                if isinstance(parent_value, UninitializedData):
                    if isinstance(region, ArrayElementRegion):
                        if isinstance(region.index, WithinRange):
                            v_lookup = self.summarize_array(region.parent,
                                                            region.index,
                                                            gcctype, loc)
                            if v_lookup:
                                return v_lookup
                return parent_value.extract_from_parent(region, gcctype, loc)
            except MissingValue:
                raise MissingValue(region)

        raise MissingValue(region)

    def make_heap_region(self, name, stmt):
        region = RegionOnHeap(name, stmt)
        # it is its own region:
        self.region_for_var[region] = region
        return region

    def make_field_region(self, target, field):
        check_isinstance(target, Region)
        check_isinstance(field, str)
        log('make_field_region(%r, %r)', target, field)
        if field in target.fields:
            log('reusing')
            return target.fields[field]
        log('not reusing')
        region = Region('%s.%s' % (target.name, field), target)
        target.fields[field] = region
        # it is its own region:
        self.region_for_var[region] = region
        return region


    def get_value_of_field_by_varname(self, varname, field):
        # Lookup varname.field
        # For use in writing selftests
        log('get_value_of_field_by_varname(%r, %r)', varname, field)
        check_isinstance(varname, str)
        check_isinstance(field, str)
        for k in self.region_for_var:
            if isinstance(k, gcc.VarDecl):
                if k.name == varname:
                    region = self.region_for_var[k]
                    region =  self.make_field_region(region, field)
                    value = self.value_for_region.get(region, None)
                    return value

    def get_value_of_field_by_region(self, region, field):
        # Lookup region->field
        # For use in writing selftests
        log('get_value_of_field_by_region(%r, %r)', region, field)
        check_isinstance(region, Region)
        check_isinstance(field, str)
        if field in region.fields:
            field_region = region.fields[field]
            return self.value_for_region.get(field_region, None)
        return None

    def init_for_function(self, fun):
        log('State.init_for_function(%r)', fun)
        self.fun = fun
        root_region = Region('root', None)
        stack = RegionOnStack('stack for %s' % fun.decl.name, root_region)

        nonnull_args = get_nonnull_arguments(fun.decl.type)
        for idx, parm in enumerate(fun.decl.arguments):
            region = RegionForLocal(parm, stack)
            self.region_for_var[parm] = region
            if idx in nonnull_args:
                # Make a non-NULL ptr:
                other = Region('region-for-arg-%s' % parm, None)
                self.region_for_var[other] = other
                self.value_for_region[region] = PointerToRegion(parm.type, parm.location, other)
            else:
                self.value_for_region[region] = UnknownValue.make(parm.type, parm.location)
        for local in fun.local_decls:
            region = RegionForLocal(local, stack)
            self.region_for_var[local] = region
            if local.static:
                # Statically-allocated locals are zero-initialized before the
                # function is called for the first time, and then preserve
                # state between function calls
                # For now, don't try to track all possible values a static var
                # can take; simply treat it as an UnknownValue
                v_local = UnknownValue.make(local.type, fun.start)
            else:
                v_local = UninitializedData(local.type, fun.start)
            self.value_for_region[region] = v_local

        # Region for the gcc.ResultDecl, if any:
        if fun.decl.result:
            result = fun.decl.result
            region = RegionForLocal(result, stack)
            self.region_for_var[result] = region
            self.value_for_region[region] = UninitializedData(result.type, fun.start)
        self.verify()

    def mktrans_assignment(self, lhs, rhs, desc):
        """
        Return a Transition to a state at the next location, with the RHS
        assigned to the LHS, if LHS is not None
        """
        log('mktrans_assignment(%r, %r, %r)', lhs, rhs, desc)
        if desc:
            check_isinstance(desc, str)
        new = self.copy()
        new.loc = self.loc.next_loc()
        if lhs:
            new.assign(lhs, rhs, self.loc.get_gcc_loc())
        return Transition(self, new, desc)

    def update_loc(self, newloc):
        new = self.copy()
        new.loc = newloc
        return new

    def use_next_loc(self):
        newloc = self.loc.next_loc()
        return self.update_loc(newloc)

    def get_gcc_loc_or_none(self):
        # Return the gcc.Location for this state, which could be None
        stmt = self.loc.get_stmt()
        if stmt:
            return stmt.loc

    def get_gcc_loc(self, fun):
        # Return a non-None gcc.Location for this state
        # Some statements have None for their location, but gcc.error() etc
        # don't allow this.  Use the end of the function for this case.
        stmt = self.loc.get_stmt()
        log('%s %r', stmt, stmt)
        if stmt:
            log('%s' % self.loc.get_stmt().loc)
            # grrr... not all statements have a non-NULL location
            gccloc = self.loc.get_stmt().loc
            if gccloc is None:
                gccloc = fun.end
            return gccloc
        else:
            return fun.end

    def raise_any_null_ptr_deref(self, expr, ptr):
        check_isinstance(expr, gcc.Tree)
        check_isinstance(ptr, AbstractValue)

        if isinstance(ptr, UninitializedData):
            raise UsageOfUninitializedData(self, expr, ptr,
                                           'dereferencing uninitialized pointer')

        if isinstance(ptr, ConcreteValue):
            if ptr.is_null_ptr():
                # Read through NULL
                # If we earlier split the analysis into NULL/non-NULL
                # cases, then we're only considering the possibility
                # that this pointer was NULL; we don't know for sure
                # that it was.
                isdefinite = not hasattr(ptr, 'fromsplit')
                raise NullPtrDereference(self, expr, ptr, isdefinite)

    def raise_any_null_ptr_func_arg(self, stmt, idx, ptr):
        # idx is the 0-based index of the argument

        check_isinstance(stmt, gcc.Gimple)
        check_isinstance(idx, int)
        check_isinstance(ptr, AbstractValue)
        if isinstance(ptr, ConcreteValue):
            if ptr.is_null_ptr():
                # NULL argument to a function that requires non-NULL
                # If we earlier split the analysis into NULL/non-NULL
                # cases, then we're only considering the possibility
                # that this pointer was NULL; we don't know for sure
                # that it was.
                isdefinite = not hasattr(ptr, 'fromsplit')
                raise NullPtrArgument(self, stmt, idx, ptr, isdefinite)

    def raise_split_value(self, ptr_rvalue, loc=None):
        """
        Raise a SplitValue exception on the given rvalue, so that we can
        backtrack and split the current state into a version with an explicit
        NULL value and a version with a non-NULL value

        FIXME: we should split into multiple non-NULL values, covering the
        various aliasing possibilities
        """
        check_isinstance(ptr_rvalue, AbstractValue)
        check_isinstance(ptr_rvalue, UnknownValue)
        check_isinstance(ptr_rvalue.gcctype, gcc.PointerType)
        global region_id
        region = Region('heap-region-%i' % region_id, None)
        region_id += 1
        self.region_for_var[region] = region
        non_null_ptr = PointerToRegion(ptr_rvalue.gcctype, loc, region)
        null_ptr = ConcreteValue(ptr_rvalue.gcctype, loc, 0)
        raise SplitValue(ptr_rvalue,
                         [non_null_ptr, null_ptr],
                         [("when treating %s as non-NULL" % ptr_rvalue),
                          ("when treating %s as NULL" % ptr_rvalue)])

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
            log('result: %s', result)
            return result

    def _get_transitions_for_stmt(self, stmt):
        log('_get_transitions_for_stmt: %r %s', stmt, stmt)
        log('dir(stmt): %s', dir(stmt))
        if stmt.loc:
            gcc.set_location(stmt.loc)
        if isinstance(stmt, gcc.GimpleCall):
            return self._get_transitions_for_GimpleCall(stmt)
        elif isinstance(stmt, (gcc.GimpleDebug, gcc.GimpleLabel,
                               gcc.GimplePredict)):
            return [Transition(self,
                               self.use_next_loc(),
                               None)]
        elif isinstance(stmt, gcc.GimpleCond):
            return self._get_transitions_for_GimpleCond(stmt)
        elif isinstance(stmt, gcc.GimpleReturn):
            return self._get_transitions_for_GimpleReturn(stmt)
        elif isinstance(stmt, gcc.GimpleAssign):
            return self._get_transitions_for_GimpleAssign(stmt)
        elif isinstance(stmt, gcc.GimpleSwitch):
            return self._get_transitions_for_GimpleSwitch(stmt)
        else:
            raise NotImplementedError("Don't know how to cope with %r (%s) at %s"
                                      % (stmt, stmt, stmt.loc))

    def mkstate_concrete_return_of(self, stmt, value):
        """
        Clone this state (at a function call), updating the location, and
        setting the result of the call to the given concrete value
        """
        newstate = self.copy()
        newstate.loc = self.loc.next_loc()
        if stmt.lhs:
            newstate.assign(stmt.lhs,
                            ConcreteValue(stmt.lhs.type, stmt.loc, value),
                            stmt.loc)
        return newstate

    def mktrans_nop(self, stmt, fnname):
        """
        Make a Transition for handling a function call that has no "visible"
        effect within our simulation (beyond advancing to the next location).
        [We might subsequently modify the destination state, though]
        """
        newstate = self.copy()
        newstate.loc = self.loc.next_loc()
        return Transition(self, newstate, 'calling %s()' % fnname)

    def mktrans_from_fncall_state(self, stmt, state, partialdesc, has_siblings):
        """
        Given a function call here, convert a State instance into a Transition
        instance, marking it.
        """
        check_isinstance(stmt, gcc.GimpleCall)
        check_isinstance(state, State)
        check_isinstance(partialdesc, str)
        fnname = stmt.fn.operand.name
        if has_siblings:
            desc = 'when %s() %s' % (fnname, partialdesc)
        else:
            desc = '%s() %s' % (fnname, partialdesc)
        return Transition(self, state, desc)

    def make_transitions_for_fncall(self, stmt, s_success, s_failure):
        """
        Given a function call, convert a pair of State instances into a pair
        of Transition instances, marking one as a successful call, the other
        as a failed call.
        """
        check_isinstance(stmt, gcc.GimpleCall)
        check_isinstance(s_success, State)
        check_isinstance(s_failure, State)

        if hasattr(stmt.fn, 'operand'):
            fnname = stmt.fn.operand.name
            return [Transition(self, s_success, 'when %s() succeeds' % fnname),
                    Transition(self, s_failure, 'when %s() fails' % fnname)]
        else:
            return [Transition(self, s_success, 'when call succeeds'),
                    Transition(self, s_failure, 'when call fails')]


    def eval_stmt_args(self, stmt):
        check_isinstance(stmt, gcc.GimpleCall)
        return [self.eval_rvalue(arg, stmt.loc)
                for arg in stmt.args]

    def _get_transitions_for_GimpleCall(self, stmt):
        log('stmt.lhs: %s %r', stmt.lhs, stmt.lhs)
        log('stmt.fn: %s %r', stmt.fn, stmt.fn)
        log('dir(stmt.fn): %s', dir(stmt.fn))
        if hasattr(stmt.fn, 'operand'):
            log('stmt.fn.operand: %s', stmt.fn.operand)
        returntype = stmt.fn.type.dereference.type
        log('returntype: %s', returntype)

        if stmt.noreturn:
            # The function being called does not return e.g. "exit(0);"
            # Transition to a special noreturn state:
            newstate = self.copy()
            newstate.not_returning = True
            return [Transition(self,
                               newstate,
                               'not returning from %s' % stmt.fn)]

        if isinstance(stmt.fn, (gcc.VarDecl, gcc.ParmDecl, gcc.SsaName)):
            # Calling through a function pointer:
            val = self.eval_rvalue(stmt.fn, stmt.loc)
            log('val: %s',  val)
            check_isinstance(val, AbstractValue)
            return val.get_transitions_for_function_call(self, stmt)

        # Evaluate the arguments:
        args = self.eval_stmt_args(stmt)

        # Check for uninitialized data:
        for i, arg in enumerate(args):
            if isinstance(arg, UninitializedData):
                raise UsageOfUninitializedData(self, stmt.args[i],
                                               arg,
                                               'passing uninitialized data as argument %i to function' % (i + 1))

        if isinstance(stmt.fn.operand, gcc.FunctionDecl):
            log('dir(stmt.fn.operand): %s', dir(stmt.fn.operand))
            log('stmt.fn.operand.name: %r', stmt.fn.operand.name)
            fnname = stmt.fn.operand.name

            # Hand off to impl_* methods of facets, where these methods exist
            # In each case, the method should have the form:
            #   def impl_foo(self, stmt, v_arg0, v_arg1, *args):
            # for a C function named "foo" i.e. it takes "self", plus the
            # gcc.GimpleCall statement, followed by the AbstractValue instances
            # for the evaluated arguments (which for some functions will
            # involve varargs, like above).
            # They should return a list of Transition instances.
            methname = 'impl_%s' % fnname
            for key in self.facets:
                facet = getattr(self, key)
                if hasattr(facet, methname):
                    meth = getattr(facet, 'impl_%s' % fnname)

                    # Call the facet's method:
                    return meth(stmt, *args)

            #from libcpychecker.c_stdio import c_stdio_functions, handle_c_stdio_function

            #if fnname in c_stdio_functions:
            #    return handle_c_stdio_function(self, fnname, stmt)

            if 0:
                # For extending coverage of the Python API:
                # Detect and complain about Python API entrypoints that
                # weren't explicitly handled
                if fnname.startswith('_Py') or fnname.startswith('Py'):
                    raise NotImplementedError('not yet implemented: %s' % fnname)

            # Unknown function returning (PyObject*):
            if str(stmt.fn.operand.type.type) == 'struct PyObject *':
                log('Invocation of unknown function returning PyObject *: %r' % fnname)
                # Assume that all such functions either:
                #   - return a new reference, or
                #   - return NULL and set an exception (e.g. MemoryError)
                from libcpychecker.attributes import fnnames_returning_borrowed_refs
                if fnname in fnnames_returning_borrowed_refs:
                    # The function being called was marked as returning a
                    # borrowed ref, rather than a new ref:
                    return self.apply_fncall_side_effects(
                        self.cpython.make_transitions_for_borrowed_ref_or_fail(stmt,
                                                                               'borrowed ref from %s()' % fnname),
                        stmt)
                return self.apply_fncall_side_effects(
                    self.cpython.make_transitions_for_new_ref_or_fail(stmt,
                                                                 'new ref from (unknown) %s' % fnname),
                    stmt)

            # Unknown function of other type:
            log('Invocation of unknown function: %r', fnname)
            return self.apply_fncall_side_effects(
                [self.mktrans_assignment(stmt.lhs,
                                         UnknownValue.make(returntype, stmt.loc),
                                         None)],
                stmt)

        log('stmt.args: %s %r', stmt.args, stmt.args)
        for i, arg in enumerate(stmt.args):
            log('args[%i]: %s %r', i, arg, arg)

    def get_function_name(self, stmt):
        """
        Try to get the function name for a gcc.GimpleCall statement as a
        string, or None if we're unable to determine it.

        For a simple function invocation this is easy, but if we're
        calling through a function pointer we may or may not know.
        """
        check_isinstance(stmt, gcc.GimpleCall)

        v_fn = self.eval_rvalue(stmt.fn, stmt.loc)
        if isinstance(v_fn, PointerToRegion):
            if isinstance(v_fn.region, RegionForGlobal):
                if isinstance(v_fn.region.vardecl, gcc.FunctionDecl):
                    return v_fn.region.vardecl.name

        # Unable to determine it:
        return None

    def apply_fncall_side_effects(self, transitions, stmt):
        """
        Given a list of Transition instances for a call to a function with
        unknown side-effects, modify all of the destination states.

        Specifically: any pointer arguments to the function are modified in
        the destination states to be an UnknownValue, given that the function
        could have written an arbitrary r-value back into the input
        """
        check_isinstance(transitions, list)
        check_isinstance(stmt, gcc.GimpleCall)

        args = self.eval_stmt_args(stmt)

        fnname = self.get_function_name(stmt)

        # cpython: handle functions marked as stealing references to their
        # arguments:
        from libcpychecker.attributes import stolen_refs_by_fnname
        if fnname in stolen_refs_by_fnname:
            for t_iter in transitions:
                check_isinstance(t_iter, Transition)
                for argindex in stolen_refs_by_fnname[stmt.fn.operand.name]:
                    v_arg = args[argindex-1]
                    if isinstance(v_arg, PointerToRegion):
                        t_iter.dest.cpython.steal_reference(v_arg.region)

        for t_iter in transitions:
            check_isinstance(t_iter, Transition)
            for v_arg in args:
                if isinstance(v_arg, PointerToRegion):
                    v_newval = UnknownValue.make(v_arg.gcctype, stmt.loc)
                    t_iter.dest.value_for_region[v_arg.region] = v_newval
        return transitions

    def _get_transitions_for_GimpleCond(self, stmt):
        def make_transition_for_true(stmt, has_siblings):
            e = true_edge(self.loc.bb)
            assert e
            nextstate = self.update_loc(Location.get_block_start(e.dest))
            nextstate.prior_bool = True
            if has_siblings:
                desc = 'when taking True path'
            else:
                desc = 'taking True path'
            return Transition(self, nextstate, desc)

        def make_transition_for_false(stmt, has_siblings):
            e = false_edge(self.loc.bb)
            assert e
            nextstate = self.update_loc(Location.get_block_start(e.dest))
            nextstate.prior_bool = False
            if has_siblings:
                desc = 'when taking False path'
            else:
                desc = 'taking False path'
            return Transition(self, nextstate, desc)

        log('stmt.exprcode: %s', stmt.exprcode)
        log('stmt.exprtype: %s', stmt.exprtype)
        log('stmt.lhs: %r %s', stmt.lhs, stmt.lhs)
        log('stmt.rhs: %r %s', stmt.rhs, stmt.rhs)
        boolval = self.eval_condition(stmt, stmt.lhs, stmt.exprcode, stmt.rhs)
        if boolval is True:
            log('taking True edge')
            nextstate = make_transition_for_true(stmt, False)
            return [nextstate]
        elif boolval is False:
            log('taking False edge')
            nextstate = make_transition_for_false(stmt, False)
            return [nextstate]
        else:
            check_isinstance(boolval, UnknownValue)
            # We don't have enough information; both branches are possible:
            return [make_transition_for_true(stmt, True),
                    make_transition_for_false(stmt, True)]

    def eval_condition(self, stmt, expr_lhs, exprcode, expr_rhs):
        """
        Evaluate a comparison, returning one of True, False, or None
        """
        log('eval_condition: %s %s %s ', expr_lhs, exprcode, expr_rhs)
        check_isinstance(expr_lhs, gcc.Tree)
        check_isinstance(exprcode, type) # it's a type, rather than an instance
        check_isinstance(expr_rhs, gcc.Tree)

        lhs = self.eval_rvalue(expr_lhs, stmt.loc)
        rhs = self.eval_rvalue(expr_rhs, stmt.loc)
        check_isinstance(lhs, AbstractValue)
        check_isinstance(rhs, AbstractValue)

        def is_equal(lhs, rhs):
            log('is_equal(%s, %s)', lhs, rhs)
            check_isinstance(lhs, AbstractValue)
            check_isinstance(rhs, AbstractValue)
            return lhs.is_equal(rhs)

        def is_lt(lhs, rhs):
            # "less-than"
            log('is_lt(%s, %s)', lhs, rhs)
            check_isinstance(lhs, AbstractValue)
            check_isinstance(rhs, AbstractValue)
            return lhs.is_lt(rhs)

        def is_le(lhs, rhs):
            # "less-than-or-equal"
            log('is_le(%s, %s)', lhs, rhs)
            return lhs.is_le(rhs)

        if exprcode == gcc.EqExpr:
            result = is_equal(lhs, rhs)
            if result is not None:
                return result
        elif exprcode == gcc.NeExpr:
            result = is_equal(lhs, rhs)
            if result is not None:
                return not result
        elif exprcode == gcc.LtExpr:
            result = is_lt(lhs, rhs)
            if result is not None:
                return result
        elif exprcode == gcc.LeExpr:
            result = is_le(lhs, rhs)
            if result is not None:
                return result
        elif exprcode == gcc.GeExpr:
            # Implement "A >= B" as "not(A < B)":
            result = is_lt(lhs, rhs)
            if result is not None:
                return not result
        elif exprcode == gcc.GtExpr:
            # Implement "A > B " as "not(A <= B)":
            result = is_le(lhs, rhs)
            if result is not None:
                return not result

        # Detect usage of uninitialized data:
        if isinstance(lhs, UninitializedData):
            raise UsageOfUninitializedData(self, expr_lhs, lhs,
                                           'comparison against uninitialized data')
        if isinstance(rhs, UninitializedData):
            raise UsageOfUninitializedData(self, expr_rhs, rhs,
                                           'comparison against uninitialized data')

        # Specialcasing: comparison of unknown ptr with NULL:
        if (isinstance(expr_lhs, gcc.VarDecl)
            and isinstance(expr_rhs, gcc.IntegerCst)
            and isinstance(expr_lhs.type, gcc.PointerType)):
            # Split the ptr variable immediately into NULL and non-NULL
            # versions, so that we can evaluate the true and false branch with
            # explicitly data
            log('splitting %s into non-NULL/NULL pointers', expr_lhs)
            self.raise_split_value(lhs, stmt.loc)

        log('unable to compare %r with %r', lhs, rhs)
        #raise NotImplementedError("Don't know how to do %s comparison of %s with %s"
        #                          % (exprcode, lhs, rhs))
        return UnknownValue(stmt.lhs.type, stmt.loc)

    def eval_binop_args(self, stmt):
        rhs = stmt.rhs
        a = self.eval_rvalue(rhs[0], stmt.loc)
        b = self.eval_rvalue(rhs[1], stmt.loc)
        log('a: %r', a)
        log('b: %r', b)
        return a, b

    def eval_rhs(self, stmt):
        log('eval_rhs(%s): %s', stmt, stmt.rhs)
        rhs = stmt.rhs
        # Handle arithmetic and boolean expressions:
        if stmt.exprcode in (gcc.PlusExpr, gcc.MinusExpr,  gcc.MultExpr, gcc.TruncDivExpr,
                             gcc.TruncModExpr,
                             gcc.MaxExpr, gcc.MinExpr,
                             gcc.BitIorExpr, gcc.BitAndExpr, gcc.BitXorExpr,
                             gcc.LshiftExpr, gcc.RshiftExpr,

                             gcc.TruthAndExpr, gcc.TruthOrExpr
                             ):
            a, b = self.eval_binop_args(stmt)
            if isinstance(a, UninitializedData):
                raise UsageOfUninitializedData(self, stmt.rhs[0], a,
                                               'usage of uninitialized data in left-hand side of %s' % stmt.exprcode)
            if isinstance(b, UninitializedData):
                raise UsageOfUninitializedData(self, stmt.rhs[1], b,
                                               'usage of uninitialized data in right-hand side of %s' % stmt.exprcode)

            try:
                c = a.eval_binop(stmt.exprcode, b, stmt.lhs.type, stmt.loc)
                check_isinstance(c, AbstractValue)
                return c
            except NotImplementedError:
                return UnknownValue.make(stmt.lhs.type, stmt.loc)
        elif stmt.exprcode == gcc.ComponentRef:
            return self.eval_rvalue(rhs[0], stmt.loc)
        elif stmt.exprcode == gcc.VarDecl:
            return self.eval_rvalue(rhs[0], stmt.loc)
        elif stmt.exprcode == gcc.ParmDecl:
            return self.eval_rvalue(rhs[0], stmt.loc)
        elif stmt.exprcode == gcc.IntegerCst:
            return self.eval_rvalue(rhs[0], stmt.loc)
        elif stmt.exprcode == gcc.AddrExpr:
            return self.eval_rvalue(rhs[0], stmt.loc)
        elif stmt.exprcode == gcc.NopExpr:
            return self.eval_rvalue(rhs[0], stmt.loc)
        elif stmt.exprcode == gcc.ArrayRef:
            return self.eval_rvalue(rhs[0], stmt.loc)
        elif stmt.exprcode == gcc.MemRef:
            return self.eval_rvalue(rhs[0], stmt.loc)
        elif stmt.exprcode == gcc.PointerPlusExpr:
            try:
                region = self.pointer_plus_region(stmt)
                return PointerToRegion(stmt.lhs.type, stmt.loc, region)
            except NotImplementedError:
                return UnknownValue.make(stmt.lhs.type, stmt.loc)
        elif stmt.exprcode in (gcc.EqExpr, gcc.NeExpr, gcc.LtExpr,
                               gcc.LeExpr, gcc.GeExpr, gcc.GtExpr):
            # Comparisons
            result = self.eval_condition(stmt, rhs[0], stmt.exprcode, rhs[1])
            if result is not None:
                return ConcreteValue(stmt.lhs.type, stmt.loc,
                                     1 if result else 0)
            else:
                return UnknownValue.make(stmt.lhs.type, stmt.loc)
        # Unary expressions:
        elif stmt.exprcode in (gcc.AbsExpr, gcc.BitNotExpr, gcc.ConvertExpr,
                               gcc.NegateExpr):
            v_rhs = self.eval_rvalue(stmt.rhs[0], stmt.loc)
            return v_rhs.eval_unary_op(stmt.exprcode, stmt.lhs.type, stmt.loc)
        elif stmt.exprcode == gcc.BitFieldRef:
            return self.eval_rvalue(rhs[0], stmt.loc)
        elif stmt.exprcode == gcc.Constructor:
            # Default value for whole array becomes 0:
            return ConcreteValue(stmt.lhs.type,
                                 stmt.loc, 0)
        else:
            raise NotImplementedError("Don't know how to cope with exprcode: %r (%s) at %s"
                                      % (stmt.exprcode, stmt.exprcode, stmt.loc))

    def _get_transitions_for_GimpleAssign(self, stmt):
        log('stmt.lhs: %r %s', stmt.lhs, stmt.lhs)
        log('stmt.rhs: %r %s', stmt.rhs, stmt.rhs)
        log('stmt: %r %s', stmt, stmt)
        log('stmt.exprcode: %r', stmt.exprcode)

        value = self.eval_rhs(stmt)
        log('value from eval_rhs: %r', value)
        check_isinstance(value, AbstractValue)

        if isinstance(value, DeallocatedMemory):
            raise ReadFromDeallocatedMemory(stmt, value)

        nextstate = self.use_next_loc()
        return [self.mktrans_assignment(stmt.lhs,
                                        value,
                                        None)]

    def _get_transitions_for_GimpleReturn(self, stmt):
        #log('stmt.lhs: %r %s', stmt.lhs, stmt.lhs)
        #log('stmt.rhs: %r %s', stmt.rhs, stmt.rhs)
        log('stmt: %r %s', stmt, stmt)
        log('stmt.retval: %r', stmt.retval)

        nextstate = self.copy()

        if stmt.retval:
            rvalue = self.eval_rvalue(stmt.retval, stmt.loc)
            log('rvalue from eval_rvalue: %r', rvalue)
            nextstate.return_rvalue = rvalue
        nextstate.has_returned = True
        return [Transition(self, nextstate, 'returning')]

    def _get_transitions_for_GimpleSwitch(self, stmt):
        def get_labels_for_rvalue(self, stmt, rvalue):
            # Gather all possible labels for the given rvalue
            result = []
            for label in stmt.labels:
                # FIXME: for now, treat all labels as possible:
                result.append(label)
            return result
        log('stmt.indexvar: %r', stmt.indexvar)
        log('stmt.labels: %r', stmt.labels)
        indexval = self.eval_rvalue(stmt.indexvar, stmt.loc)
        log('indexval: %r', indexval)
        labels = get_labels_for_rvalue(self, stmt, indexval)
        log('labels: %r', labels)
        result = []
        for label in labels:
            newstate = self.copy()
            bb = self.fun.cfg.get_block_for_label(label.target)
            newstate.loc = Location(bb, 0)
            if label.low:
                check_isinstance(label.low, gcc.IntegerCst)
                if label.high:
                    check_isinstance(label.high, gcc.IntegerCst)
                    desc = 'when following cases %i...%i' % (label.low.constant, label.high.constant)
                else:
                    desc = 'when following case %i' % label.low.constant
            else:
                desc = 'when following default'
            result.append(Transition(self,
                                     newstate,
                                     desc))
        return result

    def get_persistent_refs_for_region(self, dst_region):
        # Locate all regions containing pointers that point at the given region
        # that are either on the heap or are globals (not locals)
        check_isinstance(dst_region, Region)
        result = []
        for src_region in self.get_all_refs_for_region(dst_region):
            if src_region.is_on_stack():
                continue
            result.append(src_region)
        return result

    def get_all_refs_for_region(self, dst_region):
        # Locate all regions containing pointers that point at the given region
        check_isinstance(dst_region, Region)
        result = []
        for src_region in self.value_for_region:
            v = self.value_for_region[src_region]
            if isinstance(v, PointerToRegion):
                if v.region == dst_region:
                    result.append(src_region)
        return result

region_id = 0

class Transition(object):
    __slots__ = ('src', # State
                 'dest', # State
                 'desc', # str
                 )

    def __init__(self, src, dest, desc):
        check_isinstance(src, State)
        check_isinstance(dest, State)
        if desc:
            check_isinstance(desc, str)
        self.src = src
        self.dest = dest
        self.desc = desc

    def __repr__(self):
        return 'Transition(%r, %r)' % (self.dest, self.desc)

    def log(self, logger):
        logger('desc: %r' % self.desc)
        logger('dest:')
        self.dest.log(logger)

class Trace(object):
    __slots__ = ('states', 'transitions', 'err', 'paths_taken')

    """A sequence of States and Transitions"""
    def __init__(self):
        self.states = []
        self.transitions = []
        self.err = None

        # A list of (src Location, dest Location) pairs
        self.paths_taken = []

    def add(self, transition):
        check_isinstance(transition, Transition)
        self.states.append(transition.dest)
        self.transitions.append(transition)
        self.paths_taken.append( (transition.src.loc,
                                  transition.dest.loc) )
        return self

    def add_error(self, err):
        self.err = err

    def copy(self):
        t = Trace()
        t.states = self.states[:]
        t.transitions = self.transitions[:]
        t.err = self.err # FIXME: should this be a copy?
        t.paths_taken = self.paths_taken[:]
        return t

    def log(self, logger, name):
        logger('%s:' % name)
        for i, state in enumerate(self.states):
            logger('%i:' % i)
            state.log(logger)
        if self.err:
            logger('  Trace ended with error: %s' % self.err)

    def get_last_stmt(self):
        return self.states[-1].loc.get_stmt()

    def return_value(self):
        return self.states[-1].return_rvalue

    def has_looped(self):
        """
        Is the tail transition a path we've followed before?
        """
        endstate = self.states[-1]
        if hasattr(endstate, 'fromsplit'):
            # We have a state that was created from a SplitValue.  It will have
            # the same location as the state before it (before the split).
            # Don't treat it as a loop:
            return False
        if endstate.not_returning:
            # The handler not "exit" etc leads to a transition that has a
            # repeated location:
            return False

        endtransition = self.transitions[-1]
        if 0:
            gcc.inform(endstate.get_gcc_loc(endstate.fun),
                       ('paths_taken: %s'
                        % (self.paths_taken,)))
            gcc.inform(endstate.get_gcc_loc(endstate.fun),
                       'src, loc: %s' % ((endtransition.src.loc, endtransition.dest.loc),))

        # Is this a path we've followed before?
        if (endtransition.src.loc, endtransition.dest.loc) in self.paths_taken[0:-1]:
            return True

    def get_all_var_region_pairs(self):
        """
        Get the list of all (LHS,region) pairs in region_for_var within all of
        the states in this trace, without duplicates
        """
        result = []
        for s_iter in self.states:
            for var_iter, r_iter in s_iter.region_for_var.items():
                pair = (var_iter, r_iter)
                if pair not in result:
                    result.append(pair)
        return result

    def var_points_unambiguously_to(self, r_srcptr, r_dstptr):
        """
        Does the source region (a pointer variable) always point to the
        destination region (or be NULL, or uninitialized) throughout all of
        the states in this trace?
        """
        ever_had_value = False
        #print('r_srcptr, r_dstptr: %r, %r' % (r_srcptr, r_dstptr))
        for s_iter in self.states:
            if r_srcptr not in s_iter.value_for_region:
                continue

            v_srcptr = s_iter.value_for_region[r_srcptr]
            #print ('v_srcptr: %s' % v_srcptr)

            # It doesn't matter if it's uninitialized, or NULL:
            if isinstance(v_srcptr, UninitializedData):
                continue
            if isinstance(v_srcptr, ConcreteValue):
                if v_srcptr.is_null_ptr():
                    continue
            if isinstance(v_srcptr, PointerToRegion):
                if v_srcptr.region == r_dstptr:
                    ever_had_value = True
                    continue
                else:
                    # This variable is pointing at another region at
                    # this point within the trace:
                    return False

            # Some kind of value we weren't expecting:
            return False

        # If we get here, there was no state in which the var pointed to
        # anything else.
        #
        # If it ever pointed to the region in question, then it's a good way
        # of referring to the region:
        return ever_had_value

    def get_description_for_region(self, r_in):
        """
        Try to come up with a human-readable description of the input region
        """
        check_isinstance(r_in, Region)

        # If a local pointer variable has just the given region as a value (as
        # well as its initial "uninitialized" or NULL states), then that's a
        # good name for this region:
        for var_iter, r_iter in self.get_all_var_region_pairs():
            if self.var_points_unambiguously_to(r_iter, r_in):
                if isinstance(r_iter, (RegionForLocal, RegionForGlobal)):
                    # Only do it for variables with names, not for temporaries:
                    if r_iter.vardecl.name:
                        return "'*%s'" % r_iter.vardecl.name

        # Otherwise, just use the name of the region
        return r_in.name

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

    def log(self, logger):
        logger('resources:')
        logger('acquisitions: %s' % self._acquisitions)
        logger('releases: %s' % self._releases)

class TooComplicated(Exception):
    """
    The function is too complicated for the checker to analyze.
    """
    pass

class Limits:
    """
    Resource limits, to avoid an analysis going out of control
    """
    def __init__(self, maxtrans):
        self.maxtrans = maxtrans
        self.trans_seen = 0

    def on_transition(self, transition):
        self.trans_seen += 1
        if self.trans_seen > self.maxtrans:
            raise TooComplicated()

def iter_traces(fun, facets, prefix=None, limits=None):
    """
    Traverse the tree of traces of program state, returning a list
    of Trace instances.

    For now, don't include any traces that contain loops, as a primitive
    way of ensuring termination of the analysis
    """
    log('iter_traces(%r, %r, %r)', fun, facets, prefix)
    if prefix is None:
        prefix = Trace()
        curstate = State(fun,
                         Location.get_block_start(fun.cfg.entry),
                         facets,
                         None, None, None)
        #Resources())
        curstate.init_for_function(fun)
        for key in facets:
            facet_cls = facets[key]
            f_new = facet_cls(curstate, fun=fun)
            setattr(curstate, key, f_new)
            f_new.init_for_function(fun)
    else:
        check_isinstance(prefix, Trace)
        curstate = prefix.states[-1]

        if curstate.has_returned:
            # This state has returned a value (and hence terminated):
            return [prefix]

        if curstate.not_returning:
            # This state has called "exit" or similar, and thus this
            # trace should terminate:
            return [prefix]

        # Stop interpreting when you see a loop, to ensure termination:
        if prefix.has_looped():
            log('loop detected; stopping iteration')
            if 0:
                gcc.inform(curstate.get_gcc_loc(fun),
                           'loop detected; stopping iteration')
            # Don't return the prefix so far: it is not a complete trace
            return []

    # We need the prevstate in order to handle Phi nodes
    if len(prefix.states) > 1:
        prevstate = prefix.states[-2]
    else:
        prevstate = None

    prefix.log(log, 'PREFIX')
    log('  %s:%s', fun.decl.name, curstate.loc)
    try:
        transitions = curstate.get_transitions()
        check_isinstance(transitions, list)
    except PredictedError:
        # We're at a terminating state:
        err = sys.exc_info()[1]
        err.loc = prefix.get_last_stmt().loc
        trace_with_err = prefix.copy()
        trace_with_err.add_error(err)
        trace_with_err.log(log, 'FINISHED TRACE WITH ERROR: %s' % err)
        return [trace_with_err]
    except SplitValue:
        # Split the state up, splitting into parallel worlds with different
        # values for the given value
        # FIXME: this doesn't work; it thinks it's a loop :(
        err = sys.exc_info()[1]
        transitions = err.split(curstate)
        check_isinstance(transitions, list)

    log('transitions: %s', transitions)

    if len(transitions) > 0:
        result = []
        for transition in transitions:
            check_isinstance(transition, Transition)
            transition.dest.verify()

            if limits:
                limits.on_transition(transition)

            newprefix = prefix.copy().add(transition)

            # Recurse:
            for trace in iter_traces(fun, facets, newprefix, limits):
                result.append(trace)
        return result
    else:
        # We're at a terminating state:
        prefix.log(log, 'FINISHED TRACE')
        return [prefix]

class StateGraph:
    """
    A graph of states, representing the various routes through a function,
    tracking state.

    For now, we give up when we encounter a loop, as an easy way to ensure
    termination of the analysis
    """
    def __init__(self, fun, logger, stateclass):
        check_isinstance(fun, gcc.Function)
        self.fun = fun
        self.states = []
        self.transitions = []
        self.stateclass = stateclass

        logger('StateGraph.__init__(%r)' % fun)

        # Recursively gather states:
        initial = stateclass(Location.get_block_start(fun.cfg.entry),
                             None, None, None,
                             Resources(),
                             ConcreteValue(get_PyObjectPtr(), fun.start, 0))
        initial.init_for_function(fun)
        self.states.append(initial)
        self._gather_states(initial, logger)

    def _gather_states(self, curstate, logger):
        logger('  %s:%s' % (self.fun.decl.name, curstate.loc))
        try:
            transitions = curstate.get_transitions()
            #print transitions
            check_isinstance(transitions, list)
        except PredictedError:
            # We're at a terminating state:
            err = sys.exc_info()[1]
            errstate = curstate.copy()
            transition = Transition(curstate, errstate, str(err))
            self.states.append(transition.dest)
            self.transitions.append(transition)
            return

        logger('transitions:', 2)
        for t in transitions:
            t.log(logger, 3)

        if len(transitions) > 0:
            for transition in transitions:
                # FIXME: what about loops???
                check_isinstance(transition, Transition)
                self.states.append(transition.dest)
                self.transitions.append(transition)

                if transition.dest.has_returned():
                    # This state has returned a value (and hence terminated)
                    continue

                if transition.dest.not_returning():
                    # This state has called "exit" or similar, and thus this
                    # trace should terminate:
                    continue

                # Recurse:
                self._gather_states(transition.dest, logger)
        else:
            # We're at a terminating state:
            logger('FINISHED TRACE')

    def get_prev_state(self, state):
        assert state in self.states
        for t in self.transitions:
            if t.dest == state:
                return t.src
        # Not found:
        return None

def extra_text(msg, indent):
    sys.stderr.write('%s%s\n' % ('  ' * indent, msg))

