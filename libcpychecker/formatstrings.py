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

import sys

from gccutils import get_src_for_loc, get_global_typedef

from libcpychecker.types import *
from libcpychecker.utils import log

const_correctness = True

def get_const_char_ptr():
    return gcc.Type.char().const_equivalent.pointer

def get_const_char_ptr_ptr():
    if const_correctness:
        return gcc.Type.char().const_equivalent.pointer.pointer
    else:
        # Allow people to be sloppy about const-correctness here:
        return (gcc.Type.char().const_equivalent.pointer.pointer,
                gcc.Type.char().pointer.pointer)

def get_hash_size_type(with_size_t):
    # Was PY_SSIZE_T_CLEAN defined?
    if with_size_t:
        return get_Py_ssize_t()
    else:
        return gcc.Type.int()

class NullPointer:
    # Dummy value, for pointer arguments that can legitimately be NULL
    def describe(self):
        return 'NULL'

class CExtensionError(Exception):
    # Base class for errors discovered by static analysis in C extension code
    pass

class FormatStringError(CExtensionError):
    def __init__(self, fmt_string):
        self.fmt_string = fmt_string

class UnknownFormatChar(FormatStringError):
    def __init__(self, fmt_string, ch):
        FormatStringError.__init__(self, fmt_string)
        self.ch = ch

    def __str__(self):
        return "unknown format char in \"%s\": '%s'" % (self.fmt_string, self.ch)

class UnhandledCode(UnknownFormatChar):
    def __str__(self):
        return "unhandled format code in \"%s\": '%s' (FIXME)" % (self.fmt_string, self.ch)


class MismatchedParentheses(FormatStringError):
    def __str__(self):
        return "mismatched parentheses in format string \"%s\"" % (self.fmt_string, )

class ParsedFormatStringError(FormatStringError):
    def __init__(self, funcname, fmt):
        FormatStringError.__init__(self, fmt.fmt_string)
        self.funcname = funcname
        self.fmt = fmt

class FormatUnit:
    """
    One fragment of the string arg to PyArg_ParseTuple and friends
    """
    def __init__(self, code):
        self.code = code

    def get_expected_types(self):
        # Return a list of the types expected for this format unit,
        # either as gcc.Type instances, or as instances of AwkwardType
        raise NotImplementedError

class ConcreteUnit(FormatUnit):
    """
    The common case: a fragment of a format string that corresponds to a
    pre-determined list of types (often just a single element)
    """
    def __init__(self, code, expected_types):
        FormatUnit.__init__(self, code)
        self.expected_types = expected_types

    def get_expected_types(self):
        return self.expected_types

    def __repr__(self):
        return 'ConcreteUnit(%r,%r)' % (self.code, self.expected_types)

class AwkwardType:
    """
    Base class for expected types within a format unit that need special
    handling (e.g. for "O!" and "O&")
    """
    def is_compatible(self, actual_type, actual_arg):
        raise NotImplementedError

    def describe(self):
        raise NotImplementedError

class ParsedFormatString:
    """
    Python class representing the result of parsing a format string
    """
    def __init__(self, fmt_string):
        self.fmt_string = fmt_string
        self.args = []

    def __repr__(self):
        return ('%s(fmt_string=%r, args=%r)'
                % (self.__class__.__name__, self.fmt_string, self.args))

class WrongNumberOfVars(ParsedFormatStringError):
    def __init__(self, funcname, fmt, varargs):
        ParsedFormatStringError.__init__(self, funcname, fmt)
        self.varargs = varargs

    def __str__(self):
        result = ('%s in call to %s with format string "%s"\n'
                  '  expected %i extra arguments:\n'
                  % (self._get_desc_prefix(),
                     self.funcname,
                     self.fmt.fmt_string,
                     self.fmt.num_expected()))
        for (arg, exp_type) in self.fmt.iter_exp_types():
            result += '    %s\n' % describe_type(exp_type)
        if len(self.varargs) == 0:
            result += '  but got none\n'
        else:
            result += '  but got %i:\n' % len(self.varargs)
        for arg in self.varargs:
            result += '    %s\n' % describe_type(arg.type)
        return result

    def _get_desc_prefix(self):
        raise NotImplementedError

class NotEnoughVars(WrongNumberOfVars):
    def _get_desc_prefix(self):
        return 'Not enough arguments'

class TooManyVars(WrongNumberOfVars):
    def _get_desc_prefix(self):
        return 'Too many arguments'

class MismatchingType(ParsedFormatStringError):
    def __init__(self, funcname, fmt, arg_num, arg_fmt_string, exp_type, vararg):
        super(self.__class__, self).__init__(funcname, fmt)
        self.arg_num = arg_num
        self.arg_fmt_string = arg_fmt_string
        self.exp_type = exp_type
        self.vararg = vararg

    def extra_info(self):
        def _describe_vararg(va):
            result = '"%s"' % va.type
            if hasattr(va, 'operand'):
                result += describe_precision(va.operand.type)
            return result

        return ('  argument %i ("%s") had type\n'
                '    %s\n'
                '  but was expecting\n'
                '    %s\n'
                '  for format code "%s"\n'
                % (self.arg_num, self.vararg, describe_type(self.vararg.type),
                   describe_type(self.exp_type), self.arg_fmt_string))

    def __str__(self):
        return ('Mismatching type in call to %s with format code "%s"'
                % (self.funcname, self.fmt.fmt_string))

def describe_precision(t):
    if hasattr(t, 'precision'):
        return ' (pointing to %i bits)' % t.precision
    else:
        return ''

def describe_type(t):
    if isinstance(t, AwkwardType):
        return t.describe()
    if isinstance(t, NullPointer):
        return t.describe()
    if isinstance(t, tuple):
        result = 'one of ' + ' or '.join([describe_type(tp) for tp in t])
    else:
        # Special-case handling of function types, to avoid embedding the ID:
        #   c.f. void (*<T792>) (void)
        if isinstance(t, gcc.PointerType):
            if isinstance(t.dereference, gcc.FunctionType):
                signature = t.dereference
                return ('"%s (*fn) (%s)"' %
                        (signature.type,
                         ', '.join([str(argtype)
                                    for argtype in signature.argument_types])))
        result = '"%s"' % t
    if hasattr(t, 'dereference'):
        result += describe_precision(t.dereference)
    return result

def compatible_type(exp_type, actual_type, actualarg=None):
    log('comparing exp_type: %s (%r) with actual_type: %s (%r)', exp_type, exp_type, actual_type, actual_type)
    log('type(exp_type): %r %s', type(exp_type), type(exp_type))
    log('actualarg: %s (%r)', actualarg, actualarg)

    # Support exp_type being actually a tuple of expected types (we need this
    # for "S" and "U"):
    if isinstance(exp_type, tuple):
        for exp in exp_type:
            if compatible_type(exp, actual_type, actualarg):
                return True
        # Didn't match any of them:
        return False

    # Support the "O!" and "O&" converter codes:
    if isinstance(exp_type, AwkwardType):
        return exp_type.is_compatible(actual_type, actualarg)

    # Support the codes that can accept NULL:
    if isinstance(exp_type, NullPointer):
        if isinstance(actual_type, gcc.PointerType):
            if isinstance(actual_type.dereference, gcc.VoidType):
                # We have a (void*), double-check that it's actually NULL:
                if actualarg:
                    if isinstance(actualarg, gcc.IntegerCst):
                        if actualarg.constant == 0:
                            # We have NULL:
                            return True
        return False

    assert isinstance(exp_type, gcc.Type) or isinstance(exp_type, gcc.TypeDecl)
    assert isinstance(actual_type, gcc.Type) or isinstance(actual_type, gcc.TypeDecl)

    # Try direct comparison:
    if actual_type == exp_type:
        return True

    # Sometimes we get the typedef rather than the type, for both exp and
    # actual.  Compare using the actual types, but report using the typedefs
    # so that we can report that e.g.
    #   PyObject * *
    # was expected, rather than:
    #   struct PyObject * *
    if isinstance(exp_type, gcc.TypeDecl):
        if compatible_type(exp_type.type, actual_type):
            return True

    if isinstance(actual_type, gcc.TypeDecl):
        if compatible_type(exp_type, actual_type.type):
            return True

    # Dereference for pointers (and ptrs to ptrs etc):
    if isinstance(actual_type, gcc.PointerType) and isinstance(exp_type, gcc.PointerType):
        if compatible_type(actual_type.dereference, exp_type.dereference):
            return True

    # Don't be too fussy about typedefs to integer types
    # For instance:
    #   typedef unsigned PY_LONG_LONG gdb_py_ulongest;
    # gives a different IntegerType instance to that of
    #   gcc.Type.long_long().unsigned_equivalent
    # As long as the size, signedness etc are the same, let it go
    if isinstance(actual_type, gcc.IntegerType) and isinstance(exp_type, gcc.IntegerType):
        def compare_int_types():
            for attr in ('precision', 'unsigned',
                         'const', 'volatile', 'restrict'):
                if getattr(actual_type, attr) != getattr(exp_type, attr):
                    return False
            return True
        if compare_int_types():
            return True

    return False

def check_pyargs(fun):
    from libcpychecker.PyArg_ParseTuple import PyArgParseFmt
    from libcpychecker.Py_BuildValue import PyBuildValueFmt

    def get_format_string(stmt, format_idx):
        fmt_code = stmt.args[format_idx]
        # We can only cope with the easy case, when it's a AddrExpr(StringCst())
        # i.e. a reference to a string constant, i.e. a string literal in the C
        # source:
        if isinstance(fmt_code, gcc.AddrExpr):
            operand = fmt_code.operand
            if isinstance(operand, gcc.StringCst):
                return operand.constant

    def check_keyword_array(stmt, idx):
        keywords = stmt.args[idx]
        if isinstance(keywords, gcc.AddrExpr):
            operand = keywords.operand
            if isinstance(operand, gcc.VarDecl):
                # Caveat: "initial" will only be set up on the VarDecl of a
                # global variable, or a "static" variable in function scope;
                # for other local variables we appear to need to track the
                # gimple statements to get the value at the callsite
                initial = operand.initial
                if isinstance(initial, gcc.Constructor):
                    elements = [None] * len(initial.elements)
                    for elt in initial.elements:
                        (num, contents) = elt
                        elt_idx = num.constant
                        if isinstance(contents, gcc.NopExpr):
                            contents = contents.operand
                        if isinstance(contents, gcc.AddrExpr):
                            contents = contents.operand
                            if isinstance(contents, gcc.StringCst):
                                elements[elt_idx] = contents.constant
                        elif isinstance(contents, gcc.IntegerCst):
                            elements[elt_idx] = contents.constant
                    if elements[-1] != 0:
                        gcc.permerror(stmt.loc, 'keywords to PyArg_ParseTupleAndKeywords are not NULL-terminated')
                    i = 0
                    for elt in elements[0:-1]:
                        if not elt:
                            gcc.permerror(stmt.loc, 'keyword argument %d missing in PyArg_ParseTupleAndKeywords call' % i)
                        i = i + 1

    def check_callsite(stmt, parser, funcname, format_idx, varargs_idx, with_size_t):
        log('got call at %s', stmt.loc)
        log(get_src_for_loc(stmt.loc))
        # log('stmt: %r %s', (stmt, stmt))
        # log('args: %r', stmt.args)
        # for arg in stmt.args:
        #    # log('  arg: %s %r', (arg, arg))
            

        # We expect the following args:
        #   args[0]: PyObject *input_tuple
        #   args[1]: char * format
        #   args[2...]: output pointers

        if len(stmt.args) > 1:
            fmt_string = get_format_string(stmt, format_idx)
            if fmt_string:
                log('fmt_string: %r', fmt_string)

                loc = stmt.loc

                # Figure out expected types, based on the format string...
                try:
                    fmt = parser.from_string(fmt_string, with_size_t)
                except FormatStringError:
                    exc = sys.exc_info()[1]
                    gcc.permerror(stmt.loc, str(exc))
                    return
                log('fmt: %r', fmt.args)

                exp_types = list(fmt.iter_exp_types())
                log('exp_types: %r', exp_types)

                # ...then compare them against the actual types:
                varargs = stmt.args[varargs_idx:]
                # log('varargs: %r', varargs)
                if len(varargs) < len(exp_types):
                    gcc.permerror(loc, str(NotEnoughVars(funcname, fmt, varargs)))
                    return

                if len(varargs) > len(exp_types):
                    gcc.permerror(loc, str(TooManyVars(funcname, fmt, varargs)))
                    return

                for index, ((exp_arg, exp_type), vararg) in enumerate(zip(exp_types, varargs)):
                    if not compatible_type(exp_type, vararg.type, actualarg=vararg):
                        err = MismatchingType(funcname, fmt,
                                              index + varargs_idx + 1,
                                              exp_arg.code, exp_type, vararg)
                        if hasattr(vararg, 'location'):
                            loc = vararg.location
                        else:
                            loc = stmt.loc
                        gcc.permerror(loc,
                                      str(err))
                        sys.stderr.write(err.extra_info())

    def maybe_check_callsite(stmt):
        if stmt.fndecl:
            # If "PY_SSIZE_T_CLEAN" is defined before #include <Python.h>, then
            # the preprocessor is actually turning these into "_SizeT"-suffixed
            # variants, which handle some format codes differently

            # FIXME: should we report the name as seen by the compiler?
            # It doesn't appear in the CPython API docs

            if stmt.fndecl.name == 'PyArg_ParseTuple':
                check_callsite(stmt,
                               PyArgParseFmt,
                               'PyArg_ParseTuple',
                               1, 2, False)
            elif stmt.fndecl.name == '_PyArg_ParseTuple_SizeT':
                check_callsite(stmt,
                               PyArgParseFmt,
                               'PyArg_ParseTuple',
                               1, 2, True)
            elif stmt.fndecl.name == 'PyArg_ParseTupleAndKeywords':
                check_keyword_array(stmt, 3)
                check_callsite(stmt,
                               PyArgParseFmt,
                               'PyArg_ParseTupleAndKeywords',
                               2, 4, False)
            elif stmt.fndecl.name == '_PyArg_ParseTupleAndKeywords_SizeT':
                check_keyword_array(stmt, 3)
                check_callsite(stmt,
                               PyArgParseFmt,
                               'PyArg_ParseTupleAndKeywords',
                               2, 4, True)

    if fun.cfg:
        for bb in fun.cfg.basic_blocks:
            if isinstance(bb.gimple, list):
                for stmt in bb.gimple:
                    if stmt.loc:
                        gcc.set_location(stmt.loc)
                    if isinstance(stmt, gcc.GimpleCall):
                        maybe_check_callsite(stmt)
