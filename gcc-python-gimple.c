#include <Python.h>
#include "gcc-python.h"
#include "gcc-python-wrappers.h"
#include "gimple.h"

PyObject *
gcc_Gimple_repr(struct PyGccGimple * self)
{
    return PyString_FromFormat("%s()", Py_TYPE(self)->tp_name);
}

static PyObject *
str_for_assign(gimple gs)
{
    PyObject *lhs = NULL;
    PyObject *rhs = NULL;
    PyObject *result = NULL;

    assert(is_gimple_assign(gs));
    
    lhs = PyString_FromFormat("lhs");
    if (!lhs) {
	goto error;
    }
    rhs = PyString_FromFormat("rhs");
    if (!rhs) {
	goto error;
    }
    
    result = PyString_FromFormat("gcc.GimpleAssign(\"%s <- %s\")",
				 PyString_AsString(lhs),
				 PyString_AsString(rhs));
 error:
    Py_XDECREF(lhs);
    Py_XDECREF(rhs);
    return result;
}


PyObject *
gcc_Gimple_str(struct PyGccGimple * self)
{
    switch (gimple_code(self->stmt)) {
    case GIMPLE_ASM:
	return PyString_FromFormat("GIMPLE_ASM");

    case GIMPLE_ASSIGN:
	return str_for_assign(self->stmt);
	return PyString_FromFormat("GIMPLE_ASSIGN");
	
    case GIMPLE_BIND:
	return PyString_FromFormat("GIMPLE_BIND");
	
    case GIMPLE_CALL:
	return PyString_FromFormat("GIMPLE_CALL");
	
    case GIMPLE_COND:
	return PyString_FromFormat("GIMPLE_COND");

    case GIMPLE_LABEL:
	return PyString_FromFormat("GIMPLE_LABEL");

    case GIMPLE_GOTO:
	return PyString_FromFormat("GIMPLE_GOTO");

    case GIMPLE_NOP:
	return PyString_FromFormat("GIMPLE_NOP");

    case GIMPLE_RETURN:
	return PyString_FromFormat("GIMPLE_RETURN");

    case GIMPLE_SWITCH:
	return PyString_FromFormat("GIMPLE_SWITCH");

    case GIMPLE_TRY:
	return PyString_FromFormat("GIMPLE_TRY");

    case GIMPLE_PHI:
	return PyString_FromFormat("GIMPLE_PHI");

    case GIMPLE_OMP_PARALLEL:
	return PyString_FromFormat("GIMPLE_OMP_PARALLEL");

    case GIMPLE_OMP_TASK:
	return PyString_FromFormat("GIMPLE_OMP_TASK");

    case GIMPLE_OMP_ATOMIC_LOAD:
	return PyString_FromFormat("GIMPLE_OMP_ATOMIC_LOAD");

    case GIMPLE_OMP_ATOMIC_STORE:
	return PyString_FromFormat(" GIMPLE_OMP_ATOMIC_STORE");

    case GIMPLE_OMP_FOR:
	return PyString_FromFormat("GIMPLE_OMP_FOR");

    case GIMPLE_OMP_CONTINUE:
	return PyString_FromFormat("GIMPLE_OMP_CONTINUE");

    case GIMPLE_OMP_SINGLE:
	return PyString_FromFormat("GIMPLE_OMP_SINGLE");

    case GIMPLE_OMP_RETURN:
	return PyString_FromFormat("GIMPLE_OMP_RETURN");

    case GIMPLE_OMP_SECTIONS:
	return PyString_FromFormat("GIMPLE_OMP_SECTIONS");

    case GIMPLE_OMP_SECTIONS_SWITCH:
	return PyString_FromFormat("GIMPLE_OMP_SECTIONS_SWITCH");

    case GIMPLE_OMP_MASTER:
    case GIMPLE_OMP_ORDERED:
    case GIMPLE_OMP_SECTION:
	return PyString_FromFormat("GIMPLE_OMP_(block)");

    case GIMPLE_OMP_CRITICAL:
	return PyString_FromFormat("GIMPLE_OMP_CRITICAL");

    case GIMPLE_CATCH:
	return PyString_FromFormat("GIMPLE_CATCH");

    case GIMPLE_EH_FILTER:
	return PyString_FromFormat("GIMPLE_EH_FILTER");

    case GIMPLE_EH_MUST_NOT_THROW:
	return PyString_FromFormat("GIMPLE_EH_MUST_NOT_THROW");

    case GIMPLE_RESX:
	return PyString_FromFormat("GIMPLE_RESX");

    case GIMPLE_EH_DISPATCH:
	return PyString_FromFormat("GIMPLE_EH_DISPATCH");

    case GIMPLE_DEBUG:
	return PyString_FromFormat("GIMPLE_DEBUG");

    case GIMPLE_PREDICT:
	return PyString_FromFormat("GIMPLE_PREDICT");

    default:
	assert(0);
    }
}

/*
  PEP-7  
Local variables:
c-basic-offset: 4
End:
*/
