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

#include "gcc-python-closure.h"
#include "gcc-python-wrappers.h"

/*
  Notes on the passes

  As of 2011-03-30, http://gcc.gnu.org/onlinedocs/gccint/Plugins.html doesn't
  seem to document the type of the gcc_data passed to each callback.

  For reference, with gcc-4.6.0-0.15.fc15.x86_64 the types seem to be as
  follows:

  PLUGIN_ATTRIBUTES:
    gcc_data=0x0
    Called from: init_attributes () at ../../gcc/attribs.c:187
    However, it seems at this point to have initialized these:
      static const struct attribute_spec *attribute_tables[4];
      static htab_t attribute_hash;

  PLUGIN_PRAGMAS:
    gcc_data=0x0
    Called from: c_common_init () at ../../gcc/c-family/c-opts.c:1052

  PLUGIN_START_UNIT:
    gcc_data=0x0
    Called from: compile_file () at ../../gcc/toplev.c:573

  PLUGIN_PRE_GENERICIZE
    gcc_data is:  tree fndecl;
    Called from: finish_function () at ../../gcc/c-decl.c:8323

  PLUGIN_OVERRIDE_GATE
    gcc_data:
      &gate_status
      bool gate_status;
    Called from : execute_one_pass (pass=0x1011340) at ../../gcc/passes.c:1520

  PLUGIN_PASS_EXECUTION
    gcc_data: struct opt_pass *pass
    Called from: execute_one_pass (pass=0x1011340) at ../../gcc/passes.c:1530

  PLUGIN_ALL_IPA_PASSES_START
    gcc_data=0x0
    Called from: ipa_passes () at ../../gcc/cgraphunit.c:1779

  PLUGIN_EARLY_GIMPLE_PASSES_START
    gcc_data=0x0
    Called from: execute_ipa_pass_list (pass=0x1011fa0) at ../../gcc/passes.c:1927

  PLUGIN_EARLY_GIMPLE_PASSES_END
    gcc_data=0x0
    Called from: execute_ipa_pass_list (pass=0x1011fa0) at ../../gcc/passes.c:1930

  PLUGIN_ALL_IPA_PASSES_END
    gcc_data=0x0
    Called from: ipa_passes () at ../../gcc/cgraphunit.c:1821

  PLUGIN_ALL_PASSES_START
    gcc_data=0x0
    Called from: tree_rest_of_compilation (fndecl=0x7ffff16b1f00) at ../../gcc/tree-optimize.c:420

  PLUGIN_ALL_PASSES_END
    gcc_data=0x0
    Called from: tree_rest_of_compilation (fndecl=0x7ffff16b1f00) at ../../gcc/tree-optimize.c:425

  PLUGIN_FINISH_UNIT
    gcc_data=0x0
    Called from: compile_file () at ../../gcc/toplev.c:668

  PLUGIN_FINISH
    gcc_data=0x0
    Called from: toplev_main (argc=17, argv=0x7fffffffdfc8) at ../../gcc/toplev.c:1970

  PLUGIN_FINISH_TYPE
    gcc_data=tree
    Called from c_parser_declspecs (parser=0x7fffef559730, specs=0x15296d0, scspec_ok=1 '\001', typespec_ok=1 '\001', start_attr_ok=<optimized out>, la=cla_nonabstract_decl) at ../../gcc/c-parser.c:2111

  PLUGIN_PRAGMA
    gcc_data=0x0
    Called from: init_pragma at ../../gcc/c-family/c-pragma.c:1321
    to  "Allow plugins to register their own pragmas."
*/

static enum plugin_event current_event = GCC_PYTHON_PLUGIN_BAD_EVENT;

int gcc_python_is_within_event(enum plugin_event *out_event)
{
    if (current_event != GCC_PYTHON_PLUGIN_BAD_EVENT) {
        if (out_event) {
            *out_event = current_event;
        }
        return 1;
    } else {
        return 0;
    }
}


static void
gcc_python_finish_invoking_callback(PyGILState_STATE gstate,
                                    int expect_wrapped_data, PyObject *wrapped_gcc_data,
                                    void *user_data)
    CPYCHECKER_STEALS_REFERENCE_TO_ARG(3) /* wrapped_gcc_data */ ;

static void
gcc_python_finish_invoking_callback(PyGILState_STATE gstate,
                                    int expect_wrapped_data, PyObject *wrapped_gcc_data,
                                    void *user_data)
{
    struct callback_closure *closure = (struct callback_closure *)user_data;
    PyObject *args = NULL;
    PyObject *result = NULL;
    location_t saved_loc = input_location;
    enum plugin_event saved_event;

    assert(closure);
    /* We take ownership of wrapped_gcc_data.
       For some callbacks types it will always be NULL; for others, it's only
       NULL if an error has occurred: */
    if (expect_wrapped_data && !wrapped_gcc_data) {
        goto cleanup;
    }

    if (cfun) {
        /* Temporarily override input_location to the top of the function: */
        input_location = cfun->function_start_locus;
    }

    args = gcc_python_closure_make_args(closure, 1, wrapped_gcc_data);
    if (!args) {
        goto cleanup;
    }

    saved_event = current_event;
    current_event = closure->event;

    result = PyObject_Call(closure->callback, args, closure->kwargs);

    current_event = saved_event;

    if (!result) {
        /* Treat an unhandled Python error as a compilation error: */
        gcc_python_print_exception("Unhandled Python exception raised within callback");
    }

    // FIXME: the result is ignored

cleanup:
    Py_XDECREF(wrapped_gcc_data);
    Py_XDECREF(args);
    Py_XDECREF(result);

    PyGILState_Release(gstate);
    input_location = saved_loc;
}

/*
  C-level callbacks for each event ID follow, thunking into the registered
  Python callable.

  There's some repetition here, but it can be easier to debug if you have
  separate breakpoint locations for each event ID.
 */

static void
gcc_python_callback_for_tree(void *gcc_data, void *user_data)
{
    PyGILState_STATE gstate;
    tree t = (tree)gcc_data;

    gstate = PyGILState_Ensure();

    gcc_python_finish_invoking_callback(gstate, 
					1, gcc_python_make_wrapper_tree(t),
					user_data);
}


static void
gcc_python_callback_for_PLUGIN_ATTRIBUTES(void *gcc_data, void *user_data)
{
    PyGILState_STATE gstate;

    //printf("%s:%i:(%p, %p)\n", __FILE__, __LINE__, gcc_data, user_data);

    gstate = PyGILState_Ensure();

    gcc_python_finish_invoking_callback(gstate,
                                        0, NULL,
                                        user_data);
}

static void
gcc_python_callback_for_PLUGIN_PASS_EXECUTION(void *gcc_data, void *user_data)
{
    PyGILState_STATE gstate;
    struct opt_pass *pass = (struct opt_pass *)gcc_data;

    //printf("%s:%i:(%p, %p)\n", __FILE__, __LINE__, gcc_data, user_data);
    assert(pass);

    gstate = PyGILState_Ensure();

    gcc_python_finish_invoking_callback(gstate, 
					1, gcc_python_make_wrapper_pass(pass),
					user_data);
}



static void
gcc_python_callback_for_FINISH_UNIT(void *gcc_data, void *user_data)
{
    PyGILState_STATE gstate;

    gstate = PyGILState_Ensure();

    gcc_python_finish_invoking_callback(gstate,
					0, NULL,
					user_data);
}



PyObject*
gcc_python_register_callback(PyObject *self, PyObject *args, PyObject *kwargs)
{
    int event;
    PyObject *callback = NULL;
    PyObject *extraargs = NULL;
    struct callback_closure *closure;

    if (!PyArg_ParseTuple(args, "iO|O:register_callback", &event, &callback, &extraargs)) {
        return NULL;
    }

    //printf("%s:%i:gcc_python_register_callback\n", __FILE__, __LINE__);

    closure = gcc_python_closure_new_for_plugin_event(callback, extraargs, kwargs,
                                                      (enum plugin_event)event);
    if (!closure) {
        return PyErr_NoMemory();
    }

    switch ((enum plugin_event)event) {
    case PLUGIN_ATTRIBUTES:
        register_callback("python", // FIXME
			  (enum plugin_event)event,
			  gcc_python_callback_for_PLUGIN_ATTRIBUTES,
			  closure);
	break;

    case PLUGIN_PRE_GENERICIZE:
        register_callback("python", // FIXME
			  (enum plugin_event)event,
			  gcc_python_callback_for_tree,
			  closure);
	break;
	
    case PLUGIN_PASS_EXECUTION:
        register_callback("python", // FIXME
			  (enum plugin_event)event,
			  gcc_python_callback_for_PLUGIN_PASS_EXECUTION,
			  closure);
	break;

    case PLUGIN_FINISH_UNIT:
        register_callback("python", // FIXME
			  (enum plugin_event)event,
			  gcc_python_callback_for_FINISH_UNIT,
			  closure);
	break;

    case PLUGIN_FINISH_TYPE:
        register_callback("python", // FIXME
			  (enum plugin_event)event,
			  gcc_python_callback_for_tree,
			  closure);
	break;

    default:
        PyErr_Format(PyExc_ValueError, "event type %i invalid (or not wired up yet)", event);
	return NULL;
    }
    
    Py_RETURN_NONE;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
