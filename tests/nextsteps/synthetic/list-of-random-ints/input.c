#include <Python.h>

PyObject *
make_a_list_of_random_ints_badly(PyObject *self,
                                 PyObject *args)
{
    PyObject *list, *item;
    long count, i;

    if (!PyArg_ParseTuple(args, "i", &count)) {
         return NULL;
    }

    list = PyList_New(0);

    for (i = 0; i < count; i++) {
        item = PyLong_FromLong(random());
        PyList_Append(list, item);
    }

    return list;
}
