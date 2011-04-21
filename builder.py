#class Writer:
#    pass

#def fmt_str(template, )

# FIXME: this isn't used yet:
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
  0, /*tp_flags*/
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
        return ("""
    if (PyType_Ready(&%(name)s) < 0)
        goto error;
""" % self.__dict__)

    def c_invoke_add_to_module(self):
        return ("""
    Py_INCREF(&%(name)s);
    PyModule_AddObject(m, "%(localname)s", (PyObject *)&%(name)s);
""" % self.__dict__)


class PyModule:
    def __init__(self, modname, moddoc):
        self.modname = modname
        self.moddoc = moddoc
        self.modmethods = 'NULL' # FIXME

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
    "%(modname)s",
    "%(moddoc)s",
    -1,
    NULL, NULL, NULL, NULL, NULL
};
#endif
""" % self.__dict__)

        
    def c_invoke_ctor(self):
        return ("""
    #if PY_MAJOR_VERSION < 3
    m = Py_InitModule3("%(modname)s", %(modmethods)s,
                       "%(moddoc)s");
    #else
    m = PyModule_Create(&%(modname)smodule);
    #endif
    if (!m) {
        goto error;
    }

""" % self.__dict__)

class ModuleWriter:
    def __init__(self, modname):
        self.modname = modname

        self.includes = '#include <Python.h>\n'

        self.prototypes = ''
        
        self.definitions = ''
        self.modinit_preinit = ''
        self.modinit_postinit = ''

    def as_str(self):
        return (self.includes + 
                self.make_header('Prototypes') +
                self.prototypes + 
                self.make_header('Definitions') +
                self.definitions)

    def add_type_object(self, name, localname,
                        tp_name, struct_name,
                        tp_dealloc = 'NULL', tp_repr = 'NULL',
                        tp_methods = 'NULL', tp_init = 'NULL',  tp_new = None):
        if not tp_new:
            tp_new = 'PyType_GenericNew';

        pytype = PyTypeObject(name, localname, tp_name, struct_name, tp_dealloc, tp_repr, tp_methods, tp_init, tp_new)
        self.definitions += pytype.c_defn()
        self.modinit_preinit += pytype.c_invoke_type_ready()
        self.modinit_postinit += pytype.c_invoke_add_to_module()

    def make_header(self, text):
        return '\n/**** %s ****/\n\n' % text

    def module_init(self, modname, modmethods, moddoc):
        pymod = PyModule(modname, moddoc)


        self.prototypes += pymod.c_initfn_decl()

        self.definitions += pymod.c_py3k_moduledef()

        self.definitions += pymod.c_initfn_def_begin()
        self.definitions += self.modinit_preinit
        self.definitions += pymod.c_invoke_ctor()
        self.definitions += self.modinit_postinit
        self.definitions += pymod.c_initfn_def_end()

    def add_type(self, typename):
        self.definitions

