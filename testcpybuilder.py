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

class BuiltModule:
    """A test build of a SimpleModule for a PyRuntime, done in a tempdir"""
    def __init__(self, sm, runtime):
        self.sm = sm
        self.runtime = runtime

        self.tmpdir = tempfile.mkdtemp()

        self.srcfile = os.path.join(self.tmpdir, 'example.c')
        self.modfile = os.path.join(self.tmpdir, runtime.get_module_filename('example'))

        f = open(self.srcfile, 'w')
        f.write(sm.cu.as_str())
        f.close()
        
        cflags = runtime.get_build_flags()
        args = ['gcc']
        args += ['-o', self.modfile]
        args += cflags.split()
        args += ['-Wall',  '-Werror'] # during testing
        args += ['-shared'] # not sure why this is necessary
        args += [self.srcfile]
        #print args

        # Invoke the compiler:
        p = Popen(args)
        p.communicate()
        c = p.wait()
        assert c == 0

        assert os.path.exists(self.modfile)

    def run_command(self, cmd):
        """Run the command (using the appropriate PyRuntime), adjusting sys.path first"""
        out = self.runtime.run_command('import sys; sys.path.append("%s"); %s' % (self.tmpdir, cmd))
        return out

    def cleanup(self):
        shutil.rmtree(self.tmpdir)

class SimpleTest(unittest.TestCase):
    def test_compilation(self):
        # Verify building and running a trivial module (against multiple Python runtimes)
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
        # print sm.cu.as_str()

        for runtime in pyruntimes:
            #print(repr(runtime.get_build_flags()))

            # Build the module:
            bm = BuiltModule(sm, runtime)

            # Verify that it built:
            out = bm.run_command('import example; print(example.hello())')
            self.assertEqual(out, "Hello world!\n")
        
            # Cleanup successful test runs:
            bm.cleanup()


if __name__ == '__main__':
    unittest.main()
