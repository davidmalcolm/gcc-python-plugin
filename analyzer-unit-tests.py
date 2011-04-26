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
    def assertFindsError(self, src, experr):
        sm = SimpleModule()
        sm.cu.add_decl(src)
        try:
            bm = BuiltModule(sm, pyruntime)
            bm.build(extra_cflags=['-fplugin=%s' % os.path.abspath('python.so'),
                                   '-fplugin-arg-python-script=cpychecker.py'])
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

if __name__ == '__main__':
    unittest.main()
