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
import shutil
import tempfile
import unittest

from subprocess import Popen, PIPE

from cpybuilder import *


# FIXME: this will need tweaking:
pyruntimes = [PyRuntime('/usr/bin/python2.7', '/usr/bin/python2.7-config'),
              #PyRuntime('/usr/bin/python2.7-debug', '/usr/bin/python2.7-debug-config'),
              #PyRuntime('/usr/bin/python3.2mu', '/usr/bin/python3.2mu-config'),
              #PyRuntime('/usr/bin/python3.2dmu', '/usr/bin/python3.2dmu-config')
              ]

class CompilationError(CommandError):
    def __init__(self, bm):
        CommandError.__init__(self, bm.out, bm.err, bm.p)
        self.bm = bm
    
    def _describe_activity(self):
        return 'compiling: %s' % ' '.join(self.bm.args)

class BuiltModule:
    """A test build of a SimpleModule for a PyRuntime, done in a tempdir"""
    def __init__(self, sm, runtime):
        self.sm = sm
        self.runtime = runtime

    def write_src(self, extra_cflags = None):
        self.tmpdir = tempfile.mkdtemp()

        self.srcfile = os.path.join(self.tmpdir, 'example.c')
        self.modfile = os.path.join(self.tmpdir, self.runtime.get_module_filename('example'))

        f = open(self.srcfile, 'w')
        f.write(self.sm.cu.as_str())
        f.close()


    def compile_src(self, extra_cflags = None):
        cflags = self.runtime.get_build_flags()
        self.args = ['gcc']
        self.args += ['-o', self.modfile]
        self.args += cflags.split()
        self.args += ['-Wall',  '-Werror'] # during testing
        self.args += ['-shared'] # not sure why this is necessary
        if extra_cflags:
            self.args += extra_cflags
        self.args += [self.srcfile]
        #print self.args

        env = dict(os.environ)
        env['LANG'] = 'C'

        # Invoke the compiler:
        self.p = Popen(self.args, env=env, stdout=PIPE, stderr=PIPE)
        self.out, self.err = self.p.communicate()
        c = self.p.wait()
        if c != 0:
            raise CompilationError(self)

        assert os.path.exists(self.modfile)

    def build(self, extra_cflags = None):
        self.write_src()
        self.compile_src(extra_cflags)

    def run_command(self, cmd):
        """Run the command (using the appropriate PyRuntime), adjusting sys.path first"""
        out = self.runtime.run_command('import sys; sys.path.append("%s"); %s' % (self.tmpdir, cmd))
        return out

    def cleanup(self):
        shutil.rmtree(self.tmpdir)

class SimpleTest(unittest.TestCase):
    #def __init__(self, pyruntime):
    #    self.pytun
    def test_simple_compilation(self):
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
            # Build the module:
            bm = BuiltModule(sm, runtime)
            bm.build()

            # Verify that it built:
            out = bm.run_command('import example; print(example.hello())')
            self.assertEqual(out, "Hello world!\n")
        
            # Cleanup successful test runs:
            bm.cleanup()

    def test_module_with_type(self):
        # Verify an extension with a type
        sm = SimpleModule()

        sm.cu.add_decl("""
struct PyExampleType {
     PyObject_HEAD
     int i;
};
""")

        sm.cu.add_defn("PyObject *\n"
                       "example_Example_repr(PyObject * self)\n"
                       "{\n"
                       "#if PY_MAJOR_VERSION < 3\n"
                       "    return PyString_FromString(\"example.ExampleType('')\");\n"
                       "#else\n"
                       "    return PyUnicode_FromString(\"example.ExampleType('')\");\n"
                       "#endif\n"
                       "}\n")
        sm.add_type_object(name = 'example_ExampleType',
                           localname = 'ExampleType',
                           tp_name = 'example.ExampleType',
                           struct_name = 'struct PyExampleType',
                           tp_repr = 'example_Example_repr')

        sm.add_module_init('example', modmethods=None, moddoc='This is a doc string')
        # print sm.cu.as_str()

        for runtime in pyruntimes:
            # Build the module:
            bm = BuiltModule(sm, runtime)
            bm.build()

            # Verify that it built:
            out = bm.run_command('import example; print(repr(example.ExampleType()))')
            self.assertEqual(out, "example.ExampleType('')\n")

            # Cleanup successful test runs:
            bm.cleanup()

    def test_version_parsing(self):
        vi  = PyVersionInfo.from_text("sys.version_info(major=2, minor=7, micro=1, releaselevel='final', serial=0)")
        self.assertEqual(vi,
                         PyVersionInfo(major=2, minor=7, micro=1, releaselevel='final', serial=0))

        # "sys.version_info(major=2, minor=7, micro=1, releaselevel='final', serial=0)"
        # "sys.version_info(major=3, minor=2, micro=0, releaselevel='candidate', serial=1)"

                         


if __name__ == '__main__':
    unittest.main()
