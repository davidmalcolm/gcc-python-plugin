import os
import shutil
import tempfile
import unittest

from subprocess import Popen, PIPE

from cpybuilder import *


# FIXME: this will need tweaking:
pyruntimes = [PyRuntime('/usr/bin/python2.7', '/usr/bin/python2.7-config'),
              PyRuntime('/usr/bin/python2.7-debug', '/usr/bin/python2.7-debug-config'),
              PyRuntime('/usr/bin/python3.2mu', '/usr/bin/python3.2mu-config'),
              #PyRuntime('/usr/bin/python3.2dmu', '/usr/bin/python3.2dmu-config')
              ]

class SimpleTest(unittest.TestCase):
    def test_compilation(self):
        # Verify that the module builds and runs against multiple Python runtimes

        sm = SimpleModule()

        sm.cu.add_decl("""
static PyObject *
example_hello(PyObject *self, PyObject *args);
""")

        sm.cu.add_defn("""
static PyObject *
example_hello(PyObject *self, PyObject *args)
{
    return Py_BuildValue("s", "Hello world!");
}
""")

        methods = PyMethodTable('example_methods',
                                [PyMethodDef('hello', 'example_hello',
                                             METH_VARARGS, 'Return a greeting.')])
        sm.cu.add_defn(methods.c_defn())

        sm.add_module_init('example', modmethods=methods, moddoc='This is a doc string')
        #print sm.cu.as_str()

        for runtime in pyruntimes:
            self.build_module(runtime, sm)
            #print(repr(runtime.get_build_flags()))

    def build_module(self, runtime, sm):

        tmpdir = tempfile.mkdtemp()

        srcfile = os.path.join(tmpdir, 'example.c')
        modfile = os.path.join(tmpdir, runtime.get_module_filename('example'))

        f = open(srcfile, 'w')
        f.write(sm.cu.as_str())
        f.close()
        
        cflags = runtime.get_build_flags()
        args = ['gcc']
        args += ['-o', modfile]
        args += cflags.split()
        args += ['-Wall',  '-Werror'] # during testing
        args += ['-shared'] # not sure why this is necessary
        args += [srcfile]
        #print args

        # Invoke the compiler:
        p = Popen(args, stdin = PIPE)
        p.communicate(sm.cu.as_str())
        c = p.wait()
        assert c == 0

        self.assert_(os.path.exists(modfile))

        # Now verify that it built:
        out = runtime.run_command('import sys; sys.path.append("%s"); import example; print(example.hello())' % tmpdir)
        self.assertEqual(out, "Hello world!\n")
        
        # Cleanup successful test runs:
        shutil.rmtree(tmpdir)
        
        



if __name__ == '__main__':
    unittest.main()
