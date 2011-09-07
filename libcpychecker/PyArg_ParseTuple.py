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
#
#  Note that all of the "#" codes are affected by the presence of the
#  macro PY_SSIZE_T_CLEAN. If the macro was defined before including Python.h,
#  the various lengths for these format codes are of C type "Py_ssize_t" rather
#  than "int".
#
#  This behavior was clarified in the Python 3 version of the C API
#  documentation[1], though the Python 2 version of the API docs leave which
#  codes are affected somewhat ambiguoues.
#
#  Nevertheless, the API _does_ work this way in Python 2: all format codes
#  with a "#" do work this way.
#
#  You can see the implementation of the API in CPython's Python/getargs.c
#
#  [1] The relevant commit to the CPython docs was:
#    http://hg.python.org/cpython/rev/5d4a5655575f/

import gcc

from libcpychecker.formatstrings import *
from libcpychecker.types import *
from libcpychecker.utils import log

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

class TypeCheck(FormatUnit):
    """
    Handler for the "O!" format code
    """
    def __init__(self, code):
        FormatUnit.__init__(self, code)
        self.checker = TypeCheckCheckerType(self)
        self.result = TypeCheckResultType(self)

        # The gcc.VarDecl for the PyTypeObject, if we know it (or None):
        self.typeobject = None

    def get_expected_types(self):
        # We will discover the actual types as we go, using "self" to bind
        # together the two arguments
        return [self.checker, self.result]

    def get_other_type(self):
        if not self.typeobject:
            return None
        return get_type_for_typeobject(self.typeobject)

class TypeCheckCheckerType(AwkwardType):
    def __init__(self, typecheck):
        self.typecheck = typecheck

    def is_compatible(self, actual_type, actual_arg):
        # We should be encountering a pointer to a PyTypeObject
        # The result type (next argument) should be either a PyObject* or
        # an pointer to the corresponding type.
        #
        # For example, "O!" with
        #     &PyCode_Type, &code,
        # then "code" should be either a PyObject* or a PyCodeObject*
        # (and &code gets the usual extra level of indirection)

        if str(actual_type) != 'struct PyTypeObject *':
            return False

        # OK, the type for this argument is good.
        # Try to record the actual type object, assuming it's a pointer to a
        # global:
        if not isinstance(actual_arg, gcc.AddrExpr):
            return True

        if not isinstance(actual_arg.operand, gcc.VarDecl):
            return True

        # OK, we have a ptr to a global; record it:
        self.typecheck.typeobject = actual_arg.operand

        return True

    def describe(self):
        return '"struct PyTypeObject *"'

class TypeCheckResultType(AwkwardType):
    def __init__(self, typecheck):
        self.typecheck = typecheck
        self.base_type = get_PyObject().pointer.pointer

    def is_compatible(self, actual_type, actual_arg):
        if not isinstance(actual_type, gcc.PointerType):
            return False

        # If something went wrong with figuring out the type, we can only check
        # against PyObject*:

        # (PyObject **) is good:
        if compatible_type(actual_type,
                           self.base_type):
            return True

        other_type = self.typecheck.get_other_type()
        if other_type:
            if compatible_type(actual_type,
                               other_type.pointer.pointer):
                return True

        return False

    def describe(self):
        other_type = self.typecheck.get_other_type()
        if other_type:
            return ('%s (based on PyTypeObject: %r) or %s'
                    % (describe_type(other_type.pointer),
                       self.typecheck.typeobject.name,
                       describe_type(self.base_type)))
        else:
            if self.typecheck.typeobject:
                return ('"%s" (unfamiliar with PyTypeObject: %r)'
                        % (describe_type(self.base_type),
                           self.typecheck.typeobject.name))
            else:
                return '"%s" (unable to determine relevant PyTypeObject)' % describe_type(self.base_type)


class Conversion(FormatUnit):
    """
    Handler for the "O&" format code
    """
    def __init__(self, code):
        FormatUnit.__init__(self, code)
        self.callback = ConverterCallbackType(self)
        self.result = ConverterResultType(self)

    def get_expected_types(self):
        # We will discover the actual types as we go, using "self" to bind
        # together the two arguments
        return [self.callback, self.result]

class ConverterCallbackType(AwkwardType):
    def __init__(self, conv):
        self.conv = conv
        self.actual_type = None

    def is_compatible(self, actual_type, actual_arg):
        # We should be encountering a function pointer of type:
        #   int (fn)(PyObject *, T*)
        # The result type (next argument) should be a T*
        if not isinstance(actual_type, gcc.PointerType):
            return False

        signature = actual_type.dereference
        if not isinstance(signature, gcc.FunctionType):
            return False

        # Check return type:
        if signature.type != gcc.Type.int():
            return False

        # Check argument types:
        if len(signature.argument_types) != 2:
            return False

        if not compatible_type(signature.argument_types[0],
                               get_PyObject().pointer):
            return False

        if not isinstance(signature.argument_types[1], gcc.PointerType):
            return False

        # Write back to the ConverterResultType with the second arg:
        log('2nd argument of converter should be of type %s', signature.argument_types[1])
        self.conv.result.type = signature.argument_types[1]
        self.actual_type = actual_type

        return True

    def describe(self):
        return '"int (converter)(PyObject *, T*)" for some type T'

class ConverterResultType(AwkwardType):
    def __init__(self, conv):
        self.conv = conv
        self.type = None

    def is_compatible(self, actual_type, actual_arg):
        if not isinstance(actual_type, gcc.PointerType):
            return False

        # If something went wrong with figuring out the type, we can't check
        # it:
        if self.type is None:
            return True

        return compatible_type(self.type, actual_type)

    def describe(self):
        if self.type:
            return ('%s (from second argument of %s)'
                    % (describe_type(self.type),
                       describe_type(self.conv.callback.actual_type)))
        else:
            return '"T*" for some type T'

class PyArgParseFmt(ParsedFormatString):
    """
    Python class representing the string arg to PyArg_ParseTuple and friends
    """

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
            for exp_type in arg.get_expected_types():
                yield (arg, exp_type)

    @classmethod
    def from_string(cls, fmt_string, with_size_t):
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
                    result.add_argument(c + '#',
                                        [get_const_char_ptr_ptr(),
                                         get_hash_size_type(with_size_t).pointer])
                    i += 1
                elif next == '*':
                    result.add_argument(c + '*', [get_Py_buffer().pointer])
                    i += 1
                else:
                    result.add_argument(c, [get_const_char_ptr_ptr()])

            elif c == 'e':
                if next in ['s', 't']:
                    arg = ConcreteUnit('e' + next,
                                       [(get_const_char_ptr(), NullPointer()),
                                        gcc.Type.char().pointer.pointer])
                    i += 1
                    if i < len(fmt_string):
                        if fmt_string[i] == '#':
                            arg.code += '#'
                            # es# and et# within getargs.c use FETCH_SIZE and
                            # STORE_SIZE and are thus affected by the size
                            # macro:
                            arg.expected_types.append(get_hash_size_type(with_size_t).pointer)
                            i+=1
                    result.args.append(arg)
            elif c == 'u':
                if next == '#':
                    result.add_argument('u#',
                                        [Py_UNICODE().pointer.pointer,
                                         get_hash_size_type(with_size_t).pointer])
                    i += 1
                else:
                    result.add_argument('u', [Py_UNICODE().pointer.pointer])
            elif c == 'S':
                if is_py3k():
                    # S (bytes) [PyBytesObject *] (or PyObject *)
                    result.add_argument('S', [(get_PyBytesObject().pointer.pointer,
                                               get_PyObject().pointer.pointer)])
                else:
                    # S (string) [PyStringObject *] (or PyObject *)
                    result.add_argument('S', [(get_PyStringObject().pointer.pointer,
                                               get_PyObject().pointer.pointer)])
            elif c == 'U':
                result.add_argument('U', [(get_PyUnicodeObject().pointer.pointer,
                                           get_PyObject().pointer.pointer)])
            elif c == 'O': # object
                if next == '!':
                    result.args.append(TypeCheck('O!'))
                    i += 1
                elif next == '?':
                    raise UnhandledCode(richloc, fmt_string, c + next) # FIXME
                elif next == '&':
                    result.args.append(Conversion('O&'))
                    i += 1
                else:
                    result.add_argument('O',
                                        [get_PyObject().pointer.pointer])
            elif c == 'w':
                if next == '#':
                    result.add_argument('w#',
                                        [gcc.Type.char().pointer.pointer,
                                         get_hash_size_type(with_size_t).pointer])
                    # Note: reading CPython sources indicates it's a FETCH_SIZE
                    # type, not an Py_ssize_t, as the docs current suggest
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
                                         get_hash_size_type(with_size_t).pointer])
                    # Note: reading CPython sources indicates it's a FETCH_SIZE
                    # type, not an int, as the docs current suggest
                    i += 1
            else:
                raise UnknownFormatChar(fmt_string, c)

        if paren_nesting > 0:
            raise MismatchedParentheses(fmt_string)

        return result
