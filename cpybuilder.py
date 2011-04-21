from subprocess import Popen, PIPE
import re

METH_VARARGS = 'METH_VARARGS'

class PyMethodDef:
    def __init__(self, name, fn_name, args, docstring):
        self.name = name
        self.fn_name = fn_name
        assert args in ('METH_VARARGS', ) # FIXME
        self.args = args        
        self.docstring = docstring

    def c_defn(self):
        return ('    {"%(name)s",  %(fn_name)s, %(args)s,\n'
                '     "%(docstring)s"},\n' % self.__dict__)

class PyMethodTable:
    def __init__(self, name, methods):
        self.name = name
        self.methods = methods

    def c_defn(self):
        result = 'static PyMethodDef %s[] = {\n' % self.name
        for method in self.methods:
            result += method.c_defn()
        result += '    {NULL, NULL, 0, NULL} /* Sentinel */\n'
        result += '};\n'
        return result

class PyTypeObject:
    def __init__(self, name, localname, tp_name, struct_name, tp_dealloc, tp_repr, tp_methods, tp_init, tp_new):
        self.name = name
        self.localname = localname
        self.tp_name = tp_name
        self.struct_name = struct_name
        self.tp_dealloc = tp_dealloc
        self.tp_repr = tp_repr
        self.tp_methods = tp_methods
        self.tp_init = tp_init
        self.tp_new = tp_new

    def c_defn(self):
        return ("""
PyTypeObject %(name)s = {
  PyVarObject_HEAD_INIT(0, 0)
  "%(tp_name)s", /*tp_name*/
  sizeof(%(struct_name)s), /*tp_basicsize*/
  0, /*tp_itemsize*/
  %(tp_dealloc)s, /*tp_dealloc*/
  0, /*tp_print*/
  0, /*tp_getattr*/
  0, /*tp_setattr*/
  #if PY_MAJOR_VERSION < 3
  0, /*tp_compare*/
  #else
  0, /*reserved*/
  #endif
  %(tp_repr)s, /*tp_repr*/
  0, /*tp_as_number*/
  0, /*tp_as_sequence*/
  0, /*tp_as_mapping*/
  0, /*tp_hash*/
  0, /*tp_call*/
  0, /*tp_str*/
  0, /*tp_getattro*/
  0, /*tp_setattro*/
  0, /*tp_as_buffer*/
  Py_TPFLAGS_DEFAULT, /*tp_flags*/
  0, /*tp_doc*/
  0, /*tp_traverse*/
  0, /*tp_clear*/
  0, /*tp_richcompare*/
  0, /*tp_weaklistoffset*/
  0, /*tp_iter*/
  0, /*tp_iternext*/
  %(tp_methods)s, /*tp_methods*/
  0, /*tp_members*/
  0, /*tp_getset*/
  0, /*tp_base*/
  0, /*tp_dict*/
  0, /*tp_descr_get*/
  0, /*tp_descr_set*/
  0, /*tp_dictoffset*/
  %(tp_init)s, /*tp_init*/
  0, /*tp_alloc*/
  %(tp_new)s, /*tp_new*/
  0, /*tp_free*/
  0, /*tp_is_gc*/
  0, /*tp_bases*/
  0, /*tp_mro*/
  0, /*tp_cache*/
  0, /*tp_subclasses*/
  0, /*tp_weaklist*/
  0, /*tp_del*/
  #if PY_VERSION_HEX >= 0x02060000
  0, /*tp_version_tag*/
  #endif
};
""" % self.__dict__)

    def c_invoke_type_ready(self):
        return ('    if (PyType_Ready(&%(name)s) < 0)\n'
                '        goto error;\n'
                '\n') % self.__dict__

    def c_invoke_add_to_module(self):
        return ('    Py_INCREF(&%(name)s);\n'
                '    PyModule_AddObject(m, "%(localname)s", (PyObject *)&%(name)s);\n'
                '\n') % self.__dict__

class PyModule:
    def __init__(self, modname, modmethods, moddoc):
        self.modname = modname
        self.moddoc = moddoc
        assert (modmethods is None) or isinstance(modmethods, PyMethodTable)
        self.modmethods = modmethods

        if self.modmethods:
            self.modmethods_as_ptr = self.modmethods.name
        else:
            self.modmethods_as_ptr = 'NULL'

    def c_initfn_decl(self):
        return ("""
#if PY_MAJOR_VERSION < 3
PyMODINIT_FUNC init%(modname)s(void);
#else
PyMODINIT_FUNC PyInit_%(modname)s(void);
#endif
""" % self.__dict__)

    
    def c_initfn_def_begin(self):
        return ("""
#if PY_MAJOR_VERSION < 3
PyMODINIT_FUNC init%(modname)s(void)
#else
PyMODINIT_FUNC PyInit_%(modname)s(void)
#endif
{
    PyObject *m = NULL;
""" % self.__dict__)


    def c_initfn_def_end(self):
        return ("""
    #if PY_MAJOR_VERSION < 3
    return;
    #else
    return m;
    #endif

error:
    #if PY_MAJOR_VERSION < 3
    return;
    #else
    Py_XDECREF(m);
    return NULL;
    #endif
}
""")


    def c_py3k_moduledef(self):
        return ("""
#if PY_MAJOR_VERSION >= 3
static PyModuleDef %(modname)smodule = {
    PyModuleDef_HEAD_INIT,
    "%(modname)s", /* m_name */
    "%(moddoc)s", /* m_doc */
    -1,   /* m_size */
    %(modmethods_as_ptr)s, /* m_methods */
    NULL, NULL, NULL, NULL
};
#endif
""" % self.__dict__)

        
    def c_invoke_ctor(self):
        return ("""
    #if PY_MAJOR_VERSION < 3
    m = Py_InitModule3("%(modname)s", %(modmethods_as_ptr)s,
                       "%(moddoc)s");
    #else
    m = PyModule_Create(&%(modname)smodule);
    #endif
    if (!m) {
        goto error;
    }

""" % self.__dict__)

class CompilationUnit:
    """
    A single C file
    """
    def __init__(self):
        self._includes = '#include <Python.h>\n'

        self._prototypes = ''
        
        self._definitions = ''

    def add_include(self, path):
        self._includes += '#include "%s"\n' % path

    def add_decl(self, text):
        self._prototypes += text

    def add_defn(self, text):
        self._definitions += text

    def as_str(self):
        return ('/* Autogenerated by cpybuilder */\n' +
                self._includes +
                self.make_header('Prototypes') +
                self._prototypes + 
                self.make_header('Definitions') +
                self._definitions)

    def make_header(self, text):
        return '\n/**** %s ****/\n\n' % text

class SimpleModule:
    """
    A C extension module built from a single C file
    """
    def __init__(self):
        self.cu = CompilationUnit()

        self._modinit_preinit = ''
        self._modinit_postinit = ''

    def add_type_object(self, name, localname,
                        tp_name, struct_name,
                        tp_dealloc = 'NULL', tp_repr = 'NULL',
                        tp_methods = 'NULL', tp_init = 'NULL',  tp_new = None):
        if not tp_new:
            tp_new = 'PyType_GenericNew';

        pytype = PyTypeObject(name, localname, tp_name, struct_name, tp_dealloc, tp_repr, tp_methods, tp_init, tp_new)
        self.cu.add_defn(pytype.c_defn())
        self._modinit_preinit += pytype.c_invoke_type_ready()
        self._modinit_postinit += pytype.c_invoke_add_to_module()

    def add_module_init(self, modname, modmethods, moddoc):
        pymod = PyModule(modname, modmethods, moddoc)

        self.cu.add_decl(pymod.c_initfn_decl())

        self.cu.add_defn(pymod.c_py3k_moduledef())

        self.cu.add_defn(pymod.c_initfn_def_begin())
        self.cu.add_defn(self._modinit_preinit)
        self.cu.add_defn(pymod.c_invoke_ctor())
        self.cu.add_defn(self._modinit_postinit)
        self.cu.add_defn(pymod.c_initfn_def_end())

class SimpleBuild:
    def __init__(self, sm, builddir='.'):
        self.sm

    #def generate_c(self):
    #    with open(sm.name

class CommandError(RuntimeError):
    def __init__(self, out, err, p):
        self.out = out
        self.err = err
        self.p = p

    def __str__(self):
        result = '\n'
        result += 'returncode: %r\n' % self.p.returncode
        result += '  %s\n' % self._describe_activity()
        result += 'Stdout:\n'
        result += self._indent(self.out)
        result += 'Stderr:\n'
        result += self._indent(self.err)
        return result

    def _indent(self, txt):
        return '\n'.join(['  ' + line for line in txt.splitlines()])
    
class PyRuntimeError(CommandError):
    def __init__(self, runtime, cmd, out, err, p):
        CommandError.__init__(self, out, err, p)
        self.runtime = runtime
        self.cmd = cmd

    def _describe_activity(self):
        return 'running: %s -c %r' % (self.runtime.executable , self.cmd)

from collections import namedtuple
class PyVersionInfo(namedtuple('PyVersionInfo', 'major minor micro releaselevel serial')):
    @classmethod
    def from_text(cls, txt):
        # e.g.:
        #   sys.version_info(major=2, minor=7, micro=1, releaselevel='final', serial=0)
        m = re.match('sys\.version_info\(major=([0-9]+), minor=([0-9]+), micro=([0-9]+), releaselevel=\'(.*)\', serial=([0-9]+)\)', txt)
        return PyVersionInfo(major=int(m.group(1)),
                             minor=int(m.group(2)),
                             micro=int(m.group(3)),
                             releaselevel=m.group(4),
                             serial=int(m.group(5)))

class PyRuntime:
    def __init__(self, executable, config):
        self.executable = executable
        self.config = config

        pydebug = self.run_command('import sys; print(hasattr(sys, "getobjects"))').strip()
        assert pydebug in ('False', 'True')
        self.pydebug = (pydebug == 'True')

        versiontext = self.run_command('import sys; print(sys.version_info)').strip()
        self.versioninfo = PyVersionInfo.from_text(versiontext)

    def is_py3k(self):
        return self.versioninfo.major == 3

    def get_build_flags(self):
        return self.get_config_value(['--cflags', '--ldflags'])

    def get_config_value(self, flags):
        args = [self.config] + flags
        p = Popen(args, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        return ' '.join(out.splitlines()).strip()

    def run_command(self, cmd, checkoutput=True):
        p = Popen([self.executable, '-c', cmd],
                  stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if p.returncode != 0:
            raise PyRuntimeError(self, cmd, out, err, p)
        return out

    #def compile_simple_module(self, sm):

    def get_module_filename(self, name):
        # FIXME: this is a Fedora-ism:
        # FIXME: support for 3.2 onwards also?
        if self.pydebug:
            return '%s_d.so' % name
        else:
            return '%s.so' % name
