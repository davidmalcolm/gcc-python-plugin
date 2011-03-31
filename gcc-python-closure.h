#ifndef INCLUDED__GCC_PYTHON_CLOSURE_H
#define INCLUDED__GCC_PYTHON_CLOSURE_H

struct callback_closure
{
    PyObject *callback;
    PyObject *extraargs;
};

PyObject *
gcc_python_closure_make_args(struct callback_closure * closure, PyObject *wrapped_gcc_data);

#endif /* INCLUDED__GCC_PYTHON_CLOSURE_H */
