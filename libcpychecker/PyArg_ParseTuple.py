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

# Domain-specific warning:
#  Detecting errors in usage of the PyArg_ParseTuple API
#  
#  See http://docs.python.org/c-api/arg.html

import gcc

import sys

def log(msg, indent=0):
    if 0:
        sys.stderr.write('%s%s\n' % ('  ' * indent, msg))

from gccutils import get_src_for_loc, get_global_typedef

def get_const_char_ptr():
   return gcc.Type.char().const_equivalent.pointer

def get_Py_ssize_t():
    return get_global_typedef('Py_ssize_t')

def get_hash_size_type():
    if True: # FIXME: is PY_SSIZE_T_CLEAN defined?
        return get_Py_ssize_t()
    else:
        return gcc.Type.int()

# Helper functions for looking up various CPython implementation types.
# Unfortunately, these are all typedefs, and I'm not able to get at these yet.
def get_Py_buffer():
    return get_global_typedef('Py_buffer')

def Py_UNICODE():
    return get_global_typedef('Py_UNICODE')

def get_PY_LONG_LONG():
    # pyport.h can supply PY_LONG_LONG as a #define, as a typedef, or not at all
    # FIXME
    # If we have "long long", pyport.h uses that.
    # Assume so for now:
    return gcc.Type.long_long()

def get_PyObject():
    return get_global_typedef('PyObject')

def get_PyTypeObject():
    return get_global_typedef('PyTypeObject')

def get_PyStringObject():
    return get_global_typedef('PyStringObject')

def get_PyUnicodeObject():
    return get_global_typedef('PyUnicodeObject')

def get_Py_complex():
    return get_global_typedef('Py_complex')

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

def _type_of_simple_arg(arg):
    # Convert 1-character argument code to a gcc.Type, covering the easy cases
    #
    # Analogous to Python/getargs.c:convertsimple, this is the same order as
    # that function's "switch" statement:
    simple = {'b': gcc.Type.unsigned_char,
              'B': gcc.Type.unsigned_char,
              'h': gcc.Type.short,
              'H': gcc.Type.unsigned_short,
              'i': gcc.Type.int,
              'I': gcc.Type.unsigned_int,
              'l': gcc.Type.long,
              'k': gcc.Type.unsigned_long,
              'f': gcc.Type.float,
              'd': gcc.Type.double,
              'c': gcc.Type.char,
              }
    if arg in simple:
        # FIXME: ideally this shouldn't need calling; it should just be an
        # attribute:
        return simple[arg]()

    if arg == 'n':
        return get_Py_ssize_t()

    if arg == 'L':
        return get_PY_LONG_LONG()

    if arg == 'K':
        return get_PY_LONG_LONG().unsigned_equivalent

    if arg == 'D':
        return get_Py_complex()

class FormatUnit:
    """
    One fragment of the string arg to PyArg_ParseTuple and friends
    """
    def __init__(self, code):
        self.code = code

class ConcreteUnit(FormatUnit):
    def __init__(self, code, expected_types):
        FormatUnit.__init__(self, code)
        self.expected_types = expected_types

class Converter(FormatUnit):
    def __init__(self, code):
        FormatUnit.__init__(self, code) # FIXME: how to handle this?

class PyArgParseFmt:
    """
    Python class representing the string arg to PyArg_ParseTuple and friends
    """
    def __init__(self, fmt_string):
        self.fmt_string = fmt_string
        self.args = []

    def add_argument(self, code, expected_types):
        self.args.append(ConcreteUnit(code, expected_types))

    def num_expected(self):
        return len(list(self.iter_exp_types()))

    def iter_exp_types(self):
        """
        Yield a sequence of (FormatUnit, gcc.Type) pairs, representing
        the expected types of the varargs
        """
        for arg in self.args:
            for exp_type in arg.expected_types:
                yield (arg, exp_type)

    @classmethod
    def from_string(cls, fmt_string):
        """
        Parse fmt_string, generating a PyArgParseFmt instance
        Compare to Python/getargs.c:vgetargs1
        FIXME: only implements a subset of the various cases; no tuples yet etc
        """
        result = PyArgParseFmt(fmt_string)
        i = 0
        paren_nesting = 0
        while i < len(fmt_string):
            c = fmt_string[i]
            i += 1
            if i < len(fmt_string):
                next = fmt_string[i]
            else:
                next = None

            if c == '(':
                paren_nesting += 1
                continue

            if c == ')':
                if paren_nesting > 0:
                    paren_nesting -= 1
                    continue
                else:
                    raise MismatchedParentheses(fmt_string)

            if c in [':', ';']:
                break

            if c =='|':
                continue

            simple_type = _type_of_simple_arg(c)
            if simple_type:
                result.add_argument(c, [simple_type.pointer])

            elif c in ['s', 'z']: # string, possibly NULL/None
                if next == '#':
                    result.add_argument('c#',
                                        [get_const_char_ptr().pointer,
                                         get_hash_size_type().pointer])
                    i += 1
                elif next == '*':
                    result.add_argument('c*', [get_Py_buffer().pointer])
                    i += 1
                else:
                    result.add_argument('c', [get_const_char_ptr().pointer])
                # FIXME: seeing lots of (const char**) versus (char**) mismatches here
                # do we care?

            elif c == 'e':
                if next in ['s', 't']:
                    arg = ConcreteUnit('e' + next,
                                       [get_const_char_ptr(),
                                        gcc.Type.char().pointer.pointer])
                    i += 1
                    if i < len(fmt_string):
                        if fmt_string[i] == '#':
                            arg.code += '#'
                            arg.expected_types.append(gcc.Type.int().pointer)
                            i+=1
                    result.args.append(arg)
            elif c == 'u':
                if next == '#':
                    result.add_argument('u#',
                                        [Py_UNICODE().pointer.pointer,
                                         get_hash_size_type().pointer])
                    i += 1
                else:
                    result.add_argument('u', [Py_UNICODE().pointer.pointer])
            elif c == 'S':
                result.add_argument('S', [get_PyStringObject().pointer.pointer])
            elif c == 'U':
                result.add_argument('U', [get_PyUnicodeObject().pointer.pointer])
            elif c == 'O': # object
                if next == '!':
                    result.add_argument('O!',
                                        [get_PyTypeObject().pointer,
                                         get_PyObject().pointer.pointer])
                    i += 1
                elif next == '?':
                    raise UnhandledCode(richloc, fmt_string, c + next) # FIXME
                elif next == '&':
                    # FIXME: can't really handle this case as is, fixing for fcntmodule.c
                    result.args.append(Converter('O&'))
                    i += 1
                    #'O&',
                    #[gcc.Type.int().pointer, # FIXME: this is a converter
                    #
                    #                     # FIXME: this should be obtained from the
                    #                     # converter's type:
                    #                     gcc.Type.int().pointer])
                    #result += ['int ( PyObject * object , int * target )',  # converter
                    #           'int *'] # FIXME, anything
                else:
                    result.add_argument('O',
                                        [get_PyObject().pointer.pointer])
            elif c == 'w':
                if next == '#':
                    result.add_argument('w#',
                                        [gcc.Type.char().pointer.pointer,
                                         get_Py_ssize_t().pointer])
                    i += 1
                elif next == '*':
                    result.add_argument('w*', [get_Py_buffer().pointer])
                    i += 1
                else:
                    result.add_argument('w', [gcc.Type.char().pointer.pointer])
            elif c == 't':
                if next == '#':
                    result.add_argument('t#',
                                        [gcc.Type.char().pointer.pointer,
                                         get_hash_size_type().pointer])
                    # Note: reading CPython sources indicates it's a FETCH_SIZE
                    # type, not an int, as the docs current suggest
                    i += 1
            else:
                raise UnknownFormatChar(fmt_string, c)

        if paren_nesting > 0:
            raise MismatchedParentheses(fmt_string)

        return result

class ParsedFormatStringError(FormatStringError):
    def __init__(self, funcname, fmt):
        FormatStringError.__init__(self, fmt.fmt_string)
        self.funcname = funcname
        self.fmt = fmt

class WrongNumberOfVars(ParsedFormatStringError):
    def __init__(self, funcname, fmt, varargs):
        ParsedFormatStringError.__init__(self, funcname, fmt)
        self.varargs = varargs

    def __str__(self):
        return '%s in call to %s with format string "%s" : expected %i extra arguments (%s), but got %i' % (
            self._get_desc_prefix(),
            self.funcname,
            self.fmt.fmt_string,
            self.fmt.num_expected(),
            ','.join([str(exp_type) for (arg, exp_type) in self.fmt.iter_exp_types()]),
            len(self.varargs))

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
        def _describe_precision(t):
            if hasattr(t, 'precision'):
                return ' (pointing to %i bits)' % t.precision
            else:
                return ''

        def _describe_vararg(va):
            result = '"%s"' % va.type
            if hasattr(va, 'operand'):
                result += _describe_precision(va.operand.type)
            return result

        def _describe_exp_type(t):
            result = '"%s"' % t
            if hasattr(t, 'dereference'):
                result += _describe_precision(t.dereference)
            return result
            
        return ('  argument %i ("%s") had type %s\n'
                '  but was expecting %s for format code "%s"\n'
                % (self.arg_num, self.vararg, _describe_vararg(self.vararg),
                   _describe_exp_type(self.exp_type), self.arg_fmt_string))

    def __str__(self):
        return ('Mismatching type in call to %s with format code "%s"'
                % (self.funcname, self.fmt.fmt_string))

def type_equality(exp_type, actual_type):
    log('comparing exp_type: %s (%r) with actual_type: %s (%r)' % (exp_type, exp_type, actual_type, actual_type))
    log('type(exp_type): %r %s' % (type(exp_type), type(exp_type)))

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
        if type_equality(exp_type.type, actual_type):
            return True

    if isinstance(actual_type, gcc.TypeDecl):
        if type_equality(exp_type, actual_type.type):
            return True

    # Dereference for pointers (and ptrs to ptrs etc):
    if isinstance(actual_type, gcc.PointerType) and isinstance(exp_type, gcc.PointerType):
        if type_equality(actual_type.dereference, exp_type.dereference):
            return True

    return False

def check_pyargs(fun):
    def get_format_string(stmt, format_idx):
        fmt_code = stmt.args[format_idx]
        # We can only cope with the easy case, when it's a AddrExpr(StringCst())
        # i.e. a reference to a string constant, i.e. a string literal in the C
        # source:
        if isinstance(fmt_code, gcc.AddrExpr):
            operand = fmt_code.operand
            if isinstance(operand, gcc.StringCst):
                return operand.constant

    def check_callsite(stmt, funcname, format_idx, varargs_idx):
        log('got call at %s' % stmt.loc)
        log(get_src_for_loc(stmt.loc))
        # log('stmt: %r %s' % (stmt, stmt))
        # log('args: %r' % stmt.args)
        # for arg in stmt.args:
        #    # log('  arg: %s %r' % (arg, arg))
            

        # We expect the following args:
        #   args[0]: PyObject *input_tuple
        #   args[1]: char * format
        #   args[2...]: output pointers

        if len(stmt.args) > 1:
            fmt_string = get_format_string(stmt, format_idx)
            if fmt_string:
                log('fmt_string: %r' % fmt_string)

                loc = stmt.loc

                # Figure out expected types, based on the format string...
                try:
                    fmt = PyArgParseFmt.from_string(fmt_string)
                except FormatStringError, exc:
                    gcc.permerror(stmt.loc, str(exc))
                    return
                log('fmt: %r' % fmt.args)

                exp_types = list(fmt.iter_exp_types())
                log('exp_types: %r' % exp_types)

                # ...then compare them against the actual types:
                varargs = stmt.args[varargs_idx:]
                # log('varargs: %r' % varargs)
                if len(varargs) < len(exp_types):
                    gcc.permerror(loc, str(NotEnoughVars(funcname, fmt, varargs)))
                    return

                if len(varargs) > len(exp_types):
                    gcc.permerror(loc, str(TooManyVars(funcname, fmt, varargs)))
                    return

                for index, ((exp_arg, exp_type), vararg) in enumerate(zip(exp_types, varargs)):
                    if not type_equality(exp_type, vararg.type):
                        err = MismatchingType(funcname, fmt,
                                              index + varargs_idx + 1,
                                              exp_arg.code, exp_type, vararg)
                        gcc.permerror(vararg.location,
                                      str(err))
                        sys.stderr.write(err.extra_info())
    
    if fun.cfg:
        for bb in fun.cfg.basic_blocks:
            if isinstance(bb.gimple, list):
                for stmt in bb.gimple:
                    if isinstance(stmt, gcc.GimpleCall):
                        from gccutils import pprint
                        if stmt.fndecl:
                            if stmt.fndecl.name == 'PyArg_ParseTuple':
                                check_callsite(stmt, 'PyArg_ParseTuple', 1, 2)
                            elif stmt.fndecl.name == 'PyArg_ParseTupleAndKeywords':
                                check_callsite(stmt, 'PyArg_ParseTupleAndKeywords', 2, 4)

