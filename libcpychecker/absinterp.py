#   Copyright 2011, 2012 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2011, 2012 Red Hat, Inc.
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
import re
import sys
from six import StringIO, integer_types
from gccutils import get_src_for_loc, get_nonnull_arguments, check_isinstance
from collections import OrderedDict
from libcpychecker.utils import log, logging_enabled
from libcpychecker.types import *
from libcpychecker.diagnostics import location_as_json, type_as_json

debug_comparisons = 0

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

# Valid 'opname' parameters to eval_comparison hooks:
opnames = frozenset(['eq', 'ge', 'gt', 'le', 'lt'])

def raw_comparison(a, opname, b):
    assert opname in opnames
    if opname == 'eq':
        return a == b
    elif opname == 'ge':
        return a >= b
    elif opname == 'gt':
        return a > b
    elif opname == 'le':
        return a <= b
    elif opname == 'lt':
        return a < b
    else:
        raise ValueError()

def flip_opname(opname):
    """
    Given:
      A op B
    get the op' for:
      B op' A
    that has the same results
    """
    assert opname in opnames
    if opname == 'eq':
        return 'eq' # symmetric
    elif opname == 'ge':
        return 'le'
    elif opname == 'gt':
        return 'lt'
    elif opname == 'le':
        return 'ge'
    elif opname == 'lt':
        return 'gt'
    else:
        raise ValueError()

if debug_comparisons:
    debug_indent = 0
    # Decorator for adding debug tracking to the various comparison operators
    def dump_comparison(f):
        def impl_fn(self, *args):
            global debug_indent
            print('%s%s.%s:' % ('  ' * debug_indent, self.__class__.__name__, f.__name__))
            for arg in [self] + list(args):
                print(' %s%s' % ('  ' * debug_indent, arg))
            debug_indent += 1
            r = f(self, *args)
            debug_indent -= 1
            print('%sreturned: %s' % ('  ' * debug_indent, r))
            return r
        return impl_fn
    def debug_comparison(msg):
        print('%s%s' % ('  ' * debug_indent, msg))
else:
    # empty decorator
    def dump_comparison(f):
        return f

########################################################################

class FnMeta(object):
    """
    Metadata describing an API function
    """
    __slots__ = ('name', # the name of the function
                 'docurl', # URL of the API documentation, on docs.python.org
                 'declared_in', # name of the header file in which this is declared
                 'prototype', # fragment of C giving the prototype (for documentation purposes)
                 'defined_in', # where is this function defined (in CPython)
                 'notes', # fragment of text, giving notes on the function
                 )
    def __init__(self, **kwargs):
        for key in self.__slots__:
            setattr(self, key, None)
        for key, value in kwargs.items():
            setattr(self, key, value)

    def desc_when_call_returns_value(self, valuedesc):
        """
        Generate descriptive text for a Transition involving a call to this
        function that returns some value (described in string form)

        e.g. "when PyTuple_Size() returns ob_size"
        """
        return 'when %s() returns %s' % (self.name, valuedesc)

    def desc_when_call_succeeds(self):
        """
        Generate descriptive text for a Transition involving a call to this
        function that succeeds.

        e.g. "when PyTuple_SetItem() succeeds"
        """
        return 'when %s() succeeds' % self.name

    def desc_when_call_fails(self, why=None):
        """
        Generate descriptive text for a Transition involving a call to this
        function that fails, optionally with a textual description of the
        kind of failure

        e.g. "when PyTuple_SetItem() fails (index out of range)"
        """
        if why:
            return 'when %s() fails (%s)' % (self.name, why)
        else:
            return 'when %s() fails' % self.name

    def desc_special(self, event):
        """
        Generate descriptive text for a Transition involving a call to this
        function that does somthing unusual

        e.g. "when PyString_Concat() does nothing due to NULL *lhs"
        """
        return 'when %s() %s' % (self.name, event)

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

    def as_json(self, state):
        result = dict(kind=self.__class__.__name__,
                      gcctype=type_as_json(self.gcctype),
                      value_comes_from=location_as_json(self.loc))
        # Get extra per-class JSON fields:
        result.update(self.json_fields(state))
        return result

    def json_fields(self, state):
        # Hook for getting extra per-class fields for JSON serialization
        # Empty for the base class
        return dict()

    def is_null_ptr(self):
        """
        Is this AbstractValue *definitely* a NULL pointer?
        """
        # Overridden by ConcreteValue
        return False

    def get_transitions_for_function_call(self, state, stmt):
        """
        For use for handling function pointers.  Return a list of Transition
        instances giving the outcome of calling this function ptr value
        """
        check_isinstance(state, State)
        check_isinstance(stmt, gcc.GimpleCall)
        returntype = stmt.fn.type.dereference.type

        from libcpychecker.refcounts import type_is_pyobjptr_subclass
        if type_is_pyobjptr_subclass(returntype):
            log('Invocation of function pointer returning PyObject * (or subclass)')
            # Assume that all such functions either:
            #   - return a new reference, or
            #   - return NULL and set an exception (e.g. MemoryError)
            return state.cpython.make_transitions_for_new_ref_or_fail(stmt,
                                                                      None,
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

    def eval_binop(self, exprcode, rhs, rhsdesc, gcctype, loc):
        raise NotImplementedError

    @dump_comparison
    def eval_comparison(self, opname, rhs, rhsdesc):
        """
        opname is a string in opnames
        Return a boolean, or None (meaning we don't know)
        """
        raise NotImplementedError("eval_comparison for %s (%s)" % (self, opname))

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

    def eval_binop(self, exprcode, rhs, rhsdesc, gcctype, loc):
        return UnknownValue.make(gcctype, loc)

    @dump_comparison
    def eval_comparison(self, opname, rhs, rhsdesc):
        if opname == 'eq':
            # If it's the *same* value, it's equal to itself:
            if self is rhs:
                return True
        return None

    def extract_from_parent(self, region, gcctype, loc):
        return UnknownValue.make(gcctype, loc)

    def union(self, v_other):
        check_isinstance(v_other, AbstractValue)
        return self

def eval_binop(exprcode, a, b, rhsvalue):
    """
    Evaluate a gcc exprcode on a pair of Python values (as opposed to
    AbstractValue instances)
    """
    log('eval_binop(%s, %s, %s)', exprcode, a, b)
    assert isinstance(a, numeric_types)
    assert isinstance(b, numeric_types)
    assert isinstance(rhsvalue, AbstractValue)

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

    try:
        result = inner()
    except (ArithmeticError, ValueError):
        err = sys.exc_info()[1]
        isdefinite = not hasattr(rhsvalue, 'fromsplit')
        raise PredictedArithmeticError(err, rhsvalue, isdefinite)
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
            return ('(%s)%s from %s'
                    % (self.gcctype, value_to_str(self.value), self.loc))
        else:
            return ('(%s)%s'
                    % (self.gcctype, value_to_str(self.value)))

    def __repr__(self):
        return ('ConcreteValue(gcctype=%r, loc=%r, value=%s)'
                % (str(self.gcctype), self.loc, value_to_str(self.value)))

    def json_fields(self, state):
        return dict(value=self.value)

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
            if isinstance(self.gcctype, gcc.IntegerType) \
                    and isinstance(gcctype, gcc.IntegerType):
                if (self.value >= gcctype.min_value.constant
                    and self.value <= gcctype.max_value.constant):
                    # The old range will convert OK to the new type:
                    return ConcreteValue(gcctype, loc, self.value)
            # We might lose information e.g. truncation; be pessimistic for now:
            return UnknownValue.make(gcctype, loc)
        elif exprcode == gcc.FixTruncExpr:
            return ConcreteValue(gcctype, loc, int(self.value))
        elif exprcode == gcc.FloatExpr:
            return ConcreteValue(gcctype, loc, float(self.value))
        else:
            raise NotImplementedError("Don't know how to cope with exprcode: %r (%s) on %s at %s"
                                      % (exprcode, exprcode, self, loc))

    def eval_binop(self, exprcode, rhs, rhsdesc, gcctype, loc):
        if isinstance(rhs, ConcreteValue):
            newvalue = eval_binop(exprcode, self.value, rhs.value, rhs)
            if newvalue is not None:
                return ConcreteValue(gcctype, loc, newvalue)
        return UnknownValue.make(gcctype, loc)

    @dump_comparison
    def eval_comparison(self, opname, rhs, rhsdesc):
        log('ConcreteValue.eval_comparison(%s, %s%s)', self, opname, rhs)
        if isinstance(rhs, ConcreteValue):
            return raw_comparison(self.value, opname, rhs.value)
        elif isinstance(rhs, WithinRange):
            # Specialcase for equality:
            if opname == 'eq':
                if not rhs.contains(self.value):
                    return False
                # Split into 2 or 3 parts:
                ranges = []
                if rhs.minvalue < self.value:
                    # subrange that's <
                    ranges.append(WithinRange.make(rhs.gcctype,
                                                   rhs.loc,
                                                   rhs.minvalue,
                                                   self.value-1))
                ranges.append(WithinRange.make(rhs.gcctype,
                                               rhs.loc,
                                               self.value))
                if self.value < rhs.maxvalue:
                    # subrange that's >
                    ranges.append(WithinRange.make(rhs.gcctype,
                                                   rhs.loc,
                                                   self.value+1,
                                                   rhs.maxvalue))
                rhs.raise_split(rhsdesc, *ranges)

            # For everything else (inequalities), consider ranges:
            self_vs_min = raw_comparison(self.value, opname, rhs.minvalue)
            self_vs_max = raw_comparison(self.value, opname, rhs.maxvalue)
            if self_vs_min == self_vs_max:
                return self_vs_min
            else:
                # Prepare a split, autogenerating the appropriate
                # boundaries:
                class RangeOfComparison:
                    """
                    A range over which the comparison against the ConcreteValue
                    has a constant value
                    """
                    __slots__ = ('rng', 'result')
                    def __init__(self, rng, result):
                        check_isinstance(rng, (ConcreteValue, WithinRange))
                        check_isinstance(result, (bool, None))
                        self.rng = rng
                        self.result = result
                    def __repr__(self):
                        return ('RangeOfComparison(%r, %r)'
                                % (self.rng, self.result))

                # Where are the boundary values?
                raw_boundaries = sorted(list(set([self.value - 1,
                                                  self.value,
                                                  self.value + 1,
                                                  rhs.minvalue,
                                                  rhs.maxvalue])))
                # Filter them to be within the existing range:
                raw_boundaries = [v
                                  for v in raw_boundaries
                                  if rhs.contains(v)]
                if debug_comparisons:
                    debug_comparison([value_to_str(v) for v in raw_boundaries])

                # Calculate a minimal list of RangeOfComparison instances
                # Within each one, the comparison against the ConcreteValue has
                # a consistent result:
                ranges = []
                num_boundary_ranges = len(raw_boundaries)
                if debug_comparisons:
                    debug_comparison('num_boundary_ranges: %r' % num_boundary_ranges)
                for i in range(num_boundary_ranges):
                    minvalue = raw_boundaries[i]
                    if minvalue < rhs.gcctype.min_value.constant:
                        minvalue = rhs.gcctype.min_value.constant

                    if i < num_boundary_ranges - 1:
                        # Extend up to but not including the next range:
                        maxvalue = raw_boundaries[i + 1] - 1
                    else:
                        # Final range: use full range:
                        maxvalue = rhs.maxvalue

                    if maxvalue > rhs.gcctype.max_value.constant:
                        maxvalue = rhs.gcctype.max_value.constant

                    if debug_comparisons:
                        debug_comparison('%i [%s..%s]'
                                         % (i,
                                            value_to_str(minvalue),
                                            value_to_str(maxvalue)))

                    check_isinstance(minvalue, numeric_types)
                    check_isinstance(maxvalue, numeric_types)

                    # Only "proper" ranges:
                    if minvalue <= maxvalue:
                        self_vs_min = raw_comparison(self.value, opname, minvalue)
                        self_vs_max = raw_comparison(self.value, opname, maxvalue)

                        # All ranges should have identical value when compared
                        # against the concrete value:
                        assert self_vs_min == self_vs_max
                        if debug_comparisons:
                            debug_comparison('  [%s..%s] %s %s ?: %s'
                                             % (value_to_str(minvalue),
                                                value_to_str(maxvalue),
                                                opname, self.value,
                                                self_vs_min))

                        if ranges and ranges[-1].result == self_vs_min:
                            # These ranges are adjacent and have the same result;
                            # merge them:
                            oldrange = ranges[-1].rng
                            if isinstance(oldrange, ConcreteValue):
                                newrange = WithinRange(oldrange.gcctype,
                                                       oldrange.loc,
                                                       oldrange.value,
                                                       maxvalue)
                            else:
                                check_isinstance(oldrange, WithinRange)
                                newrange = WithinRange(oldrange.gcctype,
                                                       oldrange.loc,
                                                       oldrange.minvalue,
                                                       maxvalue)
                            ranges[-1].rng = newrange
                        else:
                            # We have a range with a different value:
                            roc = RangeOfComparison(WithinRange.make(rhs.gcctype, rhs.loc,
                                                                     minvalue, maxvalue),
                                                    self_vs_min)
                            ranges.append(roc)

                if debug_comparisons:
                    from pprint import pprint
                    pprint(ranges)
                rhs.raise_split(rhsdesc, *[roc.rng for roc in ranges])
        return None

    def extract_from_parent(self, region, gcctype, loc):
        return ConcreteValue(gcctype, loc, self.value)

    def union(self, v_other):
        check_isinstance(v_other, AbstractValue)
        if isinstance(v_other, ConcreteValue):
            if self.value == v_other.value:
                return self
            return WithinRange.make(self.gcctype, self.loc,
                               self.value, v_other.value)
        if isinstance(v_other, WithinRange):
            return WithinRange.make(self.gcctype, self.loc,
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

        # Clamp to be within the type's expressible range:
        if self.minvalue < gcctype.min_value.constant:
            self.minvalue = gcctype.min_value.constant
        if self.maxvalue > gcctype.max_value.constant:
            self.maxvalue = gcctype.max_value.constant

    @classmethod
    def make(cls, gcctype, loc, *values):
        """
        Generate a WithinRange instance, unless the range uniqely identifies
        a value, in which case generate a ConcreteValue instance
        """
        minvalue = min(values)
        maxvalue = max(values)
        if minvalue == maxvalue:
            return ConcreteValue(gcctype, loc, minvalue)
        else:
            return WithinRange(gcctype, loc, minvalue, maxvalue)

    @classmethod
    def ge_zero(cls, gcctype, loc):
        """
        Make a WithinRange for the given type, assuming a value >= 0, up to
        the maximum value representable by the type
        """
        return WithinRange(gcctype, loc, 0, gcctype.max_value.constant)

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

    def json_fields(self, state):
        return dict(minvalue=self.minvalue,
                    maxvalue=self.maxvalue)

    def eval_unary_op(self, exprcode, gcctype, loc):
        if exprcode == gcc.AbsExpr:
            values = [abs(val)
                      for val in (self.minvalue, self.maxvalue)]
            return WithinRange.make(gcctype, loc, min(values), max(values))
        elif exprcode == gcc.BitNotExpr:
            return UnknownValue.make(gcctype, loc)
        elif exprcode == gcc.NegateExpr:
            return WithinRange.make(gcctype, loc, -self.maxvalue, -self.minvalue)
        elif exprcode == gcc.ConvertExpr:
            # Is the whole of this range fully expressible within the new type?
            # If not, we might lose information
            if isinstance(self.gcctype, gcc.IntegerType) \
                    and isinstance(gcctype, gcc.IntegerType):
                if (self.minvalue >= gcctype.min_value.constant
                    and self.maxvalue <= gcctype.max_value.constant):
                    # The old range will convert OK to the new type:
                    return WithinRange.make(gcctype, loc,
                                       self.minvalue, self.maxvalue)
            # We might lose information e.g. truncation; be pessimistic for now:
            return UnknownValue.make(gcctype, loc)
        elif exprcode == gcc.FloatExpr:
            return UnknownValue.make(gcctype, loc)
        else:
            raise NotImplementedError("Don't know how to cope with exprcode: %r (%s) on %s at %s"
                                      % (exprcode, exprcode, self, loc))

    def eval_binop(self, exprcode, rhs, rhsdesc, gcctype, loc):
        if isinstance(rhs, ConcreteValue):
            values = [eval_binop(exprcode, val, rhs.value, rhs)
                      for val in (self.minvalue, self.maxvalue)]
            return WithinRange.make(gcctype, loc, min(values), max(values))
        elif isinstance(rhs, WithinRange):
            # Assume that the operations are "concave" in that the resulting
            # range is within that found by trying all four corners:

            # Avoid division by zero:
            # (see https://fedorahosted.org/gcc-python-plugin/ticket/25 )
            if exprcode == gcc.TruncDivExpr or exprcode == gcc.TruncModExpr:
                if rhs.minvalue == 0 and rhs.maxvalue > 0:
                    zero_range = WithinRange.make(rhs.gcctype, rhs.loc, 0)
                    gt_zero_range = WithinRange.make(rhs.gcctype, rhs.loc,
                                                1, rhs.maxvalue)
                    rhs.raise_split(rhsdesc, zero_range, gt_zero_range)

            # Avoid negative shifts:
            # (see https://fedorahosted.org/gcc-python-plugin/ticket/14 )
            if exprcode == gcc.LshiftExpr or exprcode == gcc.RshiftExpr:
                if rhs.minvalue < 0 and rhs.maxvalue >= 0:
                    neg_range = WithinRange.make(rhs.gcctype, rhs.loc,
                                            rhs.minvalue, -1)
                    ge_zero_range = WithinRange.make(rhs.gcctype, rhs.loc,
                                                0, rhs.maxvalue)
                    rhs.raise_split(rhsdesc, neg_range, ge_zero_range)

            values = (eval_binop(exprcode, self.minvalue, rhs.minvalue, rhs),
                      eval_binop(exprcode, self.minvalue, rhs.maxvalue, rhs),
                      eval_binop(exprcode, self.maxvalue, rhs.minvalue, rhs),
                      eval_binop(exprcode, self.maxvalue, rhs.maxvalue, rhs))
            return WithinRange.make(gcctype, loc,
                               min(values),
                               max(values))
        return UnknownValue.make(gcctype, loc)

    def contains(self, rawvalue):
        check_isinstance(rawvalue, numeric_types)
        return self.minvalue <= rawvalue and rawvalue <= self.maxvalue

    @dump_comparison
    def eval_comparison(self, opname, rhs, rhsdesc):
        log('WithinRange.eval_comparison(%s, %s%s)', self, opname, rhs)

        # If it's the *same* value, it's equal to itself:
        if opname == 'eq':
            if self is rhs:
                return True

            if isinstance(rhs, WithinRange):
                # They can only be equal if there's an overlap:
                if self.contains(rhs.minvalue) or self.contains(rhs.maxvalue):
                    # Maybe equal:
                    return None
                else:
                    # No overlap: definitely non-equal:
                    return False

        if isinstance(rhs, ConcreteValue):
            # to implement WithinRange op ConcreteValue, use:
            #   ConcreteValue flip(op) WithinRange
            return rhs.eval_comparison(flip_opname(opname), self, None)

        return None

    def raise_split(self, valuedesc, *new_ranges):
        """
        Raise a SplitValue exception to subdivide this range into subranges
        """
        descriptions = []
        if valuedesc is None:
            valuedesc = 'value'
        for r in new_ranges:
            if isinstance(r, WithinRange):
                descriptions.append('when considering range: %s <= %s <= %s' %
                                    (value_to_str(r.minvalue),
                                     valuedesc,
                                     value_to_str(r.maxvalue)))
            elif isinstance(r, ConcreteValue):
                descriptions.append('when considering %s == %s' % (valuedesc, r))
            else:
                raise TypeError('unrecognized type: %r' % r)
        raise SplitValue(self, new_ranges, descriptions)

    def raise_as_concrete(self, loc, value, desc):
        """
        Raise a SplitValue exception to reinterpret this range as a specific
        ConcreteValue from now on.

        This is slightly abusing the SplitValue mechanism, as it's just one
        new value, but it should at least add the descriptive text into the
        trace.
        """
        if loc:
            check_isinstance(loc, gcc.Location)
        check_isinstance(value, numeric_types)
        check_isinstance(desc, str)
        v_new = ConcreteValue(self.gcctype, loc,
                              value)
        raise SplitValue(self, [v_new], [desc])

    def extract_from_parent(self, region, gcctype, loc):
        return WithinRange.make(gcctype, self.loc, self.minvalue, self.maxvalue)

    def union(self, v_other):
        check_isinstance(v_other, AbstractValue)
        if isinstance(v_other, ConcreteValue):
            return WithinRange.make(self.gcctype, self.loc,
                               *(self.minvalue, self.maxvalue, v_other.value))
        if isinstance(v_other, WithinRange):
            return WithinRange.make(self.gcctype, self.loc,
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

    def json_fields(self, state):
        return dict(target=self.region.as_json())

    def eval_comparison(self, opname, rhs, rhsdesc):
        log('PointerToRegion.eval_comparison:(%s, %s%s)', self, opname, rhs)

        if opname == 'eq':
            if isinstance(rhs, ConcreteValue) and rhs.value == 0:
                log('ptr to region vs 0: %s is definitely not equal to %s', self, rhs)
                return False

            if isinstance(rhs, PointerToRegion):
                log('comparing regions: %s %s', self, rhs)
                return self.region == rhs.region

            # We don't know:
            return None

    def eval_unary_op(self, exprcode, gcctype, loc):
        if exprcode == gcc.ConvertExpr:
            # Casting of this non-NULL pointer to another type:
            return UnknownValue.make(gcctype, loc)

        # Defer to base class:
        AbstractValue.eval_unary_op(self, exprcode, gcctype, loc)

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

def make_null_ptr(gcctype, loc):
    return ConcreteValue(gcctype, loc, 0)

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

class PredictedArithmeticError(PredictedError):
    def __init__(self, err, rhsvalue, isdefinite):
        check_isinstance(err, (ArithmeticError, ValueError))
        self.err = err
        self.rhsvalue = rhsvalue
        self.isdefinite = isdefinite

    def __str__(self):
        if self.isdefinite:
            return '%s with right-hand-side %s' % (self.err, self.rhsvalue)
        else:
            return 'possible %s with right-hand-side %s' % (self.err, self.rhsvalue)

class UsageOfUninitializedData(PredictedValueError):
    def __init__(self, state, expr, value, desc):
        check_isinstance(state, State)
        check_isinstance(expr, gcc.Tree)
        check_isinstance(value, AbstractValue)
        PredictedValueError.__init__(self, state, expr, value, True)
        check_isinstance(desc, str)
        self.desc = desc

    def __str__(self):
        return ('%s at %s'
                % (self.desc, self.state.loc.get_stmt().loc))

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
    def __init__(self, state, stmt, idx, ptr, isdefinite, why):
        check_isinstance(state, State)
        check_isinstance(stmt, gcc.Gimple)
        check_isinstance(idx, int)
        check_isinstance(ptr, AbstractValue)
        if why is not None:
            check_isinstance(why, str)
        PredictedValueError.__init__(self, state, stmt.args[idx], ptr, isdefinite)
        self.stmt = stmt
        self.idx = idx
        # this is a 0-based index; it is changed to a 1-based index when
        # printed
        self.why = why

    def __str__(self):
        if self.isdefinite:
            return ('calling %s with NULL as argument %i (%s) at %s'
                    % (self.stmt.fn,
                       self.idx + 1,
                       self.expr,
                       self.state.loc.get_stmt().loc))
        else:
            return ('possibly calling %s with NULL as argument %i (%s) at %s'
                    % (self.stmt.fn,
                       self.idx + 1,
                       self.expr,
                       self.state.loc.get_stmt().loc))



class ReadFromDeallocatedMemory(PredictedError):
    def __init__(self, stmt, value):
        check_isinstance(stmt, gcc.Gimple)
        check_isinstance(value, DeallocatedMemory)
        self.stmt = stmt
        self.value = value

    def __str__(self):
        return ('reading from deallocated memory at %s: %s'
                % (self.stmt.loc, self.value))

class PassingPointerToDeallocatedMemory(PredictedError):
    def __init__(self, argidx, fnname, stmt, value):
        check_isinstance(stmt, gcc.Gimple)
        check_isinstance(value, DeallocatedMemory)
        self.argidx = argidx
        self.fnname = fnname
        self.stmt = stmt
        self.value = value

    def __str__(self):
        return ('passing pointer to deallocated memory as argument %i of %s at %s: %s'
                % (self.argidx + 1, self.fnname, self.stmt.loc, self.value))


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

    def as_json(self):
        m = re.match(r"region for gcc.ParmDecl\('(\S+)'\)\.(\S+)", self.name)
        if m:
            return '%s->%s' % (m.group(1), m.group(2))
        return self.name

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

    def as_json(self):
        return str(self.vardecl)

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

    def as_json(self):
        return str(self.vardecl)

class RegionForStaticLocal(RegionForGlobal):
    # "static" locals work more like globals.  In particular, they're not on
    # the stack
    pass

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

    def as_json(self):
        return str(repr(self.text))

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

    def as_json(self, desc):
        variables = OrderedDict()
        for k in self.region_for_var:
            region = self.region_for_var[k]
            value = self.value_for_region.get(region, None)
            if value:
                variables[region.as_json()] = value.as_json(self)
        result = dict(location=location_as_json(self.loc.get_gcc_loc()),
                      message=desc,
                      variables=variables)
        return result

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
        if isinstance(expr, gcc.RealCst):
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
                self.value_for_region[ob_refcnt] = RefcountValue.borrowed_ref(None, region)
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
            # Offset of zero? just reuse the existing pointer's region:
            if index == 0:
                return a.region
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
        if field:
            # (field can be None for C++ destructors)
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
        """
        Lookup region->field, getting its AbstractValue, if any, or None

        For use in writing selftests and diagnostics, as it has no
        side-effects.

        You may want to use read_field_by_name() instead
        """
        log('get_value_of_field_by_region(%r, %r)', region, field)
        check_isinstance(region, Region)
        check_isinstance(field, str)
        if field in region.fields:
            field_region = region.fields[field]
            return self.value_for_region.get(field_region, None)
        return None

    def read_field_by_name(self, stmt, gcctype, region, fieldname):
        """
        Lookup region->field, getting its AbstractValue.

        If the field doesn't have a value yet, if will be set to a new
        UnknownValue so that subsequent reads of the field receive the
        *same* unknown value
        """
        log('read_field_by_name(%r, %r)', region, fieldname)
        check_isinstance(stmt, gcc.Gimple)
        if gcctype:
            check_isinstance(gcctype, gcc.Type)
        check_isinstance(region, Region)
        check_isinstance(fieldname, str)

        v_field = self.get_value_of_field_by_region(region,
                                                    fieldname)
        if v_field is None:
            v_field = UnknownValue.make(gcctype, stmt.loc)
            r_field = self.make_field_region(region,
                                             fieldname)
            self.value_for_region[r_field] = v_field

        return v_field

    def set_field_by_name(self, r_struct, fieldname, v_field):
        r_field = self.make_field_region(r_struct, fieldname)
        self.value_for_region[r_field] = v_field

    def dereference(self, expr, v_ptr, loc):
        check_isinstance(v_ptr, AbstractValue)

        if isinstance(v_ptr, UnknownValue):
            self.raise_split_value(v_ptr, loc)
        self.raise_any_null_ptr_deref(expr, v_ptr)

        check_isinstance(v_ptr, PointerToRegion)
        if v_ptr.region not in self.value_for_region:
            # Add a new UnknownValue:
            if v_ptr.gcctype:
                gcctype = v_ptr.gcctype.dereference
            else:
                gcctype = None
            self.value_for_region[v_ptr.region] = UnknownValue.make(gcctype, loc)
        return self.value_for_region[v_ptr.region]

    def init_for_function(self, fun):
        log('State.init_for_function(%r)', fun)
        self.fun = fun
        root_region = Region('root', None)
        stack = RegionOnStack('stack for %s' % fun.decl.name, root_region)

        nonnull_args = get_nonnull_arguments(fun.decl.type)
        for idx, parm in enumerate(fun.decl.arguments):
            def parm_is_this():
                if idx == 0 and parm.is_artificial and parm.name == 'this':
                    return True
            region = RegionForLocal(parm, stack)
            self.region_for_var[parm] = region
            if idx in nonnull_args or parm_is_this() \
                    or isinstance(parm.type, gcc.ReferenceType):
                # Make a non-NULL ptr:
                other = Region('region-for-arg-%r' % parm, None)
                self.region_for_var[other] = other
                self.value_for_region[region] = PointerToRegion(parm.type, parm.location, other)
            else:
                self.value_for_region[region] = UnknownValue.make(parm.type, parm.location)
        for local in fun.local_decls:
            if local.static:
                # Statically-allocated locals are zero-initialized before the
                # function is called for the first time, and then preserve
                # state between function calls
                region = RegionForStaticLocal(local)

                # For now, don't try to track all possible values a static var
                # can take; simply treat it as an UnknownValue
                v_local = UnknownValue.make(local.type, fun.start)
            else:
                region = RegionForLocal(local, stack)
                v_local = UninitializedData(local.type, fun.start)
            self.region_for_var[local] = region
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
                      'dereferencing uninitialized pointer (%s)' % expr)

        if ptr.is_null_ptr():
            # Read through NULL
            # If we earlier split the analysis into NULL/non-NULL
            # cases, then we're only considering the possibility
            # that this pointer was NULL; we don't know for sure
            # that it was.
            isdefinite = not hasattr(ptr, 'fromsplit')
            raise NullPtrDereference(self, expr, ptr, isdefinite)

    def raise_any_null_ptr_func_arg(self, stmt, idx, ptr, why=None):
        # idx is the 0-based index of the argument

        check_isinstance(stmt, gcc.Gimple)
        check_isinstance(idx, int)
        check_isinstance(ptr, AbstractValue)
        if why:
            check_isinstance(why, str)
        if isinstance(ptr, UnknownValue):
            self.raise_split_value(ptr, stmt.loc)
        if ptr.is_null_ptr():
            # NULL argument to a function that requires non-NULL
            # If we earlier split the analysis into NULL/non-NULL
            # cases, then we're only considering the possibility
            # that this pointer was NULL; we don't know for sure
            # that it was.
            isdefinite = not hasattr(ptr, 'fromsplit')
            raise NullPtrArgument(self, stmt, idx, ptr, isdefinite, why)

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

    def deallocate_region(self, stmt, region):
        # Mark the region as deallocated
        # Since regions are shared with other states, we have to set this up
        # for this state by assigning it with a special "DeallocatedMemory"
        # value
        # Clear the value for any fields within the region:
        for k, v in region.fields.items():
            if v in self.value_for_region:
                del self.value_for_region[v]
        # Set the default value for the whole region to be "DeallocatedMemory"
        self.region_for_var[region] = region
        self.value_for_region[region] = DeallocatedMemory(None, stmt.loc)

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
                               gcc.GimplePredict, gcc.GimpleNop)):
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
        elif isinstance(stmt, gcc.GimpleAsm):
            return self._get_transitions_for_GimpleAsm(stmt)
        else:
            raise NotImplementedError("Don't know how to cope with %r (%s) at %s"
                                      % (stmt, stmt, stmt.loc))

    def mkstate_nop(self, stmt):
        """
        Clone this state (at a function call), updating the location, for
        functions with "void" return type
        """
        newstate = self.copy()
        newstate.loc = self.loc.next_loc()
        return newstate

    def mkstate_return_of(self, stmt, v_return):
        """
        Clone this state (at a function call), updating the location, and
        setting the result of the call to the given AbstractValue
        """
        check_isinstance(v_return, AbstractValue)
        newstate = self.copy()
        newstate.loc = self.loc.next_loc()
        if stmt.lhs:
            newstate.assign(stmt.lhs,
                            v_return,
                            stmt.loc)
        return newstate

    def mkstate_concrete_return_of(self, stmt, value):
        """
        Clone this state (at a function call), updating the location, and
        setting the result of the call to the given concrete value
        """
        check_isinstance(value, numeric_types)
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


    def mktrans_not_returning(self, desc):
        # The function being called does not return e.g. "exit(0);"
        # Transition to a special noreturn state:
        s_new = self.copy()
        s_new.not_returning = True
        return Transition(self, s_new, desc)

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

    def make_transitions_for_fncall(self, stmt, fnmeta, s_success, s_failure):
        """
        Given a function call, convert a pair of State instances into a pair
        of Transition instances, marking one as a successful call, the other
        as a failed call.
        """
        check_isinstance(stmt, gcc.GimpleCall)
        if fnmeta:
            check_isinstance(fnmeta, FnMeta)
        check_isinstance(s_success, State)
        check_isinstance(s_failure, State)

        if fnmeta:
            return [Transition(self, s_success, fnmeta.desc_when_call_succeeds()),
                    Transition(self, s_failure, fnmeta.desc_when_call_fails())]
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
            return [self.mktrans_not_returning('not returning from %s'
                                               % stmt.fn)]

        if isinstance(stmt.fn, (gcc.VarDecl, gcc.ParmDecl, gcc.SsaName)):
            # Calling through a function pointer:
            val = self.eval_rvalue(stmt.fn, stmt.loc)
            log('val: %s',  val)
            check_isinstance(val, AbstractValue)
            return val.get_transitions_for_function_call(self, stmt)

        # Evaluate the arguments:
        args = self.eval_stmt_args(stmt)

        # Check for uninitialized and deallocated data:
        for i, arg in enumerate(args):
            if isinstance(arg, UninitializedData):
                raise UsageOfUninitializedData(self, stmt.args[i],
                                               arg,
                                               'passing uninitialized data (%s) as argument %i to function' % (stmt.args[i], i + 1))
            if isinstance(arg, PointerToRegion):
                rvalue = self.value_for_region.get(arg.region, None)
                if isinstance(rvalue, DeallocatedMemory):
                    raise PassingPointerToDeallocatedMemory(i, 'function', stmt, rvalue)

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
            from libcpychecker.refcounts import type_is_pyobjptr_subclass
            if type_is_pyobjptr_subclass(stmt.fn.operand.type.type):
                log('Invocation of unknown function returning PyObject * (or subclass): %r' % fnname)

                fnmeta = FnMeta(name=fnname)

                # Assume that all such functions either:
                #   - return a new reference, or
                #   - return NULL and set an exception (e.g. MemoryError)
                from libcpychecker.attributes import fnnames_returning_borrowed_refs
                if fnname in fnnames_returning_borrowed_refs:
                    # The function being called was marked as returning a
                    # borrowed ref, rather than a new ref:
                    return self.apply_fncall_side_effects(
                        self.cpython.make_transitions_for_borrowed_ref_or_fail(stmt,
                                                                               fnmeta),
                        stmt)
                return self.apply_fncall_side_effects(
                    self.cpython.make_transitions_for_new_ref_or_fail(stmt,
                                                                      fnmeta,
                                                                 'new ref from (unknown) %s' % fnname),
                    stmt)

            # GCC builtins:
            if fnname == '__builtin_expect':
                # http://gcc.gnu.org/onlinedocs/gcc/Other-Builtins.html
                # The return value of:
                #    __builtin_expect(long exp, long c)
                # is "exp" (the 0-th argument):
                return [self.mktrans_assignment(stmt.lhs, stmt.args[0], None)]

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
                        t_iter.dest.cpython.steal_reference(v_arg, stmt.loc)

        # cpython: handle functions that have been marked as setting the
        # exception state:
        from libcpychecker.attributes import fnnames_setting_exception
        if fnname in fnnames_setting_exception:
            for t_iter in transitions:
                # Mark the global exception state (with an arbitrary
                # error):
                t_iter.dest.cpython.set_exception('PyExc_MemoryError',
                                                  stmt.loc)

        # cpython: handle functions that have been marked as setting the
        # exception state when they return a negative value:
        from libcpychecker.attributes import fnnames_setting_exception_on_negative_result
        if fnname in fnnames_setting_exception_on_negative_result:

            def handle_negative_return(t_iter):
                check_isinstance(t_iter, Transition)
                check_isinstance(t_iter.src, State)
                check_isinstance(stmt, gcc.GimpleCall)
                if stmt.lhs:
                    v_returnval = t_iter.dest.eval_rvalue(stmt.lhs, stmt.loc)
                    # This could raise a SplitValue exception:
                    # the split value affects State instances that are already
                    # within the trace, whereas we're splitting on a new value
                    # that only exists within a new State.
                    # Hence we have to do this within
                    #  process_splittable_transitions
                    # so that we can split the new state:
                    eqzero = v_returnval.eval_comparison(
                        'lt',
                        ConcreteValue.from_int(0),
                        None)
                    if eqzero is True:
                        # Mark the global exception state (with an arbitrary
                        # error):
                        t_iter.dest.cpython.set_exception('PyExc_MemoryError',
                                                          stmt.loc)

            transitions = process_splittable_transitions(transitions,
                                                         handle_negative_return)

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

        # Detect usage of uninitialized data:
        if isinstance(lhs, UninitializedData):
            raise UsageOfUninitializedData(self, expr_lhs, lhs,
                                           'comparison against uninitialized data (%s)' % expr_lhs)
        if isinstance(rhs, UninitializedData):
            raise UsageOfUninitializedData(self, expr_rhs, rhs,
                                           'comparison against uninitialized data (%s)' % expr_rhs)

        if exprcode == gcc.EqExpr:
            result = lhs.eval_comparison('eq', rhs, expr_rhs)
            if result is not None:
                return result
        elif exprcode == gcc.NeExpr:
            result = lhs.eval_comparison('eq', rhs, expr_rhs)
            if result is not None:
                return not result
        elif exprcode == gcc.LtExpr:
            result = lhs.eval_comparison('lt', rhs, expr_rhs)
            if result is not None:
                return result
        elif exprcode == gcc.LeExpr:
            result = lhs.eval_comparison('le', rhs, expr_rhs)
            if result is not None:
                return result
        elif exprcode == gcc.GeExpr:
            result = lhs.eval_comparison('ge', rhs, expr_rhs)
            if result is not None:
                return result
        elif exprcode == gcc.GtExpr:
            result = lhs.eval_comparison('gt', rhs, expr_rhs)
            if result is not None:
                return result

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
                             gcc.RdivExpr,
                             gcc.MaxExpr, gcc.MinExpr,
                             gcc.BitIorExpr, gcc.BitAndExpr, gcc.BitXorExpr,
                             gcc.LshiftExpr, gcc.RshiftExpr,

                             gcc.TruthAndExpr, gcc.TruthOrExpr
                             ):
            a, b = self.eval_binop_args(stmt)
            if isinstance(a, UninitializedData):
                raise UsageOfUninitializedData(self, stmt.rhs[0], a,
                                               'usage of uninitialized data (%s) on left-hand side of %s'
                                               % (stmt.rhs[0], stmt.exprcode.get_symbol()))
            if isinstance(b, UninitializedData):
                raise UsageOfUninitializedData(self, stmt.rhs[1], b,
                                               'usage of uninitialized data (%s) on right-hand side of %s'
                                               % (stmt.rhs[0], stmt.exprcode.get_symbol()))
            try:
                c = a.eval_binop(stmt.exprcode, b, rhs[1], stmt.lhs.type, stmt.loc)
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
        elif stmt.exprcode == gcc.RealCst:
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
                               gcc.NegateExpr, gcc.FixTruncExpr, gcc.FloatExpr):
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

    def _get_transitions_for_GimpleAsm(self, stmt):
        log('stmt: %r %s', stmt, stmt)

        if stmt.string == '':
            # Empty fragment of inline assembler:
            s_next = self.copy()
            s_next.loc = self.loc.next_loc()
            return [Transition(self, s_next, None)]

        raise NotImplementedError('Unable to handle inline assembler: %s'
                                  % stmt.string)

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

        # A list of (src gcc.BasicBlock, dest gcc.BasicBlock) pairs
        # where the basic blocks are different
        self.paths_taken = []

    def add(self, transition):
        check_isinstance(transition, Transition)
        self.states.append(transition.dest)
        self.transitions.append(transition)
        if transition.src.loc.bb != transition.dest.loc.bb:
            self.paths_taken.append( (transition.src.loc.bb,
                                      transition.dest.loc.bb) )
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
        src_bb = endtransition.src.loc.bb
        dest_bb = endtransition.dest.loc.bb
        if src_bb != dest_bb:
            if (src_bb, dest_bb) in self.paths_taken[0:-1]:
                return True

    def get_all_var_region_pairs(self):
        """
        Get the set of all (LHS,region) pairs in region_for_var within all of
        the states in this trace, without duplicates
        """
        result = set()
        for s_iter in self.states:
            for var_iter, r_iter in s_iter.region_for_var.items():
                pair = (var_iter, r_iter)
                result.add(pair)
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


def process_splittable_transitions(transitions, callback):
    """
    Apply a processing function to each Transition in transitions,
    handling the case where a SplitValue exception is raised by
    splitting the destination states.

    Return a new list of Transition instances: which will be the
    old Transition objects, potentially with additional Transition
    instances if any have been split
    """
    newtransitions = []
    for t_iter in transitions:
        try:
            callback(t_iter)
            newtransitions.append(t_iter)
        except SplitValue:
            err = sys.exc_info()[1]
            splittransitions = err.split(t_iter.dest)
            check_isinstance(splittransitions, list)
            # Recurse:
            newtransitions += process_splittable_transitions(splittransitions,
                                                             callback)
    return newtransitions

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

    We have a list of Trace instances, each of which is "complete" in the sense
    that it fully captures one path through the function.  However, we know
    that the list itself is incomplete: it's not the full list of all
    possible traces.
    """
    def __init__(self, complete_traces):
        check_isinstance(complete_traces, list)
        self.complete_traces = complete_traces

class Limits:
    """
    Resource limits, to avoid an analysis going out of control
    """
    def __init__(self, maxtrans):
        self.maxtrans = maxtrans
        self.trans_seen = 0

    def on_transition(self, transition, result):
        """
        result is a list of all *complete* traces so far
        """
        self.trans_seen += 1
        if self.trans_seen > self.maxtrans:
            raise TooComplicated(result)

def iter_traces(fun, facets, prefix=None, limits=None, depth=0):
    """
    Traverse the tree of traces of program state, returning a list
    of Trace instances.

    For now, don't include any traces that contain loops, as a primitive
    way of ensuring termination of the analysis

    This is recursive, setting up a depth-first traversal of the state tree.
    If it's interrupted by a TooComplicated exception, we should at least
    capture an incomplete list of paths down to some of the bottoms of the
    tree.
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

            # Potentially raise a TooComplicated exception:
            if limits:
                limits.on_transition(transition, result)

            newprefix = prefix.copy().add(transition)

            # Recurse
            # This gives us a depth-first traversal of the state tree
            try:
                for trace in iter_traces(fun, facets, newprefix, limits,
                                         depth + 1):
                    result.append(trace)
            except TooComplicated:
                err = sys.exc_info()[1]
                traces = err.complete_traces
                traces += result
                raise TooComplicated(traces)
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

