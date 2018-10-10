# -*- coding: utf-8 -*-
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

import os
from subprocess import Popen, PIPE
import sys
import unittest

import six

from testcpybuilder import BuiltModule, SimpleModule, CompilationError
from cpybuilder import PyMethodTable, PyMethodDef, METH_VARARGS

PLUGIN_NAME = os.environ.get('PLUGIN_NAME', 'python')

def get_gcc_version():
    p = Popen(['./print-gcc-version'],
              stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    return(int(out))

GCC_VERSION = get_gcc_version()

class ExpectedErrorNotFound(CompilationError):
    def __init__(self, expected_err, actual_err, bm):
        CompilationError.__init__(self, bm)
        self.expected_err = expected_err
        self.actual_err = actual_err


    def _describe_activity(self):
        result = 'This error was expected, but was not found:\n'
        result += '  ' + self._indent(self.expected_err) + '\n'
        result += '  whilst compiling:\n'
        result += '    ' + self.bm.srcfile + '\n'
        result += '  using:\n'
        result += '    ' + ' '.join(self.bm.args) + '\n'
        
        from difflib import unified_diff
        for line in unified_diff(self.expected_err.splitlines(),
                                 self.actual_err.splitlines(),
                                 fromfile='Expected stderr',
                                 tofile='Actual stderr',
                                 lineterm=""):
            result += '%s\n' % line
        return result

class AnalyzerTests(unittest.TestCase):
    def compile_src(self, bm):
        here = os.path.dirname(os.path.abspath(__file__))
        extra_cflags=['-fplugin=%s' % os.path.abspath('%s.so' % PLUGIN_NAME),
                      '-fplugin-arg-%s-script=%s/cpychecker.py' % (PLUGIN_NAME, here)]

        # GCC 4.8 started showing the source line where the problem is,
        # followed by another line showing a caret indicating column.
        # This is a great usability feature, but totally breaks our "gold"
        # output, so turn it off for running tests:
        if GCC_VERSION >= 4008:
            extra_cflags += ['-fno-diagnostics-show-caret']

        bm.compile_src(extra_cflags)

    def build_module(self, bm):
        bm.write_src('example')
        self.compile_src(bm)

    def assertNoErrors(self, src):
        if isinstance(src, SimpleModule):
            sm = src
        else:
            sm = SimpleModule()
            sm.cu.add_defn(src)
        bm = BuiltModule(sm)
        self.build_module(bm)
        bm.cleanup()
        return bm

    def assertFindsError(self, src, experr):
        if GCC_VERSION >= 4009:
            experr = experr.replace('$(SRCFILE):12:26:', '$(SRCFILE):12:10:')
            experr = experr.replace('$(SRCFILE):13:25:', '$(SRCFILE):13:9:')
            experr = experr.replace('$(SRCFILE):13:26:', '$(SRCFILE):13:10:')
            experr = experr.replace('$(SRCFILE):14:26:', '$(SRCFILE):14:10:')
            experr = experr.replace('$(SRCFILE):14:37:', '$(SRCFILE):14:10:')
            experr = experr.replace('$(SRCFILE):17:26:', '$(SRCFILE):17:10:')
        if GCC_VERSION >= 5000:
            experr = experr.replace('$(SRCFILE):12:5:', '$(SRCFILE):12:12:')
            experr = experr.replace('$(SRCFILE):13:5:', '$(SRCFILE):13:12:')
        if isinstance(src, SimpleModule):
            sm = src
        else:
            sm = SimpleModule()
            sm.cu.add_defn(src)
        bm = BuiltModule(sm)
        try:
            bm.write_src('example')
            experr = experr.replace('$(SRCFILE)', bm.srcfile)
            self.compile_src(bm)
        except CompilationError:
            exc = sys.exc_info()[1]
            if experr not in exc.err:
                raise ExpectedErrorNotFound(experr, exc.err, bm)
        else:
            raise ExpectedErrorNotFound(experr, bm.err, bm)
        bm.cleanup()
        return bm

class PyArg_ParseTupleTests(AnalyzerTests):
    def test_bogus_format_string(self):
        src = ('PyObject *\n'
               'bogus_format_string(PyObject *self, PyObject *args)\n'
               '{\n'
               '    if (!PyArg_ParseTuple(args, "This is not a valid format string")) {\n'
               '  	    return NULL;\n'
               '    }\n'
               '    Py_RETURN_NONE;\n'
               '}\n')
        experr = ("$(SRCFILE): In function 'bogus_format_string':\n"
                  '$(SRCFILE):12:26: error: unknown format char in "This is not a valid format string": \'T\' [-Werror]\n')
        self.assertFindsError(src, experr)
                   
    def test_finding_htons_error(self):
        #  Erroneous argument parsing of socket.htons() on 64bit big endian
        #  machines from CPython's Modules/socket.c; was fixed in svn r34931
        #  FIXME: the original had tab indentation, but what does this mean
        # for "column" offsets in the output?
        if six.MAXSIZE == 0x7fffffff:
            raise unittest.SkipTest('Test assumes a 64-bit machine')

        src = """
extern uint16_t htons(uint16_t hostshort);

PyObject *
socket_htons(PyObject *self, PyObject *args)
{
    unsigned long x1, x2;

    if (!PyArg_ParseTuple(args, "i:htons", &x1)) {
        return NULL;
    }
    x2 = (int)htons((short)x1);
#if PY_MAJOR_VERSION >= 3
    return PyLong_FromLong(x2);
#else
    return PyInt_FromLong(x2);
#endif
}
"""
        self.assertFindsError(src,
                              "$(SRCFILE): In function 'socket_htons':\n"
                              '$(SRCFILE):17:26: error: Mismatching type in call to PyArg_ParseTuple with format code "i:htons" [-Werror]\n'
                              '  argument 3 ("&x1") had type\n'
                              '    "long unsigned int *" (pointing to 64 bits)\n'
                              '  but was expecting\n'
                              '    "int *" (pointing to 32 bits)\n'
                              '  for format code "i"\n')

    def test_not_enough_varargs(self):
        src = """
PyObject *
not_enough_varargs(PyObject *self, PyObject *args)
{
   if (!PyArg_ParseTuple(args, "i")) {
       return NULL;
   }
   Py_RETURN_NONE;
}
"""
        self.assertFindsError(src,
                              "$(SRCFILE): In function 'not_enough_varargs':\n"
                              '$(SRCFILE):13:25: error: Not enough arguments in call to PyArg_ParseTuple with format string "i" [-Werror]\n'
                              '  expected 1 extra arguments:\n'
                              '    "int *" (pointing to 32 bits)\n'
                              '  but got none\n')

    def test_too_many_varargs(self):
        src = """
PyObject *
too_many_varargs(PyObject *self, PyObject *args)
{
    int i, j;
    if (!PyArg_ParseTuple(args, "i", &i, &j)) {
	 return NULL;
    }
    Py_RETURN_NONE;
}
"""
        self.assertFindsError(src,
                              "$(SRCFILE): In function 'too_many_varargs':\n"
                              '$(SRCFILE):14:26: error: Too many arguments in call to PyArg_ParseTuple with format string "i" [-Werror]\n'
                              '  expected 1 extra arguments:\n'
                              '    "int *" (pointing to 32 bits)\n'
                              '  but got 2:\n'
                              '    "int *" (pointing to 32 bits)\n'
                              '    "int *" (pointing to 32 bits)\n')

    def test_correct_usage(self):
        src = """
PyObject *
correct_usage(PyObject *self, PyObject *args)
{
    int i;
    if (!PyArg_ParseTuple(args, "i", &i)) {
	 return NULL;
    }
    Py_RETURN_NONE;
}
"""
        self.assertNoErrors(src)

    def get_function_name(self, header, code):
        name = '%s_%s' % (header, code)
        name = name.replace('*', '_star')
        name = name.replace('#', '_hash')
        name = name.replace('!', '_bang')
        name = name.replace('&', '_amp')
        return name

    def make_src_for_correct_function(self, code, typenames, params=None):
        # Generate a C function that uses the format code correctly, and verify
        # that it compiles with gcc with the cpychecker script, without errors
        function_name = self.get_function_name('correct_usage_of', code)
        src = ('PyObject *\n'
               '%(function_name)s(PyObject *self, PyObject *args)\n'
               '{\n') % locals()
        for i, typename in enumerate(typenames):
            src += ('    %(typename)s val%(i)s;\n') % locals()
        if not params:
            params = ', '.join('&val%i' % i for i in range(len(typenames)))
        src += ('    if (!PyArg_ParseTuple(args, "%(code)s", %(params)s)) {\n'
                '              return NULL;\n'
                '    }\n'
                '    Py_RETURN_NONE;\n'
                '}\n') % locals()
        return src

    def make_src_for_incorrect_function(self, code, typenames):
        function_name = self.get_function_name('incorrect_usage_of', code)
        params = ', '.join('&val' for i in range(len(typenames)))
        src = ('PyObject *\n'
               '%(function_name)s(PyObject *self, PyObject *args)\n'
               '{\n'
               '    void *val;\n'
               '    if (!PyArg_ParseTuple(args, "%(code)s", %(params)s)) {\n'
               '  	    return NULL;\n'
               '    }\n'
               '    Py_RETURN_NONE;\n'
               '}\n') % locals()
        return src, function_name

    def get_funcname(self):
        return 'PyArg_ParseTuple'

    def get_argindex(self):
        return 3

    def get_linenum(self):
        return 13

    def get_colnum(self):
        return 26

    def get_expected_error(self):
        return ("$(SRCFILE): In function '%(function_name)s':\n"
                '$(SRCFILE):%(linenum)i:%(colnum)i: error: Mismatching type in call to %(funcname)s with format code "%(code)s" [-Werror]\n'
                '  argument %(argindex)i ("&val") had type\n'
                '    "void * *"\n'
                '  but was expecting\n'
                '    %(exptypename)s')
        # we stop there, to avoid spelling out the various possible
        #    (pointing to N bits)
        # variants of the message

    def _test_format_code(self, code, typenames, exptypenames=None):
        if isinstance(typenames, str):
            typenames = [typenames]
        if isinstance(exptypenames, str):
            exptypenames = [exptypenames]
        if not exptypenames:
            exptypenames = ['"%s *"'%t for t in typenames]

        def _test_correct_usage_of_format_code(self, code, typenames):
            src = self.make_src_for_correct_function(code, typenames)
            self.assertNoErrors(src)

        def _test_incorrect_usage_of_format_code(self, code, typenames, exptypenames):
            # Generate a C function that uses the format code, with the
            # correct number of arguments, but all of the arguments being of
            # the incorrect type; compile it with cpychecker, and verify that there's
            # a warning
            exptypename = exptypenames[0]
            src, function_name = self.make_src_for_incorrect_function(code, typenames)
            funcname = self.get_funcname()
            argindex = self.get_argindex()
            linenum = self.get_linenum()
            colnum = self.get_colnum()
            experr = self.get_expected_error() % locals()
            bm = self.assertFindsError(src, experr)
                                       
        _test_correct_usage_of_format_code(self, code, typenames)
        _test_incorrect_usage_of_format_code(self, code, typenames, exptypenames)

    # The following test cases are intended to be in the same order as the API
    # documentation at http://docs.python.org/c-api/arg.html
        
    def test_format_code_s(self):
        self._test_format_code('s', 'const char *')

    # "s#" is affected by the PY_SSIZE_T_CLEAN macro; we test it within:
    #   tests/cpychecker/PyArg_ParseTuple/with_PY_SSIZE_T_CLEAN
    #   tests/cpychecker/PyArg_ParseTuple/without_PY_SSIZE_T_CLEAN

    def test_format_code_s_star(self):
        self._test_format_code('s*', ['Py_buffer'], '"struct Py_buffer *"')

    def test_format_code_z(self):
        self._test_format_code('z', 'const char *')

    # "z#" is affected by the PY_SSIZE_T_CLEAN macro; we test it within:
    #   tests/cpychecker/PyArg_ParseTuple/with_PY_SSIZE_T_CLEAN
    #   tests/cpychecker/PyArg_ParseTuple/without_PY_SSIZE_T_CLEAN

    def test_format_code_z_star(self):
        self._test_format_code('z*', ['Py_buffer'], '"struct Py_buffer *"')

    def test_format_code_u(self):
        self._test_format_code('u', 'Py_UNICODE *')

    # "u#" is affected by the PY_SSIZE_T_CLEAN macro; we test it within:
    #   tests/cpychecker/PyArg_ParseTuple/with_PY_SSIZE_T_CLEAN
    #   tests/cpychecker/PyArg_ParseTuple/without_PY_SSIZE_T_CLEAN

    def test_format_code_es(self):
        self._test_format_code('es',
          ['const char', 'char *'],
          [('one of "const char *" (pointing to 8 bits)'
            ' or "char *" (pointing to 8 bits) or NULL'),
           '"char * *"'])

    def test_format_code_et(self):
        self._test_format_code('et',
          ['const char', 'char *'],
          [('one of "const char *" (pointing to 8 bits)'
            ' or "char *" (pointing to 8 bits) or NULL'),
           '"char * *"'])

    # "es#" and "et#" are affected by the PY_SSIZE_T_CLEAN macro; we test them
    # within:
    #   tests/cpychecker/PyArg_ParseTuple/with_PY_SSIZE_T_CLEAN
    #   tests/cpychecker/PyArg_ParseTuple/without_PY_SSIZE_T_CLEAN

    def test_format_code_b(self):
        self._test_format_code('b', 'unsigned char')

    def test_format_code_B(self):
        self._test_format_code('B', 'unsigned char')

    def test_format_code_h(self):
        self._test_format_code('h', 'short',
                               '"short int *"')

    def test_format_code_H(self):
        self._test_format_code('H', 'unsigned short',
                               '"short unsigned int *"')

    def test_format_code_i(self):
        self._test_format_code('i', 'int')

    def test_format_code_I(self):
        self._test_format_code('I', 'unsigned int')

    def test_format_code_l(self):
        self._test_format_code('l', 'long',
                               '"long int *"')

    def test_format_code_k(self):
        self._test_format_code('k', 'unsigned long',
                               '"long unsigned int *"')

    def test_format_code_L(self):
        self._test_format_code('L', 'PY_LONG_LONG',
                               '"long long int *"')

    def test_format_code_K(self):
        self._test_format_code('K', 'unsigned PY_LONG_LONG',
                               '"long long unsigned int *"')

    def test_format_code_n(self):
        self._test_format_code('n', 'Py_ssize_t')

    def test_format_code_c(self):
        self._test_format_code('c', 'char')

    def test_format_code_f(self):
        self._test_format_code('f', 'float')

    def test_format_code_d(self):
        self._test_format_code('d', 'double')

    def test_format_code_D(self):
        self._test_format_code('D', 'Py_complex', '"struct Py_complex *"')

    def test_format_code_O(self):
        self._test_format_code('O', ['PyObject *'], '"struct PyObject * *"')

    # Code "O!" is tested by:
    #   tests/cpychecker/PyArg_ParseTuple/code_O_bang/

    # Code "O&" is tested by:
    #   tests/cpychecker/PyArg_ParseTuple/correct_converter/
    #   tests/cpychecker/PyArg_ParseTuple/incorrect_converters/

    # Codes "S" and "U" require some special treatment, as they can support
    # multiple types.  We tests them via these selftests:
    #	tests/cpychecker/PyArg_ParseTuple/correct_codes_S_and_U/
    #	tests/cpychecker/PyArg_ParseTuple/incorrect_codes_S_and_U/

    # "t#" is affected by the PY_SSIZE_T_CLEAN macro; we test it within:
    #   tests/cpychecker/PyArg_ParseTuple/with_PY_SSIZE_T_CLEAN
    #   tests/cpychecker/PyArg_ParseTuple/without_PY_SSIZE_T_CLEAN

    def test_format_code_w(self):
        self._test_format_code('w', 'char *')

    # "w#" is affected by the PY_SSIZE_T_CLEAN macro; we test it within:
    #   tests/cpychecker/PyArg_ParseTuple/with_PY_SSIZE_T_CLEAN
    #   tests/cpychecker/PyArg_ParseTuple/without_PY_SSIZE_T_CLEAN

    def test_format_code_w_star(self):
        self._test_format_code('w*', ['Py_buffer'], '"struct Py_buffer *"')

    def test_mismatched_parentheses(self):
        for code in ['(', ')', '(()']:
            function_name = 'fn'
            src = ('PyObject *\n'
                   '%(function_name)s(PyObject *self, PyObject *args)\n'
                   '{\n') % locals()
            src += ('    if (!PyArg_ParseTuple(args, "%(code)s")) {\n'
                    '              return NULL;\n'
                    '    }\n'
                    '    Py_RETURN_NONE;\n'
                    '}\n') % locals()
            experr = ("$(SRCFILE): In function '%(function_name)s':\n"
                      '$(SRCFILE):12:26: error: mismatched parentheses in format string "%(code)s"' % locals())
            bm = self.assertFindsError(src, experr)

class PyArg_ParseTupleAndKeywordsTests(PyArg_ParseTupleTests):
    def get_funcname(self):
        return 'PyArg_ParseTupleAndKeywords'

    def get_argindex(self):
        return 5

    def get_linenum(self):
        return 14

    def get_colnum(self):
        return 37

    def make_src_for_correct_function(self, code, typenames, params=None):
        # Generate a C function that uses the format code correctly, and verify
        # that it compiles with gcc with the cpychecker script, without errors
        function_name = self.get_function_name('correct_usage_of', code)
        src = ('PyObject *\n'
               '%(function_name)s(PyObject *self, PyObject *args, PyObject *kw)\n'
               '{\n') % locals()
        src += '    char *keywords[] = {"fake_keyword", NULL};\n'
        for i, typename in enumerate(typenames):
            src += ('    %(typename)s val%(i)s;\n') % locals()
        if not params:
            params = ', '.join('&val%i' % i for i in range(len(typenames)))
        src += ('    if (!PyArg_ParseTupleAndKeywords(args, kw, "%(code)s", keywords, %(params)s)) {\n'
                '              return NULL;\n'
                '    }\n'
                '    Py_RETURN_NONE;\n'
                '}\n') % locals()
        return src

    def make_src_for_incorrect_function(self, code, typenames):
        function_name = self.get_function_name('incorrect_usage_of', code)
        params = ', '.join('&val' for i in range(len(typenames)))
        src = ('PyObject *\n'
               '%(function_name)s(PyObject *self, PyObject *args, PyObject *kw)\n'
               '{\n'
               '    void *val;\n'
               '    char *keywords[] = {"fake_keyword", NULL};\n'
               '    if (!PyArg_ParseTupleAndKeywords(args, kw, "%(code)s", keywords, %(params)s)) {\n'
               '        return NULL;\n'
               '    }\n'
               '    Py_RETURN_NONE;\n'
               '}\n') % locals()
        return src, function_name

class Py_BuildValueTests(AnalyzerTests):
    def test_bogus_format_string(self):
        src = ('PyObject *\n'
               'bogus_format_string(PyObject *self, PyObject *args)\n'
               '{\n'
               '    return Py_BuildValue("this is not a valid format string");\n'
               '}\n')
        experr = ("$(SRCFILE): In function 'bogus_format_string':\n"
                  '$(SRCFILE):12:5: error: unknown format char in "this is not a valid format string": \'t\' [-Werror]\n')
        self.assertFindsError(src, experr)

    def test_not_enough_varargs(self):
        src = """
PyObject *
not_enough_varargs(PyObject *self, PyObject *args)
{
    return Py_BuildValue("i");
}
"""
        self.assertFindsError(src,
                              "$(SRCFILE): In function 'not_enough_varargs':\n"
                              '$(SRCFILE):13:5: error: Not enough arguments in call to Py_BuildValue with format string "i" [-Werror]\n'
                              '  expected 1 extra arguments:\n'
                              '    "int"\n'
                              '  but got none\n')

    def test_too_many_varargs(self):
        src = """
PyObject *
too_many_varargs(PyObject *self, PyObject *args)
{
    return Py_BuildValue("i", 0, 1);
}
"""
        self.assertFindsError(src,
                              "$(SRCFILE): In function 'too_many_varargs':\n"
                              '$(SRCFILE):13:5: error: Too many arguments in call to Py_BuildValue with format string "i" [-Werror]\n'
                              '  expected 1 extra arguments:\n'
                              '    "int"\n'
                              '  but got 2:\n'
                              '    "int"\n'
                              '    "int"\n')

    def test_correct_usage(self):
        src = """
PyObject *
correct_usage(PyObject *self, PyObject *args)
{
    return Py_BuildValue("ii", 0, 1);
}
"""
        self.assertNoErrors(src)



if __name__ == '__main__':
    unittest.main()
