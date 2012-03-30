/*
   Copyright 2011, 2012 David Malcolm <dmalcolm@redhat.com>
   Copyright 2011, 2012 Red Hat, Inc.

   This is free software: you can redistribute it and/or modify it
   under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful, but
   WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
   General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program.  If not, see
   <http://www.gnu.org/licenses/>.
*/

#include <Python.h>
#include "gcc-python.h"
#include "gcc-python-wrappers.h"
#include "diagnostic.h"
#include "proposed-plugin-api/gcc-location.h"

/*
  Wrapper for GCC's (opt_pass *)
*/

/*
   Ensure we have a unique PyGccPass per pass address (by maintaining a dict)

   For passes defined in Python, this dictionary maps from
   long (struct opt_pass *) to the gcc.Pass wrapper object for that pass

   The references on the right-hand-side keep these wrappers alive
*/
static PyObject *pass_wrapper_cache = NULL;

static bool impl_gate(void)
{
    PyObject *pass_obj;
    PyObject *cfun_obj = NULL;
    PyObject* result_obj;
    int result;
    GccLocationI saved_loc = Gcc_GetInputLocation();

    assert(current_pass);
    pass_obj = gcc_python_make_wrapper_pass(current_pass);
    assert(pass_obj); /* we own a ref at this point */

    if (!PyObject_HasAttrString(pass_obj, "gate")) {
        /* No "gate" method?  Always execute this pass: */
        Py_DECREF(pass_obj);
        return true;
    }

    /* Supply the current function, if any */
    if (cfun) {
        /* Temporarily override input_location to the top of the function: */
        Gcc_SetInputLocation(GccPrivate_make_LocationI(cfun->function_start_locus));
        cfun_obj = gcc_python_make_wrapper_function(cfun);
        if (!cfun_obj) {
            gcc_python_print_exception("Unhandled Python exception raised calling 'gate' method");
            Py_DECREF(pass_obj);
            Gcc_SetInputLocation(saved_loc);
            return false;
        }
        result_obj = PyObject_CallMethod(pass_obj, "gate", "O", cfun_obj, NULL);
    } else {
        result_obj = PyObject_CallMethod(pass_obj, "gate", NULL);
    }

    Py_XDECREF(cfun_obj);
    Py_DECREF(pass_obj);

    if (!result_obj) {
        gcc_python_print_exception("Unhandled Python exception raised calling 'gate' method");
        Gcc_SetInputLocation(saved_loc);
        return false;
    }

    result = PyObject_IsTrue(result_obj);
    Py_DECREF(result_obj);
    Gcc_SetInputLocation(saved_loc);
    return result;
}

static unsigned int impl_execute(void)
{
    PyObject *pass_obj;
    PyObject *cfun_obj = NULL;
    PyObject* result_obj;
    GccLocationI saved_loc = Gcc_GetInputLocation();

    assert(current_pass);
    pass_obj = gcc_python_make_wrapper_pass(current_pass);
    assert(pass_obj); /* we own a ref at this point */

    /* Supply the current function, if any */
    if (cfun) {
        /* Temporarily override input_location to the top of the function: */
        Gcc_SetInputLocation(GccPrivate_make_LocationI(cfun->function_start_locus));
        cfun_obj = gcc_python_make_wrapper_function(cfun);
        if (!cfun_obj) {
            gcc_python_print_exception("Unhandled Python exception raised calling 'execute' method");
            Py_DECREF(pass_obj);
            Gcc_SetInputLocation(saved_loc);
            return false;
        }
        result_obj = PyObject_CallMethod(pass_obj, "execute", "O", cfun_obj, NULL);
    } else {
        result_obj = PyObject_CallMethod(pass_obj, "execute", NULL);
    }

    Py_XDECREF(cfun_obj);
    Py_DECREF(pass_obj);

    if (!result_obj) {
        gcc_python_print_exception("Unhandled Python exception raised calling 'execute' method");
        Gcc_SetInputLocation(saved_loc);
        return 0;
    }

    if (result_obj == Py_None) {
        Py_DECREF(result_obj);
        Gcc_SetInputLocation(saved_loc);
        return 0;
    }

#if PY_MAJOR_VERSION < 3
    if (PyInt_Check(result_obj)) {
        long result = PyInt_AS_LONG(result_obj);
        Py_DECREF(result_obj);
        Gcc_SetInputLocation(saved_loc);
        return result;
    }
#endif

    if (PyLong_Check(result_obj)) {
        long result = PyLong_AsLong(result_obj);
        Py_DECREF(result_obj);
        Gcc_SetInputLocation(saved_loc);
        return result;
    }

    PyErr_Format(PyExc_TypeError,
                 "execute returned a non-integer"   \
                 "(type %.200s)",
                 Py_TYPE(result_obj)->tp_name);
    Py_DECREF(result_obj);
    gcc_python_print_exception("Unhandled Python exception raised calling 'execute' method");
    Gcc_SetInputLocation(saved_loc);
    return 0;
}

static int
do_pass_init(PyObject *s, PyObject *args, PyObject *kwargs,
             enum opt_pass_type pass_type,
             size_t sizeof_pass)
{
    struct PyGccPass *self = (struct PyGccPass *)s;
    const char *name;
    char *keywords[] = {"name",
                        NULL};
    struct opt_pass *pass;

    /*
      We need to call _track manually as we're not using PyGccWrapper_New():
    */
    gcc_python_wrapper_track(&self->head);

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,
                                     "s:gcc.Pass.__init__", keywords,
                                     &name)) {
        return -1;
    }

    pass = PyMem_Malloc(sizeof_pass);
    if (!pass) {
        return -1;
    }
    memset(pass, 0, sizeof_pass);
    pass->type = pass_type;

    pass->name = gcc_python_strdup(name);
    /* does the name need to be unique?
       mapping from opt_pass ptr to callable?
       (the ID (as a long) is unique)
    */
    if (!pass->name) {
        PyMem_Free(pass);
        return -1;
    }

    pass->gate = impl_gate;
    pass->execute = impl_execute;

    if (gcc_python_insert_new_wrapper_into_cache(&pass_wrapper_cache,
                                                 pass,
                                                 s)) {
        return -1;
    }

    self->pass = pass;
    return 0; // FIXME
}

int
gcc_GimplePass_init(PyObject *self, PyObject *args, PyObject *kwds)
{
    return do_pass_init(self, args, kwds,
                        GIMPLE_PASS,
                        sizeof(struct gimple_opt_pass));
}

int
gcc_RtlPass_init(PyObject *self, PyObject *args, PyObject *kwds)
{
    return do_pass_init(self, args, kwds,
                        RTL_PASS,
                        sizeof(struct rtl_opt_pass));
}

int
gcc_SimpleIpaPass_init(PyObject *self, PyObject *args, PyObject *kwds)
{
    return do_pass_init(self, args, kwds,
                        SIMPLE_IPA_PASS,
                        sizeof(struct simple_ipa_opt_pass));
}

int
gcc_IpaPass_init(PyObject *self, PyObject *args, PyObject *kwds)
{
    return do_pass_init(self, args, kwds,
                        IPA_PASS,
                        sizeof(struct ipa_opt_pass_d));
}



PyObject *
gcc_Pass_repr(struct PyGccPass *self)
{
     return gcc_python_string_from_format("%s(name='%s')",
                                          Py_TYPE(self)->tp_name,
                                          self->pass->name);
}

PyObject *
gcc_Pass_get_dump_enabled(struct PyGccPass *self, void *closure)
{
    return PyBool_FromLong(dump_enabled_p(self->pass->static_pass_number));
}

int
gcc_Pass_set_dump_enabled(struct PyGccPass *self, PyObject *value, void *closure)
{
    struct dump_file_info *dfi = get_dump_file_info (self->pass->static_pass_number);
    assert(dfi);

    int newbool = PyObject_IsTrue(value);
    if (newbool == -1) {
        return -1;
    }

    if (dfi->state == 0) {
        /* Dumping was disabled: */
        if (newbool) {
            /* Enabling: */
            dfi->state = -1;
            return 0;
        } else {
            /* No change: */
            return 0;
        }
    } else {
        if (dfi->state < 0) {
            /* Dumping was enabled but has not yet started */
            if (newbool) {
                /* No change: */
                return 0;
            } else {
                /* Disabling: */
                dfi->state = 0;
                return 0;
            }
        } else {
            assert(dfi->state > 0);
            /* Dumping was enabled and has already started */
            if (newbool) {
                /* No change: */
                return 0;
            } else {
                /* Can't disable after it's started: */
                PyErr_SetString(PyExc_RuntimeError,
                                "Can't disable dumping: already started");
                return -1;
            }
        }
    }
}

PyObject *
gcc_Pass_get_roots(PyObject *cls, PyObject *noargs)
{
    /*
      There are 5 "roots" for the pass tree; see gcc/passes.c
    */
    PyObject *result;
    PyObject *passobj;

    result = PyTuple_New(5);
    if (!result) {
        goto error;
    }

#define SET_PASS(IDX, P) \
    passobj = gcc_python_make_wrapper_pass(P); \
    if (!passobj) goto error;                  \
    PyTuple_SET_ITEM(result, IDX, passobj);    \
    (void)0;

    SET_PASS(0, all_lowering_passes);
    SET_PASS(1, all_small_ipa_passes);
    SET_PASS(2, all_regular_ipa_passes);
    SET_PASS(3, all_lto_gen_passes);
    SET_PASS(4, all_passes);

    return result;

 error:
    Py_XDECREF(result);
    return NULL;

}

static struct opt_pass *
find_pass_by_name(const char *name, struct opt_pass *pass_list)
{
    struct opt_pass *pass;

    for (pass = pass_list; pass; pass = pass->next)
    {
        if (pass->name && !strcmp (name, pass->name)) {
            /* Found: */
            return pass;
        }

        if (pass->sub) {
            /* Recurse: */
            struct opt_pass *result = find_pass_by_name(name, pass->sub);
            if (result) {
                return result;
            }
        }
    }

    /* Not found: */
    return NULL;
}


PyObject *
gcc_Pass_get_by_name(PyObject *cls, PyObject *args, PyObject *kwargs)
{
    const char *name;
    char *keywords[] = {"name",
                        NULL};
    struct opt_pass *result;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,
                                     "s:get_by_name", keywords,
                                     &name)) {
        return NULL;
    }

#define SEARCH_WITHIN_LIST(PASS_LIST) \
    result = find_pass_by_name(name, (PASS_LIST));   \
    if (result) {                                    \
        return gcc_python_make_wrapper_pass(result); \
    }

    SEARCH_WITHIN_LIST(all_lowering_passes);
    SEARCH_WITHIN_LIST(all_small_ipa_passes);
    SEARCH_WITHIN_LIST(all_regular_ipa_passes);
    SEARCH_WITHIN_LIST(all_lto_gen_passes);
    SEARCH_WITHIN_LIST(all_passes);

    /* Not found: */
    PyErr_Format(PyExc_ValueError, "pass named '%s' not found", name);
    return NULL;
}

static PyObject *
impl_register(struct PyGccPass *self, PyObject *args, PyObject *kwargs,
              enum pass_positioning_ops pos_op, const char *arg_format)
{
    struct register_pass_info rpi;
    char *keywords[] = {"name",
                        "instance_number",
                        NULL};

    rpi.pass = self->pass;
    rpi.pos_op = pos_op;
    rpi.ref_pass_instance_number = 0;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,
                                     arg_format, keywords,
                                     &rpi.reference_pass_name,
                                     &rpi.ref_pass_instance_number)) {
        return NULL;
    }

    /* (Failures lead to a fatal error) */
    register_pass (&rpi);

    Py_RETURN_NONE;
}

PyObject *
gcc_Pass_register_before(struct PyGccPass *self, PyObject *args, PyObject *kwargs)
{
    return impl_register(self, args, kwargs,
                         PASS_POS_INSERT_BEFORE,
                         "s|i:register_before");
}

PyObject *
gcc_Pass_register_after(struct PyGccPass *self, PyObject *args, PyObject *kwargs)
{
    return impl_register(self, args, kwargs,
                         PASS_POS_INSERT_AFTER,
                         "s|i:register_after");
}

PyObject *
gcc_Pass_replace(struct PyGccPass *self, PyObject *args, PyObject *kwargs)
{
    return impl_register(self, args, kwargs,
                         PASS_POS_REPLACE,
                         "s|i:replace");
}

static PyGccWrapperTypeObject *
get_type_for_pass_type(enum opt_pass_type pt)
{
    switch (pt) {
    default: assert(0);

    case GIMPLE_PASS:
	return &gcc_GimplePassType;

    case RTL_PASS:
	return &gcc_RtlPassType;

    case SIMPLE_IPA_PASS:
	return &gcc_SimpleIpaPassType;

    case IPA_PASS:
	return &gcc_IpaPassType;
    }
};


static PyObject *
real_make_pass_wrapper(void *p)
{
    struct opt_pass *pass = (struct opt_pass *)p;
    PyGccWrapperTypeObject *type_obj;
    struct PyGccPass *pass_obj = NULL;

    if (NULL == pass) {
	Py_RETURN_NONE;
    }

    type_obj = get_type_for_pass_type(pass->type);

    pass_obj = PyGccWrapper_New(struct PyGccPass, type_obj);
    if (!pass_obj) {
        goto error;
    }

    pass_obj->pass = pass;
    /* FIXME: do we need to do something for the GCC GC? */

    return (PyObject*)pass_obj;
      
error:
    return NULL;
}

void
wrtp_mark_for_PyGccPass(PyGccPass *wrapper)
{
    /*
      This function is empty: struct opt_pass does not have a GTY()
      and any (struct opt_pass*) is either statically-allocated, or
      allocated by us within do_pass_init using PyMem_Malloc
    */
}

PyObject *
gcc_python_make_wrapper_pass(struct opt_pass *pass)
{
    return gcc_python_lazily_create_wrapper(&pass_wrapper_cache,
					    pass,
					    real_make_pass_wrapper);
}

/*
  PEP-7  
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
