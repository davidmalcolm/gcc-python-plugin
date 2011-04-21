#class Writer:
#    pass

#def fmt_str(template, )

# FIXME: this isn't used yet:
from collections import namedtuple
class PyTypeObject(namedtuple('PyTypeObject', 'name tp_name struct_name tp_dealloc tp_repr tp_methods tp_init tp_new')):
    def get_definition_str(self):
        self.definitions += ("""
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
        self.definitions += ("""
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
""" % locals())

        self.modinit_preinit += ("""
    if (PyType_Ready(&%(name)s) < 0)
        goto error;
""" % locals())

        self.modinit_postinit += ("""
    Py_INCREF(&%(name)s);
    PyModule_AddObject(m, "%(localname)s", (PyObject *)&%(name)s);
""" % locals())

    def make_header(self, text):
        return '\n/**** %s ****/\n\n' % text

    def module_init(self, modname, modmethods, moddoc):
        self.prototypes += ("""
#if PY_MAJOR_VERSION < 3
PyMODINIT_FUNC init%s(void);
#else
PyMODINIT_FUNC PyInit_%s(void);
#endif
""" % (modname, modname))

        self.definitions += ("""
#if PY_MAJOR_VERSION >= 3
static PyModuleDef %(modname)smodule = {
    PyModuleDef_HEAD_INIT,
    "%(modname)s",
    "%(moddoc)s",
    -1,
    NULL, NULL, NULL, NULL, NULL
};
#endif

#if PY_MAJOR_VERSION < 3
PyMODINIT_FUNC init%(modname)s(void)
#else
PyMODINIT_FUNC PyInit_%(modname)s(void)
#endif
{
    PyObject *m = NULL;
""" % locals())
        self.indent = 1

        self.definitions += self.modinit_preinit

        self.definitions += ("""
    #if PY_MAJOR_VERSION < 3
    m = Py_InitModule3("%(modname)s", %(modmethods)s,
                       "%(moddoc)s");
    #else
    m = PyModule_Create(&%(modname)smodule);
    #endif
    if (!m) {
        goto error;
    }
""" % locals())

        self.definitions += self.modinit_postinit

        self.definitions += ("""
    #if PY_MAJOR_VERSION < 3
    return;
    #else
    return m;
    #endif

error:
    #if PY_MAJOR_VERSION < 3
    return;
    #else
    PY_XDECREF(m);
    return NULL;
    #endif
}
""")

    def add_type(self, typename):
        self.definitions

