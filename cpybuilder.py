from subprocess import Popen, PIPE
import re

def nullable_ptr(ptr):
    if ptr:
        return ptr
    else:
        return 'NULL'

class NamedEntity:
    """A thing within C code that has an identifier"""
    def __init__(self, identifier):
        self.identifier = identifier

class PyGetSetDef:
    def __init__(self, name, get, set, doc, closure=None):
        self.name = name
        self.get = get
        self.set = set
        self.doc = doc
        self.closure = closure

    def c_defn(self):
        result =  '    {"%s",\n' % self.name
        result += '     (getter)%s,\n' % nullable_ptr(self.get)
        result += '     (setter)%s,\n' % nullable_ptr(self.set)
        result += '     "%s",\n' % nullable_ptr(self.doc)
        result += '     %s},\n' % nullable_ptr(self.closure)
        return result

class PyGetSetDefTable(NamedEntity):
    def __init__(self, identifier, gsdefs, identifier_prefix=None, typename=None):
        NamedEntity.__init__(self, identifier)
        self.gsdefs = gsdefs
        self.identifier_prefix = identifier_prefix
        self.typename = typename

    def c_defn(self):
        result = 'static PyGetSetDef %s[] = {\n' % self.identifier
        for gsdef in self.gsdefs:
            result += gsdef.c_defn()
        result += '    {NULL}  /* Sentinel */\n'
        result += '};\n'
        return result

    def add_gsdef(self, name, get, set, doc, closure=None):
        self.gsdefs.append(PyGetSetDef(name, get, set, doc, closure=None))

    def add_simple_getter(self, cu, name, c_expression, doc):
        assert self.identifier_prefix
        assert self.typename
        identifier = self.identifier_prefix + '_get_' + name
        cu.add_simple_getter(identifier, self.typename, c_expression)
        self.add_gsdef(name, identifier, None, doc)

METH_VARARGS = 'METH_VARARGS'

class PyMethodDef:
    def __init__(self, name, fn_name, args, docstring):
        self.name = name
        self.fn_name = fn_name
        #assert args in ('METH_VARARGS', ) # FIXME
        self.args = args        
        self.docstring = docstring

    def c_defn(self):
        return ('    {"%(name)s",  %(fn_name)s, %(args)s,\n'
                '     "%(docstring)s"},\n' % self.__dict__)

class PyMethodTable(NamedEntity):
    def __init__(self, identifier, methods):
        NamedEntity.__init__(self, identifier)
        self.methods = methods

    def c_defn(self):
        result = 'static PyMethodDef %s[] = {\n' % self.identifier
        for method in self.methods:
            result += method.c_defn()
        result += '    {NULL, NULL, 0, NULL} /* Sentinel */\n'
        result += '};\n'
        return result

    def add_method(self, name, fn_name, args, docstring):
        self.methods.append(PyMethodDef(name, fn_name, args, docstring))

class PyTypeObject(NamedEntity):
    def __init__(self, identifier, localname, tp_name, struct_name, **kwargs):
        NamedEntity.__init__(self, identifier)
        self.localname = localname
        self.tp_name = tp_name
        self.struct_name = struct_name
        self.__dict__.update(kwargs)
        if not hasattr(self, 'tp_new'):
            self.tp_new = 'PyType_GenericNew'

    def c_defn(self):
        def c_ptr_field(name):
            if hasattr(self, name):
                val = getattr(self, name)
            else:
                val = None
            return '    %s, /* %s */\n' % (nullable_ptr(val), name)

        result = '\n'
        result += 'PyTypeObject %(identifier)s = {\n' % self.__dict__
        result += '    PyVarObject_HEAD_INIT(0, 0)\n'
        result += '    "%(tp_name)s", /*tp_name*/\n' % self.__dict__
        result += '    sizeof(%(struct_name)s), /*tp_basicsize*/\n' % self.__dict__
        result += '    0, /*tp_itemsize*/\n'
        result += c_ptr_field('tp_dealloc')
        result += c_ptr_field('tp_print')
        result += c_ptr_field('tp_getattr')
        result += c_ptr_field('tp_setattr')
        result += '#if PY_MAJOR_VERSION < 3\n' % self.__dict__
        result += '    0, /*tp_compare*/\n' % self.__dict__
        result += '#else\n' % self.__dict__
        result += '    0, /*reserved*/\n' % self.__dict__
        result += '#endif\n' % self.__dict__
        result += c_ptr_field('tp_repr')
        result += c_ptr_field('tp_as_number')
        result += c_ptr_field('tp_as_sequence')
        result += c_ptr_field('tp_as_mapping')
        result += c_ptr_field('tp_hash')
        result += c_ptr_field('tp_call')
        result += c_ptr_field('tp_str')
        result += c_ptr_field('tp_getattro')
        result += c_ptr_field('tp_setattro')
        result += c_ptr_field('tp_as_buffer')
        result += '    Py_TPFLAGS_DEFAULT, /*tp_flags*/\n' % self.__dict__
        result += '    0, /*tp_doc*/\n'
        result += c_ptr_field('tp_traverse')
        result += c_ptr_field('tp_clear')
        result += c_ptr_field('tp_richcompare')
        result += '    0, /* tp_weaklistoffset */\n'
        result += c_ptr_field('tp_iter')
        result += c_ptr_field('tp_iternext')
        result += c_ptr_field('tp_methods')
        result += c_ptr_field('tp_members')
        result += c_ptr_field('tp_getset')
        result += c_ptr_field('tp_base')
        result += c_ptr_field('tp_dict')
        result += c_ptr_field('tp_descr_get')
        result += c_ptr_field('tp_descr_set')
        result += '    0, /* tp_dictoffset */\n'
        result += c_ptr_field('tp_init')
        result += c_ptr_field('tp_alloc')
        result += c_ptr_field('tp_new')
        result += c_ptr_field('tp_free')
        result += c_ptr_field('tp_is_gc')
        result += c_ptr_field('tp_bases')
        result += c_ptr_field('tp_mro')
        result += c_ptr_field('tp_cache')
        result += c_ptr_field('tp_subclasses')
        result += c_ptr_field('tp_weaklist')
        result += c_ptr_field('tp_del')
        result += '#if PY_VERSION_HEX >= 0x02060000\n' % self.__dict__
        result += '    0, /*tp_version_tag*/\n' % self.__dict__
        result += '#endif\n' % self.__dict__
        result += '};\n' % self.__dict__
        result +='\n'
        return result

    def c_invoke_type_ready(self):
        return ('    if (PyType_Ready(&%(identifier)s) < 0)\n'
                '        goto error;\n'
                '\n') % self.__dict__

    def c_invoke_add_to_module(self):
        return ('    Py_INCREF(&%(identifier)s);\n'
                '    PyModule_AddObject(m, "%(localname)s", (PyObject *)&%(identifier)s);\n'
                '\n') % self.__dict__

class PyModule:
    def __init__(self, modname, modmethods, moddoc):
        self.modname = modname
        self.moddoc = moddoc
        assert (modmethods is None) or isinstance(modmethods, PyMethodTable)
        self.modmethods = modmethods

        if self.modmethods:
            self.modmethods_as_ptr = self.modmethods.identifier
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

    def add_simple_getter(self, identifier, typename, c_expression):
        """Define a simple getter, suitable for use by a PyGetSetDef"""
        self.add_defn("static PyObject *\n" +                      
                      "%s(%s *self, void *closure)\n" % (identifier, typename) +
                      "{\n" +
                      "    return %s;\n" % c_expression + 
                      "}\n\n")
        return identifier



class SimpleModule:
    """
    A C extension module built from a single C file
    """
    def __init__(self):
        self.cu = CompilationUnit()

        self._modinit_preinit = ''
        self._modinit_postinit = ''

    def add_type_object(self, name, localname,
                        tp_name, struct_name, **kwargs):
        pytype = PyTypeObject(name, localname, tp_name, struct_name, **kwargs)
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
        result += self._indent(self.err, 4)
        return result

    def _indent(self, txt, size=2):
        return '\n'.join([' '*size + line for line in txt.splitlines()])
    
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
