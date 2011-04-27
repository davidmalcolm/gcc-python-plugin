import os
import unittest
from subprocess import Popen, PIPE

from testcpybuilder import BuiltModule, PyRuntime, SimpleModule, CompilationError

#FIXME:
pyruntime = PyRuntime('/usr/bin/python2.7', '/usr/bin/python2.7-config')

class ExpectedErrorNotFound(CompilationError):
    def __init__(self, experr, bm):
        CompilationError.__init__(self, bm)
        self.experr = experr

    def _describe_activity(self):
        result = 'This error was expected, but was not found:\n'
        result += '  ' + self._indent(self.experr) + '\n'
        result += '  whilst compiling:\n'
        result += '    ' + self.bm.srcfile + '\n'
        result += '  using:\n'
        result += '    ' + ' '.join(self.bm.args)
        return result

class AnalyzerTests(unittest.TestCase):
    def build_module(self, bm):
        bm.build(extra_cflags=['-fplugin=%s' % os.path.abspath('python.so'),
                               '-fplugin-arg-python-script=cpychecker.py'])

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
            self.build_module(bm)
        except CompilationError, exc:
            if experr not in exc.err:
                raise ExpectedErrorNotFound(experr, bm)
        else:
            raise ExpectedErrorNotFound(experr, bm)
        bm.cleanup()
                   
    def test_simple(self):
        #  Erroneous argument parsing of socket.htons() on 64bit big endian
        #  machines from CPython's Modules/socket.c; was fixed in svn r34931
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
                              'buggy.c:13: Mismatching type of argument 1: expected "int *" for PyArg_ParseTuple format string "i" but got "unsigned long *"')

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
                              'example.c:13:foo:Not enough arguments in call to PyArg_ParseTuple with format string "i" : expected 1 extra arguments (int *), but got 0')

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
                              'example.c:14:foo:Too many arguments in call to PyArg_ParseTuple with format string "i" : expected 1 extra arguments (int *), but got 2')

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
