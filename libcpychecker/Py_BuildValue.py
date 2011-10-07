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
#  Detecting errors in usage of the Py_BuildValue API
#  
#  See http://docs.python.org/c-api/arg.html#Py_BuildValue
#
# FIXME:
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
import sys

from libcpychecker.formatstrings import *
from libcpychecker.types import *
from libcpychecker.utils import log

def _type_of_simple_arg(arg):
    # Convert 1-character argument code to a gcc.Type, covering the easy cases
    #
    # Analogous to Python/modsupport.c:do_mkvalue, this is the same order as
    # that function's "switch" statement:
    simple = {
        # all of these actually just use "int":
        'b': gcc.Type.char,
        'B': gcc.Type.unsigned_char,
        'h': gcc.Type.short,
        'i': gcc.Type.int,
        'H': gcc.Type.unsigned_short,
        'I': gcc.Type.unsigned_int,
        # 'n' covered below
        'l': gcc.Type.long,
        'k': gcc.Type.unsigned_long,
        # 'L' covered below
        # 'K' covered below
        }
    if arg in simple:
        # FIXME: ideally this shouldn't need calling; it should just be an
        # attribute:
        return simple[arg]()

    if arg == 'n':
        return get_Py_ssize_t()
    elif arg == 'L':
        return get_PY_LONG_LONG()
    elif arg == 'K':
        return get_PY_LONG_LONG().unsigned_equivalent

    """
        case 'u':
        {
            PyObject *v;
            Py_UNICODE *u = va_arg(*p_va, Py_UNICODE *);
            Py_ssize_t n;
            if (**p_format == '#') {
                ++*p_format;
                if (flags & FLAG_SIZE_T)
                    n = va_arg(*p_va, Py_ssize_t);
                else
                    n = va_arg(*p_va, int);
            }
            else
                n = -1;
            if (u == NULL) {
                v = Py_None;
                Py_INCREF(v);
            }
            else {
                if (n < 0)
                    n = _ustrlen(u);
                v = PyUnicode_FromUnicode(u, n);
            }
            return v;
        }
        """
    
    #case 'f':
    #case 'd':
    #case 'D':
    #case 'c':

class ObjectFormatUnit(FormatUnit):
    """
    Base class for Py_BuildValue format codes that expect a PyObject*
    """
    def get_expected_types(self):
        return [get_PyObject().pointer]

class CodeSO(ObjectFormatUnit):
    """
    Corresponds to Py_BuildValue format codes "S" and "O"
    """
    pass

class CodeN(ObjectFormatUnit):
    """
    Corresponds to Py_BuildValue format code "N"
    """
    pass


class CompoundFmt:
    def __init__(self, opench, closech):
        self.opench = opench
        self.closech = closech
        self.args = []

    def __repr__(self):
        return 'CompoundFmt(%r, %r, %r)' % (self.opench, self.args, self.closech)

    def append(self, item):
        self.args.append(item)

    def iter_exp_types(self):
        for arg in self.args:
            if isinstance(arg, CompoundFmt):
                for inner in arg.iter_exp_types():
                    yield inner
            else:
                for exp_type in arg.get_expected_types():
                    yield (arg, exp_type)
        
class PyBuildValueFmt(ParsedFormatString):
    def __init__(self, fmt_string):
        ParsedFormatString.__init__(self, fmt_string)
        self.arg_stack = [self.args]

    def num_expected(self):
        from pprint import pformat
        #sys.stderr.write('%s\n' % pformat(list(self.iter_exp_types())))
        return len(list(self.iter_exp_types()))

    def iter_exp_types(self):
        """
        Yield a sequence of (FormatUnit, gcc.Type) pairs, representing
        the expected types of the varargs
        """
        for arg in self.args:
            if isinstance(arg, CompoundFmt):
                for inner in arg.iter_exp_types():
                    yield inner
            else:
                for exp_type in arg.get_expected_types():
                    yield (arg, exp_type)

    def add_argument(self, code, expected_types):
        self.arg_stack[-1].append(ConcreteUnit(code, expected_types))

    def add_complex_argument(self, arg):
        self.arg_stack[-1].append(arg)

    def _do_open_compound_fmt(self, opench, closech):
        """
        Analogous to Python/modsupport.c:do_mktuple
        """
        # Store tuples using lists, so that they are mutable during
        # construction:
        new = CompoundFmt(opench, closech)
        self.arg_stack[-1].append(new)
        self.arg_stack.append(new)

    def _do_close_compound_fmt(self, closech):
        if len(self.arg_stack) < 1:
            raise MismatchedParentheses(self.fmt_string)
        cf = self.arg_stack.pop()
        if cf.closech != closech:
            raise MismatchedParentheses(self.fmt_string)

    @classmethod
    def from_string(cls, fmt_string, with_size_t):
        """
        Parse fmt_string, generating a PyBuildValue instance
        Compare to Python/modsupport.c:va_build_value
        FIXME: only implements a subset of the various cases
        """
        result = PyBuildValueFmt(fmt_string)
        i = 0
        while i < len(fmt_string):
            c = fmt_string[i]
            i += 1
            if i < len(fmt_string):
                next = fmt_string[i]
            else:
                next = None
            #sys.stderr.write('(%r, %r)\n' % (c, None))

            # Analogous to Python/modsupport.c:do_mkvalue, this is in the same
            # order as that function's "switch" statement:
            simple_type = _type_of_simple_arg(c)
            if simple_type:
                result.add_argument(c, [simple_type])
                continue
                
            if c == '(':
                result._do_open_compound_fmt('(', ')')
                continue
            if c == '[':
                result._do_open_compound_fmt('[', ']')
                continue
            if c == '{':
                result._do_open_compound_fmt('{', '}')
                continue

            if c in ')]}':
                result._do_close_compound_fmt(c)
                continue

            if c in 'sz':
                if next == '#':
                    result.add_argument(c + '#',
                                        [get_const_char_ptr_ptr(),
                                         get_hash_size_type(with_size_t).pointer])
                    i += 1
                else:
                    result.add_argument(c,
                                        [get_const_char_ptr_ptr()])
                continue

            if c in 'NSO':
                if next == '&':
                    result.add_complex_argument()
                    i += 1
                else:
                    if c == 'N':
                        result.add_complex_argument(CodeN(c))
                    else:
                        result.add_complex_argument(CodeSO(c))
                continue

            if c in ":, \t":
                continue

            raise UnknownFormatChar(fmt_string, c)

        if len(result.arg_stack) > 1:
            # Not all parentheses were closed:
            raise MismatchedParentheses(self.fmt_string)

        #print result
        #from pprint import pprint
        #pprint(result.args)
        
        return result
