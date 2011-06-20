#include <Python.h>

PyObject*
my_method_A(PyObject *self, PyObject *args)
{
    Py_RETURN_NONE;
}

PyObject*
my_method_B(PyObject *self, PyObject *args)
{
    Py_RETURN_NONE;
}

static PyMethodDef def_table[] = {
    {"my_method_A",  my_method_A, METH_VARARGS, NULL},
    {"my_method_B",  my_method_B, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL} /* Sentinel */
};


