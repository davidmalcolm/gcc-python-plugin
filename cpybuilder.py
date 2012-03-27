#   Copyright 2011, 2012 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2011, 2012 Red Hat, Inc.
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

from subprocess import Popen, PIPE
import re

# For the purpose of the GCC plugin, it's OK to assume that we're compiling
# with GCC itself, and thus we can use GCC extensions
with_gcc_extensions = True

def camel_case(txt):
    return ''.join([word.title()
                    for word in txt.split('_')])

def nullable_ptr(ptr):
    if ptr:
        return ptr
    else:
        return 'NULL'

def simple_unaryfunc(identifier, typename, c_expression):
    """Define a simple unaryfunc, using a specifc PyObject subclass"""
    self.add_defn("static PyObject *\n" +
                  "%s(%s *self)\n" % (identifier, typename) +
                  "{\n" +
                  "    return %s;\n" % c_expression +
                  "}\n\n")
    return identifier


class NamedEntity:
    """A thing within C code that has an identifier"""
    def __init__(self, identifier):
        self.identifier = identifier

    def c_ptr_field(self, name, cast=None):
        if hasattr(self, name):
            val = getattr(self, name)
        else:
            val = None
        if cast:
            caststr = '(%s)' % cast
        else:
            caststr = ''
        if with_gcc_extensions:
            # Designate the initializer fields:
            return '    .%s = %s%s,\n' % (name, caststr, nullable_ptr(val))
        else:
            return '    %s%s, /* %s */\n' % (caststr, nullable_ptr(val), name)

    def unaryfunc_field(self, name):
        return self.c_ptr_field(name, 'unaryfunc')

    def c_src_field(self, name):
        assert hasattr(self, name)
        val = getattr(self, name)
        if with_gcc_extensions:
            # Designate the initializer fields:
            return '    .%s = %s,\n' % (name, val)
        else:
            return '    %s, /* %s */\n' % (val, name)

    def c_src_field_value(self, name, val, cast=None):
        if cast:
            caststr = '(%s)' % cast
        else:
            caststr = ''
        if with_gcc_extensions:
            # Designate the initializer fields:
            return '    .%s = %s%s,\n' % (name, caststr, val)
        else:
            return '    %s%s, /* %s */\n' % (caststr, val, name)

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

    def add_gsdef(self, name, getter, setter, doc, closure=None):
        self.gsdefs.append(PyGetSetDef(name, getter, setter, doc, closure=None))

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

# See http://docs.python.org/c-api/typeobj.html#number-structs
class PyNumberMethods(NamedEntity):
    def __init__(self, identifier):
        NamedEntity.__init__(self, identifier)

    def c_defn(self):
        result = 'static PyNumberMethods %s = {\n' % self.identifier
        result += self.c_ptr_field('nb_add')
        result += self.c_ptr_field('nb_subtract')
        result += self.c_ptr_field('nb_multiply')
        result += '#if PY_MAJOR_VERSION < 3\n'
        result += self.c_ptr_field('nb_divide')
        result += '#endif\n'
        result += self.c_ptr_field('nb_remainder')
        result += self.c_ptr_field('nb_divmod')
        result += self.c_ptr_field('nb_power')
        result += self.unaryfunc_field('nb_negative')
        result += self.unaryfunc_field('nb_positive')
        result += self.unaryfunc_field('nb_absolute')
        result += '#if PY_MAJOR_VERSION >= 3\n'
        result += self.c_ptr_field('nb_bool')
        result += '#else\n'
        result += self.c_ptr_field('nb_nonzero')
        result += '#endif\n'
        result += self.unaryfunc_field('nb_invert')
        result += self.c_ptr_field('nb_lshift')
        result += self.c_ptr_field('nb_rshift')
        result += self.c_ptr_field('nb_and')
        result += self.c_ptr_field('nb_xor')
        result += self.c_ptr_field('nb_or')
        result += '#if PY_MAJOR_VERSION < 3\n'
        result += self.c_ptr_field('nb_coerce')
        result += '#endif\n'
        result += self.unaryfunc_field('nb_int')
        result += '#if PY_MAJOR_VERSION >= 3\n'
        result += self.c_ptr_field('nb_reserved')
        result += '#else\n'
        result += self.unaryfunc_field('nb_long')
        result += '#endif\n'
        result += self.unaryfunc_field('nb_float')
        result += '#if PY_MAJOR_VERSION < 3\n'
        result += self.unaryfunc_field('nb_oct')
        result += self.unaryfunc_field('nb_hex')
        result += '#endif\n'
        result += self.c_ptr_field('nb_inplace_add')
        result += self.c_ptr_field('nb_inplace_subtract')
        result += self.c_ptr_field('nb_inplace_multiply')
        result += '#if PY_MAJOR_VERSION < 3\n'
        result += self.c_ptr_field('nb_inplace_divide')
        result += '#endif\n'
        result += self.c_ptr_field('nb_inplace_remainder')
        result += self.c_ptr_field('nb_inplace_power')
        result += self.c_ptr_field('nb_inplace_lshift')
        result += self.c_ptr_field('nb_inplace_rshift')
        result += self.c_ptr_field('nb_inplace_and')
        result += self.c_ptr_field('nb_inplace_xor')
        result += self.c_ptr_field('nb_inplace_or')
        result += self.c_ptr_field('nb_floor_divide')
        result += self.c_ptr_field('nb_true_divide')
        result += self.c_ptr_field('nb_inplace_floor_divide')
        result += self.c_ptr_field('nb_inplace_true_divide')
        result += self.unaryfunc_field('nb_index')
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
        if not hasattr(self, 'tp_flags'):
            self.tp_flags = 'Py_TPFLAGS_DEFAULT'

    def c_defn(self):
        result = '\n'
        result += 'PyTypeObject %(identifier)s = {\n' % self.__dict__
        result += self.c_initializer()
        result += '};\n' % self.__dict__
        result +='\n'
        return result

    def c_initializer(self):
        if hasattr(self, 'ob_type'):
            ob_type_str = getattr(self, 'ob_type')
        else:
            ob_type_str = 'NULL'
        result = '    PyVarObject_HEAD_INIT(%s, 0)\n' % ob_type_str
        result += '    "%(tp_name)s", /*tp_name*/\n' % self.__dict__
        result += '    sizeof(%(struct_name)s), /*tp_basicsize*/\n' % self.__dict__
        result += '    0, /*tp_itemsize*/\n'
        result += self.c_ptr_field('tp_dealloc')
        result += self.c_ptr_field('tp_print')
        result += self.c_ptr_field('tp_getattr')
        result += self.c_ptr_field('tp_setattr')
        result += '#if PY_MAJOR_VERSION < 3\n' % self.__dict__
        result += '    0, /*tp_compare*/\n' % self.__dict__
        result += '#else\n' % self.__dict__
        result += '    0, /*reserved*/\n' % self.__dict__
        result += '#endif\n' % self.__dict__
        result += self.c_ptr_field('tp_repr')
        result += self.c_ptr_field('tp_as_number')
        result += self.c_ptr_field('tp_as_sequence')
        result += self.c_ptr_field('tp_as_mapping')
        result += self.c_ptr_field('tp_hash')
        result += self.c_ptr_field('tp_call')
        result += self.c_ptr_field('tp_str')
        result += self.c_ptr_field('tp_getattro')
        result += self.c_ptr_field('tp_setattro')
        result += self.c_ptr_field('tp_as_buffer')
        result += self.c_src_field('tp_flags')
        result += '    0, /*tp_doc*/\n'
        result += self.c_ptr_field('tp_traverse')
        result += self.c_ptr_field('tp_clear')
        result += self.c_ptr_field('tp_richcompare')
        result += '    0, /* tp_weaklistoffset */\n'
        result += self.c_ptr_field('tp_iter')
        result += self.c_ptr_field('tp_iternext')
        result += self.c_ptr_field('tp_methods')
        result += self.c_ptr_field('tp_members')
        result += self.c_ptr_field('tp_getset')
        result += self.c_ptr_field('tp_base', 'PyTypeObject*')
        result += self.c_ptr_field('tp_dict')
        result += self.c_ptr_field('tp_descr_get')
        result += self.c_ptr_field('tp_descr_set')
        result += '    0, /* tp_dictoffset */\n'
        result += self.c_ptr_field('tp_init', 'initproc')
        result += self.c_ptr_field('tp_alloc')
        result += self.c_ptr_field('tp_new')
        result += self.c_ptr_field('tp_free')
        result += self.c_ptr_field('tp_is_gc')
        result += self.c_ptr_field('tp_bases')
        result += self.c_ptr_field('tp_mro')
        result += self.c_ptr_field('tp_cache')
        result += self.c_ptr_field('tp_subclasses')
        result += self.c_ptr_field('tp_weaklist')
        result += self.c_ptr_field('tp_del')
        result += '#if PY_VERSION_HEX >= 0x02060000\n' % self.__dict__
        result += '    0, /*tp_version_tag*/\n' % self.__dict__
        result += '#endif\n' % self.__dict__
        result += '\n'
        return result

    def c_invoke_type_ready(self):
        return ('    if (PyType_Ready((PyTypeObject*)&%(identifier)s) < 0)\n'
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

    def add_simple_setter(self, identifier, typename, attrname, c_typecheck_fn, c_assignment):
        """Define a simple setter, suitable for use by a PyGetSetDef"""
        self.add_defn("static int\n" +
                      "%s(%s *self, PyObject *value, void *closure)\n" % (identifier, typename) +
                      "{\n" +
                      "    if (! %s(value)) {\n" % c_typecheck_fn +
                      "        PyErr_SetString(PyExc_TypeError,\n" +
                      '                        "%s must be an int");\n' % attrname +
                      '        return -1;\n'
                      '    }\n' +
                      '    %s;\n' % c_assignment +
                      "    return 0;\n"
                      "}\n\n")
        return identifier

    def add_simple_int_setter(self, identifier, typename, attrname, c_assignment):
        """
        Define a simple setter for an int-valued attribute, suitable for use
        by a PyGetSetDef
        """
        return self.add_simple_setter(identifier, typename, attrname,
                                      'gcc_python_int_check',
                                      c_assignment)

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
        assert isinstance(out, str)
        assert isinstance(err, str)
        assert isinstance(p, Popen)

        self.out = out
        self.err = err
        self.p = p

    def __str__(self):
        result = '\n'
        result += 'returncode: %r\n' % self.p.returncode
        result += '  %s\n' % self._describe_activity()
        result += 'Stdout:\n'
        result += self._indent(self.out)
        result += '\nStderr:\n'
        result += self._indent(self.err, 4)
        result += self._extra_info()
        return result

    def _indent(self, txt, size=2):
        return '\n'.join([' '*size + line for line in txt.splitlines()])

    def _extra_info(self):
        return ''
    
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
