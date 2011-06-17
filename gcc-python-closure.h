#ifndef INCLUDED__GCC_PYTHON_CLOSURE_H
#define INCLUDED__GCC_PYTHON_CLOSURE_H

struct callback_closure
{
    PyObject *callback;
    PyObject *extraargs;
    PyObject *kwargs;
};

struct callback_closure *
gcc_python_closure_new(PyObject *callback, PyObject *extraargs, PyObject *kwargs);

PyObject *
gcc_python_closure_make_args(struct callback_closure * closure, PyObject *wrapped_gcc_data);

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/

#endif /* INCLUDED__GCC_PYTHON_CLOSURE_H */
