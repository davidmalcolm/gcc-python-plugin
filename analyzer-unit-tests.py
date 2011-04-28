# -*- coding: utf-8 -*-
import os
import unittest
from subprocess import Popen, PIPE

from testcpybuilder import BuiltModule, PyRuntime, SimpleModule, CompilationError

#FIXME:
pyruntime = PyRuntime('/usr/bin/python2.7', '/usr/bin/python2.7-config')

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
        bm.compile_src(extra_cflags=['-fplugin=%s' % os.path.abspath('python.so'),
                                     '-fplugin-arg-python-script=cpychecker.py'])

    def build_module(self, bm):
        bm.write_src()
        self.compile_src(bm)

    def assertNoErrors(self, src):
        sm = SimpleModule()
        sm.cu.add_defn(src)
        bm = BuiltModule(sm, pyruntime)
        self.build_module(bm)
        bm.cleanup()

    def assertFindsError(self, src, experr):
        sm = SimpleModule()
        sm.cu.add_defn(src)
        bm = BuiltModule(sm, pyruntime)
        try:
            bm.write_src()
            experr = experr.replace('$(SRCFILE)', bm.srcfile)
            self.compile_src(bm)
        except CompilationError, exc:
            if experr not in exc.err:
                raise ExpectedErrorNotFound(experr, exc.err, bm)
        else:
            raise ExpectedErrorNotFound(experr, bm)
        bm.cleanup()
                   
    def test_simple(self):
        #  Erroneous argument parsing of socket.htons() on 64bit big endian
        #  machines from CPython's Modules/socket.c; was fixed in svn r34931
        #  FIXME: the original had tab indentation, but what does this mean
        # for "column" offsets in the output?
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
    return PyInt_FromLong(x2);
}
"""
        self.assertFindsError(src,
                              '$(SRCFILE): In function ‘socket_htons’:\n'
                              '$(SRCFILE):17:26: error: Mismatching type of argument 1 in "i:htons": expected "int *" but got "long unsigned int *\n'
                              '" [-fpermissive]\n')
        # the trailing whitespace/newline is a bug

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
                              '$(SRCFILE): In function ‘not_enough_varargs’:\n'
                              '$(SRCFILE):13:25: error: Not enough arguments in call to PyArg_ParseTuple with format string "i" : expected 1 extra arguments (int *), but got 0 [-fpermissive]\n')

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
                              '$(SRCFILE): In function ‘too_many_varargs’:\n'
                              '$(SRCFILE):14:26: error: Too many arguments in call to PyArg_ParseTuple with format string "i" : expected 1 extra arguments (int *), but got 2 [-fpermissive]\n')

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

from cpychecker import get_types

class TestArgParsing(unittest.TestCase):
    def assert_args(self, arg_str, exp_result):
        result = get_types(None, arg_str)
        self.assertEquals(result, exp_result)

    def test_simple_cases(self):
        self.assert_args('c',
                         ['char *'])

    def test_socketmodule_socket_htons(self):
        self.assert_args('i:htons',
                         ['int *'])

    def test_fcntlmodule_fcntl_flock(self):
        # FIXME: somewhat broken, we can't know what the converter callback is
        self.assert_args("O&i:flock", 
                         ['int ( PyObject * object , int * target )', 
                          'int *', 
                          'int *'])

    def test_posixmodule_listdir(self):
        self.assert_args("et#:listdir",
                         ['const char *', 'char * *', 'int *'])

    def test_bsddb_DBSequence_set_range(self):
        self.assert_args("(LL):set_range",
                         ['PY_LONG_LONG *', 'PY_LONG_LONG *'])


if __name__ == '__main__':
    unittest.main()
