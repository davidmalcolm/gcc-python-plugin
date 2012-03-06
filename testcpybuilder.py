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


from distutils import sysconfig as sc
import os
import shutil
from subprocess import Popen, PIPE
import sys
import sysconfig
import tempfile
import unittest

import six

from cpybuilder import *

def get_module_filename(name):
    # Python 3.2 onwards embeds the SOABI variable in module filenames
    # (see PEP 3149):
    SOABI = sysconfig.get_config_var('SOABI')
    if SOABI:
        return '%s.%s.so' % (name, SOABI)

    if hasattr(sys, "getobjects"):
        # debug build of Python:
        # FIXME: this is a Fedora-ism:
        return '%s_d.so' % name
    else:
        # regular (optimized) build of Python:
        return '%s.so' % name

class CompilationError(CommandError):
    def __init__(self, bm):
        CommandError.__init__(self, bm.out, bm.err, bm.p)
        self.bm = bm
    
    def _describe_activity(self):
        return 'compiling: %s' % ' '.join(self.bm.args)

class BuiltModule:
    """A test build of a SimpleModule using sys.executable, done in a tempdir"""
    def __init__(self, sm):
        self.sm = sm

    def write_src(self, modname, extra_cflags = None):
        self.tmpdir = tempfile.mkdtemp()

        self.srcfile = os.path.join(self.tmpdir, '%s.c' % modname)
        self.modfile = os.path.join(self.tmpdir, get_module_filename(modname))

        f = open(self.srcfile, 'w')
        f.write(self.sm.cu.as_str())
        f.close()


    def compile_src(self, extra_cflags = None):
        self.args = [os.environ.get('GCC', 'gcc')]
        self.args += ['-o', self.modfile]
        self.args +=  ['-I' + sc.get_python_inc(),
                       '-I' + sc.get_python_inc(plat_specific=True)]
        self.args += sc.get_config_var('CFLAGS').split()
        self.args += ['-Wall',  '-Werror'] # during testing
        # on some builds of Python, CFLAGS does not contain -fPIC, but it
        # appears to still be necessary:
        self.args += ['-fPIC']
        self.args += ['-shared'] # not sure why this is necessary
        if extra_cflags:
            self.args += extra_cflags
        self.args += [self.srcfile]
        # print(self.args)

        env = dict(os.environ)
        env['LC_ALL'] = 'C'

        # Invoke the compiler:
        self.p = Popen(self.args, env=env, stdout=PIPE, stderr=PIPE)
        self.out, self.err = self.p.communicate()
        if six.PY3:
            self.out = self.out.decode()
            self.err = self.err.decode()
        c = self.p.wait()
        if c != 0:
            raise CompilationError(self)

        assert os.path.exists(self.modfile)
        # print(self.modfile)

    def build(self, modname, extra_cflags = None):
        self.write_src(modname)
        self.compile_src(extra_cflags)

    def cleanup(self):
        shutil.rmtree(self.tmpdir)

class SimpleTest(unittest.TestCase):

    # We'll be manipulating sys.path during the test
    # Save a copy, and restore it after each test:
    def setUp(self):
        self.saved_sys_path = sys.path
        sys.path = sys.path[:]

    def tearDown(self):
        sys.path = self.saved_sys_path

    def test_simple_compilation(self):
        # Verify building and running a trivial module (against multiple Python runtimes)
        MODNAME = 'simple_compilation'
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

        sm.add_module_init(MODNAME, modmethods=methods, moddoc='This is a doc string')
        # print(sm.cu.as_str())

        # Build the module:
        bm = BuiltModule(sm)
        bm.build(MODNAME)

        # Verify that it built:
        sys.path.append(bm.tmpdir)
        import simple_compilation
        self.assertEqual(simple_compilation.hello(), 'Hello world!')
        
        # Cleanup successful test runs:
        bm.cleanup()

    def test_module_with_type(self):
        # Verify an extension with a type
        MODNAME = 'module_with_type'
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

        sm.add_module_init(MODNAME, modmethods=None, moddoc='This is a doc string')
        # print sm.cu.as_str()

        # Build the module:
        bm = BuiltModule(sm)
        bm.build(MODNAME)

        # Verify that it built:
        sys.path.append(bm.tmpdir)
        import module_with_type
        self.assertEqual(repr(module_with_type.ExampleType()),
                         "example.ExampleType('')")

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
